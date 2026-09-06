#!/usr/bin/env python
"""Measure manuscript siglum spellings against line-reference fragment keys (#18).

The first parser research focused on the dominant ``€n`` family.  Some source apparatuses
use braces such as ``{A1}``; this pass inventories exact families in repaired/strict
converted sources and checks which forms are actually referenced by ``lb/@lnr``.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import sys

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tlhdig import lineref, manuscripts, repair
from tlhdig.paths import CORPUS, ENCRYPTED, PATCHES, rel

BRACED = re.compile(r"\{\s*([^{}]+?)\s*\}")


def family(value: str) -> str:
    v = value.strip()
    if re.fullmatch(r"€\d+", v):
        return "euro-number"
    if re.fullmatch(r"[A-Za-z]\d+", v):
        return "letter-number"
    if re.fullmatch(r"\d+", v):
        return "number"
    return "other"


def main() -> int:
    patches = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    braced_family = Counter()
    attr_family = Counter()
    line_family = Counter()
    braced_values = Counter()
    attr_values = Counter()
    line_values = Counter()
    parser_values = Counter()
    missed_examples = []

    for path in sorted(CORPUS.rglob("*.xml")):
        r = rel(path)
        if r == ENCRYPTED:
            continue
        data = path.read_bytes()
        entry = patches.get(r)
        if entry:
            try:
                data = repair.apply(data, entry[1], expect_sha=entry[0])
            except repair.PatchError:
                continue
        try:
            root = ET.fromstring(data)
        except ET.XMLSyntaxError:
            continue

        block_tokens = set()
        parsed_tokens = set()
        for block in root.xpath("//*[local-name()='Manuscripts']"):
            text = " ".join("".join(block.itertext()).split())
            for raw in BRACED.findall(text):
                raw = raw.strip()
                braced_family[family(raw)] += 1
                braced_values[raw] += 1
                block_tokens.add(raw)
            for child in block.iterchildren():
                raw = (child.get("nr") or "").strip()
                if raw:
                    attr_family[family(raw)] += 1
                    attr_values[raw] += 1
                    block_tokens.add(raw)
            for app_entry in manuscripts.parse(block).entries:
                if app_entry.siglum:
                    parser_values[app_entry.siglum] += 1
                    parsed_tokens.add(app_entry.siglum)

        line_tokens = set()
        for lb in root.iter("lb"):
            ref = lineref.parse(lb.get("lnr"))
            for token in ref.frags:
                if token:
                    line_family[family(token)] += 1
                    line_values[token] += 1
                    line_tokens.add(token)

        missing = sorted((line_tokens & block_tokens) - parsed_tokens)
        if missing and len(missed_examples) < 50:
            missed_examples.append((r, tuple(missing), tuple(sorted(line_tokens)), tuple(sorted(block_tokens))))

    print("braced token families:")
    for k, v in braced_family.most_common():
        print(f"  {k}: {v:,}")
    print("attribute siglum families:")
    for k, v in attr_family.most_common():
        print(f"  {k}: {v:,}")
    print("line fragment families (occurrences):")
    for k, v in line_family.most_common():
        print(f"  {k}: {v:,}")
    print("distinct values:")
    print(f"  braced: {len(braced_values):,}")
    print(f"  attr: {len(attr_values):,}")
    print(f"  line: {len(line_values):,}")
    print(f"  parser: {len(parser_values):,}")
    print("non-euro braced values used by lines:")
    used = sorted((set(braced_values) | set(attr_values)) & set(line_values))
    for token in used:
        if family(token) != "euro-number":
            print(f"  {token!r}: source={braced_values[token] + attr_values[token]:,} line={line_values[token]:,} parsed={parser_values[token]:,}")
    print(f"documents where a line-used source siglum is not recovered by parser: {len(missed_examples):,} shown (cap 50)")
    for row in missed_examples:
        print(f"  {row}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
