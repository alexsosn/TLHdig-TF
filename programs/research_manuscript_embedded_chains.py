#!/usr/bin/env python
"""Measure canonical join syntax embedded inside AO:Manuscripts entry elements (#18).

Some newer records wrap an entire legacy chain in one TxtPubl/InvNr element, e.g.
``<TxtPubl>KBo 3.45 {€1} + UBT 34 {€2}</TxtPubl>``. The first parser census treated
that as one entry. This pass measures only whitespace-delimited canonical +/(+) markers
inside entry element text; publication suffixes such as ``KUB 47.90+`` are excluded.
"""
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
MARKER = re.compile(r"(?<!\S)(?P<m>\(\+\)|\+)(?!\S)")
BRACED = re.compile(r"\{\s*([^{}]+?)\s*\}")


def lname(node):
    return ET.QName(node).localname if isinstance(node.tag, str) else "?"


def main() -> int:
    patches = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    c = Counter()
    shapes = Counter()
    examples = []
    line_used = Counter()

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

        lnr_text = " ".join((lb.get("lnr") or "") for lb in root.iter("lb"))
        for block_no, block in enumerate(root.xpath("//*[local-name()='Manuscripts']"), 1):
            for child_no, child in enumerate(block, 1):
                kind = lname(child)
                if kind not in ENTRY:
                    continue
                text = " ".join("".join(child.itertext()).split())
                markers = list(MARKER.finditer(text))
                if not markers:
                    continue
                c["elements"] += 1
                c["markers"] += len(markers)
                direct = sum(1 for m in markers if m.group("m") == "+")
                indirect = len(markers) - direct
                c["direct"] += direct
                c["indirect"] += indirect
                shapes[(kind, len(markers), tuple(m.group("m") for m in markers))] += 1
                sigla = tuple(x.strip() for x in BRACED.findall(text))
                c["braced_tokens"] += len(sigla)
                if sigla:
                    c["elements_with_sigla"] += 1
                    for s in sigla:
                        if "{" + s + "}" in lnr_text:
                            line_used[s] += 1
                            c["source_sigla_used_on_lines"] += 1
                parts = []
                pos = 0
                for m in markers:
                    parts.append(text[pos:m.start()].strip())
                    pos = m.end()
                parts.append(text[pos:].strip())
                if all(parts):
                    c["markers_with_two_nonempty_segments"] += len(markers)
                else:
                    c["elements_with_empty_segment"] += 1
                if len(examples) < 80:
                    examples.append((r, block_no, child_no, kind, text, sigla))

    for key in (
        "elements", "markers", "direct", "indirect", "elements_with_sigla",
        "braced_tokens", "source_sigla_used_on_lines", "markers_with_two_nonempty_segments",
        "elements_with_empty_segment",
    ):
        print(f"{key}: {c[key]:,}")
    print("shapes:")
    for shape, n in shapes.most_common(30):
        print(f"  {n:>5,} {shape}")
    print("line-used sigla in embedded chains:")
    for siglum, n in line_used.most_common():
        print(f"  {siglum!r}: {n:,} source elements")
    print("first examples:")
    for row in examples:
        print(f"  {row}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
