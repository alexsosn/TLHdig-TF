#!/usr/bin/env python
"""Measure canonical manuscript markers admitted beyond whitespace boundaries (#18)."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import sys

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tlhdig import repair
from tlhdig.paths import CORPUS, ENCRYPTED, PATCHES, rel

ENTRY = {"TxtPubl", "TextPubl", "InvNr"}
CANDIDATE = re.compile(r"(?P<m>\(\+\)|\+)")
OLD = re.compile(r"(?<!\S)(?P<m>\(\+\)|\+)(?!\S)")


def lname(node):
    return ET.QName(node).localname if isinstance(node.tag, str) else "?"


def new_marker(text: str, match) -> bool:
    start, end = match.span()
    left = text[start - 1] if start else ""
    right = text[end] if end < len(text) else ""
    return (not left or left.isspace() or left == "}") and (
        not right or right.isspace() or right == "{"
    )


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
            for child_no, child in enumerate(block, 1):
                if lname(child) not in ENTRY:
                    continue
                text = " ".join("".join(child.itertext()).split())
                old_spans = {m.span() for m in OLD.finditer(text)}
                for match in CANDIDATE.finditer(text):
                    if not new_marker(text, match) or match.span() in old_spans:
                        continue
                    start, end = match.span()
                    left_text = text[:start].strip()
                    right_text = text[end:].strip()
                    counts["new_markers"] += 1
                    counts["direct" if match.group("m") == "+" else "indirect"] += 1
                    if left_text and right_text:
                        counts["two_nonempty_sides"] += 1
                    else:
                        counts["missing_side"] += 1
                    rows.append(
                        (
                            r,
                            block_no,
                            child_no,
                            lname(child),
                            match.group("m"),
                            bool(left_text),
                            bool(right_text),
                            text[:350],
                        )
                    )

    for key in ("new_markers", "direct", "indirect", "two_nonempty_sides", "missing_side"):
        print(f"{key}: {counts[key]:,}")
    print("brace-adjacent marker records:")
    for row in rows:
        print(f"  {row!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
