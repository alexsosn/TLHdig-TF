#!/usr/bin/env python
"""Certify the TF 0.2.1 docid_raw correction against 0.2.0 and source XML.

This is deliberately stronger than checking the three known examples: every non-target
TF feature body must be identical across the two releases, and every 0.2.1 docid_raw
value must equal repaired source AOHeader/docID text at the converter parse boundary.
"""
from __future__ import annotations

from pathlib import Path
import sys
from xml.parsers import expat

import lxml.etree as LE

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import TF_VERSION, repair, source
from tlhdig.paths import CORPUS, ENCRYPTED, PATCHES, ROOT, corpus_files, rel as rel_key

OLD = "0.2.0"
NEW = "0.2.1"
EXPECTED = {
    "CTH 209_XML_TLH/KBo 50.89 .xml": "KBo 50.89 ",
    "CTH 628_XML_HFR/Merzifon I .xml": "Merzifon I ",
    "CTH 670_XML_TLH/KBo 71.241 .xml": "KBo 71.241 ",
}


def feature_body(path: Path) -> bytes:
    data = path.read_bytes()
    marker = b"\n\n"
    at = data.find(marker)
    if at < 0:
        raise AssertionError(f"no TF metadata/body separator in {path}")
    return data[at + len(marker):]


def metadata_value(path: Path, key: str) -> str | None:
    prefix = f"@{key}="
    for line in path.read_text(encoding="utf8").splitlines():
        if line.startswith(prefix):
            return line[len(prefix):]
        if not line.startswith("@"):
            break
    return None


def assert_non_target_tf_data_unchanged(old: Path, new: Path) -> None:
    old_names = {p.name for p in old.glob("*.tf")}
    new_names = {p.name for p in new.glob("*.tf")}
    assert old_names == new_names, (old_names - new_names, new_names - old_names)
    for name in sorted(old_names - {"docid_raw.tf"}):
        assert feature_body(old / name) == feature_body(new / name), name


def load_documents(path: Path):
    from tf.fabric import Fabric

    tf = Fabric(locations=str(path), silent="deep")
    api = tf.load("src_file docid docid_raw project subcorpus", silent="deep") or tf.api
    assert api is not None, path
    F = api.F
    docs = {}
    for d in F.otype.s("document"):
        src = F.src_file.v(d)
        assert src and src not in docs, src
        docs[src] = {
            "docid": F.docid.v(d),
            "docid_raw": F.docid_raw.v(d),
            "project": F.project.v(d),
            "subcorpus": F.subcorpus.v(d),
        }
    return api, docs


def repaired_source_docids() -> dict[str, str | None]:
    patches = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    result: dict[str, str | None] = {}
    for path in corpus_files():
        rel = rel_key(path, CORPUS)
        if rel == ENCRYPTED:
            continue
        data = path.read_bytes()
        entry = patches.get(rel)
        if entry:
            data = repair.apply(data, entry[1], expect_sha=entry[0])
        try:
            source.scan(data)
            root = LE.fromstring(data)
        except (expat.ExpatError, LE.XMLSyntaxError, ValueError):
            continue
        if root.find("body/div1/text") is None:
            continue
        result[rel] = root.findtext("AOHeader/docID")
    return result


def main() -> int:
    assert TF_VERSION == NEW, f"expected TF_VERSION={NEW}, got {TF_VERSION}"
    old = ROOT / "tf" / OLD
    new = ROOT / "tf" / NEW
    old_prov = ROOT / "tf-provenance" / OLD
    new_prov = ROOT / "tf-provenance" / NEW
    for path in (old, new, old_prov, new_prov):
        assert path.is_dir(), path

    # No graph/feature data except docid_raw may move. Metadata headers may differ by
    # version/date and docid_raw description, so compare the serialized data bodies.
    assert_non_target_tf_data_unchanged(old, new)
    assert_non_target_tf_data_unchanged(old_prov, new_prov)

    old_section = metadata_value(old / "otext.tf", "sectionFeatures")
    new_section = metadata_value(new / "otext.tf", "sectionFeatures")
    assert old_section == new_section == "docid,collabel,lnno", (old_section, new_section)

    old_api, old_docs = load_documents(old)
    new_api, new_docs = load_documents(new)
    assert len(old_docs) == len(new_docs) == 23884
    assert set(old_docs) == set(new_docs)

    changed = {}
    for src in sorted(old_docs):
        a, b = old_docs[src], new_docs[src]
        assert a["docid"] == b["docid"], src
        assert b["project"] == b["subcorpus"], src
        if a["docid_raw"] != b["docid_raw"]:
            changed[src] = b["docid_raw"]
    assert changed == EXPECTED, changed

    source_values = repaired_source_docids()
    assert set(source_values) == set(new_docs), (
        len(source_values), len(new_docs),
        sorted(set(source_values) - set(new_docs))[:5],
        sorted(set(new_docs) - set(source_values))[:5],
    )
    missing = []
    mismatched = []
    for src, raw in source_values.items():
        if raw in (None, ""):
            missing.append(src)
        elif new_docs[src]["docid_raw"] != raw:
            mismatched.append((src, raw, new_docs[src]["docid_raw"]))
    assert not missing, missing[:10]
    assert not mismatched, mismatched[:10]

    # The three corrected strings must also survive the fresh TF load above exactly.
    for src, raw in EXPECTED.items():
        assert new_docs[src]["docid_raw"] == raw

    old_types = {t: len(old_api.F.otype.s(t)) for t in old_api.F.otype.all}
    new_types = {t: len(new_api.F.otype.s(t)) for t in new_api.F.otype.all}
    assert old_types == new_types

    print(f"docid_raw release check OK: {len(new_docs):,} documents; 3 intended changes")
    print("all other main/provenance TF feature data bodies are unchanged")
    print("every 0.2.1 docid_raw matches repaired source XML")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
