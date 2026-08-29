#!/usr/bin/env python
"""Generate programs/patches.yaml from the detectors, for files that do not parse.

The detectors are the generator; the manifest is the auditable artifact.  Only files
that (a) currently fail to parse and (b) parse after patching are recorded -- a
proposal that does not actually fix the file is reported, not shipped.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import repair
from tlhdig.paths import ENCRYPTED, PROGRAMS, REPORTS, corpus_files, rel


def main() -> int:
    entries: dict[str, tuple[str, list[repair.Patch]]] = {}
    stats = Counter()
    unfixed = []

    for f in corpus_files():
        data = f.read_bytes()
        if repair.parses(data):
            continue
        r = rel(f)
        stats["broken"] += 1

        if data[:7] == b"HBEGIN:":
            stats["encrypted"] += 1
            unfixed.append((r, "encrypted", "ownCloud/Nextcloud blob; not XML"))
            continue

        patches = repair.propose_iteratively(data)
        if not patches:
            stats["no_proposal"] += 1
            unfixed.append((r, "no_proposal", ""))
            continue
        try:
            fixed = repair.apply(data, patches)
        except repair.PatchError as e:
            stats["patch_error"] += 1
            unfixed.append((r, "patch_error", str(e)[:120]))
            continue
        if repair.parses(fixed):
            stats["repaired"] += 1
            entries[r] = (repair.sha256(data), patches)
            stats["patches"] += len(patches)
        else:
            stats["still_broken"] += 1
            unfixed.append((r, "still_broken", f"{len(patches)} patch(es) applied"))

    repair.write_manifest(PROGRAMS / "patches.yaml", entries)
    REPORTS.mkdir(exist_ok=True)
    with (REPORTS / "unrepaired.tsv").open("w", encoding="utf8") as fh:
        fh.write("file\treason\tdetail\n")
        for r in unfixed:
            fh.write("\t".join(r) + "\n")

    print(f"broken files   : {stats['broken']:,}")
    print(f"  repaired     : {stats['repaired']:,}  ({stats['patches']:,} patches)")
    print(f"  encrypted    : {stats['encrypted']:,}  (unrepairable, excluded)")
    print(f"  no proposal  : {stats['no_proposal']:,}")
    print(f"  still broken : {stats['still_broken']:,}")
    print(f"  patch error  : {stats['patch_error']:,}")
    print(f"\nmanifest -> {PROGRAMS / 'patches.yaml'}")
    print(f"report   -> {REPORTS / 'unrepaired.tsv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
