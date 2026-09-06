#!/usr/bin/env python
"""Measure which AO:Manuscripts blocks/statements are reachable by production conversion.

Issue #18 research originally counted every Manuscripts block in recovered XML. Production
uses the repository repair/exclusion contract and one primary ``body/div1/text`` per
converted source record. This pass measures the exact repaired/strict gap and classifies
where statement-bearing blocks outside that primary apparatus live before the graph model
is changed again.
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


def _lname(node) -> str:
    return ET.QName(node).localname if isinstance(node.tag, str) else "?"


def _shape(block) -> str:
    nodes = list(block.iterancestors())[::-1] + [block]
    return "/".join(_lname(n) for n in nodes)


def main() -> int:
    patches = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    counts = Counter()
    path_shapes = Counter()
    statement_path_shapes = Counter()
    examples = []
    statement_examples = []

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
            parsed = manuscripts.parse(primary)
            counts["reachable_blocks"] += 1
            counts["reachable_entries"] += len(parsed.entries)
            counts["reachable_statements"] += len(parsed.statements)

        unreachable = [b for b in all_blocks if b is not primary]
        if unreachable:
            counts["files_with_unreachable_blocks"] += 1
            counts["unreachable_blocks"] += len(unreachable)
            nstmt = 0
            for block_index, block in enumerate(unreachable):
                parsed = manuscripts.parse(block)
                shape = _shape(block)
                path_shapes[shape] += 1
                nstmt += len(parsed.statements)
                if parsed.statements:
                    statement_path_shapes[shape] += len(parsed.statements)
                    counts["statement_bearing_unreachable_blocks"] += 1
                    if len(statement_examples) < 60:
                        statement_examples.append(
                            (
                                r,
                                block_index,
                                shape,
                                len(parsed.entries),
                                tuple(
                                    (s.order, s.kind, s.encoding, s.raw, s.left, s.right, s.resolved)
                                    for s in parsed.statements
                                ),
                                " ".join("".join(block.itertext()).split())[:240],
                            )
                        )
            counts["unreachable_statements"] += nstmt
            if len(examples) < 30:
                examples.append((r, len(all_blocks), len(unreachable), nstmt))

    for key in (
        "files", "excluded_encrypted", "unparseable", "patch_failed",
        "strict_blocks_all", "reachable_blocks", "unreachable_blocks",
        "strict_statements_all", "reachable_statements", "unreachable_statements",
        "statement_bearing_unreachable_blocks", "reachable_entries",
        "files_with_unreachable_blocks",
    ):
        print(f"{key}: {counts[key]:,}")

    print("unreachable block ancestry shapes:")
    for shape, n in path_shapes.most_common(20):
        print(f"  {n:>5,}  {shape}")
    print("statement counts by unreachable ancestry shape:")
    for shape, n in statement_path_shapes.most_common(20):
        print(f"  {n:>5,}  {shape}")

    if examples:
        print("first files with blocks outside production primary apparatus:")
        for row in examples:
            print("  %s all=%d unreachable=%d statements=%d" % row)
    if statement_examples:
        print("first statement-bearing unreachable blocks:")
        for relpath, index, shape, nentries, statements, text in statement_examples:
            print(f"  {relpath} block={index} path={shape} entries={nentries}")
            print(f"    statements={statements}")
            print(f"    text={text!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
