"""One-time source-only staging for #174; never overwrite a working corpus."""
import hashlib
import json
import stat
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

PREFIX = 'TLHbasisONLINE25_1_ZENODO_Beta_04/'
SHA256 = '3ec8ca10fde9d73106310f346b1790bf11ce538bcf855721cd75fa92b2d0f798'


def read_manifest(path):
    result = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        digest, sep, rel = line.partition('  ')
        if not sep or len(digest) != 64 or rel in result:
            raise ValueError('invalid old manifest row: ' + line)
        result[rel] = digest
    return result


def delta(old, new):
    added = sorted(new.keys() - old.keys())
    removed = sorted(old.keys() - new.keys())
    changed = sorted(p for p in old.keys() & new.keys() if old[p] != new[p])
    unchanged = sorted(p for p in old.keys() & new.keys() if old[p] == new[p])
    by_hash = defaultdict(list)
    for p in added:
        by_hash[new[p]].append(p)
    candidates = {p: by_hash[old[p]] for p in removed if old[p] in by_hash}
    return dict(added=added, removed=removed, changed=changed, unchanged=unchanged,
                exact_byte_rename_candidates=candidates)


def stage(archive, target):
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
        raise ValueError('wrong archive SHA-256')
    if target.exists():
        raise ValueError('target already exists')
    manifest = {}
    with ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError('CRC mismatch')
        members = {}
        for info in z.infolist():
            if info.is_dir() or info.filename.startswith('__MACOSX/'):
                continue
            if not info.filename.startswith(PREFIX):
                raise ValueError('unexpected archive root')
            rel = unicodedata.normalize('NFC', info.filename[len(PREFIX):])
            parts = rel.split('/')
            if any(p in ('', '.', '..') or p.lower() in ('.git', '.gitmodules', '.gitattributes', '.gitignore') for p in parts) or '\\' in rel:
                raise ValueError('unsafe path: ' + rel)
            if parts[-1] in ('.DS_Store', '.Spotlight-V100', '.Trashes') or parts[-1].startswith('._'):
                continue
            if info.flag_bits & 1 or stat.S_ISLNK(info.external_attr >> 16) or rel in members:
                raise ValueError('encrypted, symlink or duplicate member: ' + rel)
            members[rel] = info
        if len(members) != 24324 or sum(p.endswith('.xml') for p in members) != 24131:
            raise ValueError('unexpected source member count')
        target.mkdir(parents=True)
        for rel, info in sorted(members.items()):
            data = z.read(info)
            path = target / PurePosixPath(rel)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            manifest[rel] = hashlib.sha256(data).hexdigest()
    return manifest


def main():
    archive, target, old_file, report = map(Path, sys.argv[1:])
    old = read_manifest(old_file)
    new = stage(archive, target)
    d = delta(old, new)
    counts = {k: len(v) for k, v in d.items()}
    xml_counts = {k: sum(p.endswith('.xml') for p in v) for k, v in d.items()}
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(dict(counts=counts, xml_counts=xml_counts, **d), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(counts, xml_counts)


if __name__ == '__main__':
    main()
