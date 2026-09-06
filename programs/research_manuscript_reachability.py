#!/usr/bin/env python
"""Measure which AO:Manuscripts blocks/statements are reachable by production conversion.

Issue #18 research counted every Manuscripts block in recovered XML.  Production uses the
repository repair/exclusion contract and one primary body/div1/text per converted source
record.  This pass closes that scope boundary before the source->graph conservation gate
is frozen.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tlhdig import manuscripts, repair
from tlhdig.paths import CORPUS, ENCRYPTED, PATCHES, rel

AO = "{http://hethiter.net/ns/AO/1.0}"


def main() -> int:
    patches = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    counts = Counter()
    examples = []

    for path in sorted(CORPUS.rglob("*.xml")):
        r = rel(path)
        counts["files"] += 1
        if r == ENCRYPTED:
            counts["excluded_encrypted"] += 1
            continue
        data = path.read_bytes()
        entry = patches.get(r)
        if entry:
            try:
                data = repair.apply(data, entry[1], expect_sha=entry[0])
            except repair.PatchError:
                counts["patch_failed"] += 1
                continue
        try:
            root = ET.fromstring(data)
        except ET.XMLSyntaxError:
            counts["unparseable"] += 1
            continue

        all_blocks = root.xpath("//*[local-name()='Manuscripts']")
        counts["strict_blocks_all"] += len(all_blocks)
        counts["strict_statements_all"] += sum(len(manuscripts.parse(b).statements) for b in all_blocks)

        text = root.find("body/div1/text")
        primary = text.find(f"{AO}Manuscripts") if text is not None else None
        if primary is not None:
            counts["reachable_blocks"] += 1
            counts["reachable_entries"] += len(manuscripts.parse(primary).entries)
            counts["reachable_statements"] += len(manuscripts.parse(primary).statements)

        unreachable = [b for b in all_blocks if b is not primary]
        if unreachable:
            counts["files_with_unreachable_blocks"] += 1
            counts["unreachable_blocks"] += len(unreachable)
            nstmt = sum(len(manuscripts.parse(b).statements) for b in unreachable)
            counts["unreachable_statements"] += nstmt
            if len(examples) < 30:
                examples.append((r, len(all_blocks), len(unreachable), nstmt))

    for key in (
        "files", "excluded_encrypted", "unparseable", "patch_failed",
        "strict_blocks_all", "reachable_blocks", "unreachable_blocks",
        "strict_statements_all", "reachable_statements", "unreachable_statements",
        "reachable_entries", "files_with_unreachable_blocks",
    ):
        print(f"{key}: {counts[key]:,}")
    if examples:
        print("first files with blocks outside production primary apparatus:")
        for row in examples:
            print("  %s all=%d unreachable=%d statements=%d" % row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
