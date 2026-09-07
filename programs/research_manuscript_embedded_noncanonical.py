#!/usr/bin/env python
"""Independently census noncanonical join-shaped markers inside manuscript entry text (#18)."""
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
# Longest/most-specific alternatives first. Canonical +/(+) are included so the scan can
# segment text correctly, but this report emits only the noncanonical or endpoint-missing cases.
MARKER = re.compile(r"(?P<m>\(\+\)\s*\?|\+\s*\?|\+\+|\(\+\)|\+)")


def lname(node):
    return ET.QName(node).localname if isinstance(node.tag, str) else "?"


def admitted(text: str, match) -> bool:
    start, end = match.span()
    left = text[start - 1] if start else ""
    right = text[end] if end < len(text) else ""
    return (not left or left.isspace() or left == "}") and (
        not right or right.isspace() or right == "{"
    )


def kind(raw: str) -> str:
    compact = "".join(raw.split())
    if compact == "+":
        return "direct"
    if compact == "(+)":
        return "indirect"
    if compact == "++":
        return "direct-multi"
    if compact in {"+?", "(+)?"}:
        return "uncertain"
    return "other"


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
                markers = [m for m in MARKER.finditer(text) if admitted(text, m)]
                if not markers:
                    continue
                cursor = 0
                segments = []
                for m in markers:
                    segments.append(text[cursor:m.start()].strip())
                    cursor = m.end()
                segments.append(text[cursor:].strip())
                for index, m in enumerate(markers):
                    raw = " ".join(m.group("m").split())
                    k = kind(raw)
                    left_ok = bool(segments[index])
                    right_ok = bool(segments[index + 1])
                    if k in {"direct", "indirect"} and left_ok and right_ok:
                        continue
                    counts["records"] += 1
                    counts[k] += 1
                    counts["both_sides" if left_ok and right_ok else "missing_side"] += 1
                    rows.append((
                        r, block_no, child_no, lname(child), raw, k,
                        left_ok, right_ok, text[:500],
                    ))

    for key in ("records", "direct", "indirect", "direct-multi", "uncertain", "other", "both_sides", "missing_side"):
        print(f"{key}: {counts[key]:,}")
    print("noncanonical/endpoint-missing embedded records:")
    for row in rows:
        print(f"  {row!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
