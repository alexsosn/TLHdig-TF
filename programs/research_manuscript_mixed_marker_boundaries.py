#!/usr/bin/env python
"""Measure newly admitted canonical markers in Manuscripts mixed text/tails (#18)."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import sys

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tlhdig import manuscripts, repair
from tlhdig.paths import CORPUS, ENCRYPTED, PATCHES, rel

ENTRY = {"TxtPubl", "TextPubl", "InvNr"}
XML_OP = {"DirectJoin", "InDirectJoin"}
OLD = re.compile(r"(?<!\S)(?P<m>\(\+\)\s*\?|\+\s*\?|\+\+|\(\+\)|\+)(?!\S)")


def lname(node):
    return ET.QName(node).localname if isinstance(node.tag, str) else "?"


def delta_markers(text: str):
    old_spans = {m.span() for m in OLD.finditer(text)}
    return [m for m in manuscripts._iter_markers(text) if m.span() not in old_spans]


def main() -> int:
    patches = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    counts = Counter()
    rows = []

    for path in sorted(CORPUS.rglob("*.xml")):
        r = rel(path)
        if r == ENCRYPTED:
            continue
        data = path.read_bytes()
        patch = patches.get(r)
        if patch:
            try:
                data = repair.apply(data, patch[1], expect_sha=patch[0])
            except repair.PatchError:
                continue
        try:
            root = ET.fromstring(data)
        except ET.XMLSyntaxError:
            continue

        for block_no, block in enumerate(root.xpath("//*[local-name()='Manuscripts']"), 1):
            chunks = [("block-text", None, block.text or "")]
            for child_no, child in enumerate(block, 1):
                kind = lname(child)
                if kind in ENTRY:
                    tail = child.tail or ""
                    match = manuscripts._TAIL_SIGLUM.match(tail)
                    if match:
                        tail = tail[match.end():]
                    chunks.append(("entry-tail", child_no, tail))
                elif kind in XML_OP:
                    chunks.append(("operator-tail", child_no, child.tail or ""))
                # Unknown-child tails are opaque in both grammars.

            for where, child_no, text in chunks:
                for match in delta_markers(text):
                    start, end = match.span()
                    left = text[:start].strip()
                    right = text[end:].strip()
                    counts["new_markers"] += 1
                    counts[where] += 1
                    counts["two_nonempty_sides" if left and right else "missing_side"] += 1
                    rows.append(
                        (
                            r,
                            block_no,
                            where,
                            child_no,
                            " ".join(match.group("marker").split()),
                            bool(left),
                            bool(right),
                            " ".join(text.split())[:350],
                        )
                    )

    for key in (
        "new_markers", "block-text", "entry-tail", "operator-tail",
        "two_nonempty_sides", "missing_side",
    ):
        print(f"{key}: {counts[key]:,}")
    print("mixed-text marker records:")
    for row in rows:
        print(f"  {row!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
