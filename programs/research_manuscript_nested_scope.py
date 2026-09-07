#!/usr/bin/env python
"""Audit nested AO:Manuscripts blocks before graph integration for issue #18."""
from __future__ import annotations

from pathlib import Path
import sys

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tlhdig import lineref, manuscripts, repair
from tlhdig.paths import CORPUS, ENCRYPTED, PATCHES, rel


def lname(node) -> str:
    return ET.QName(node).localname if isinstance(node.tag, str) else "?"


def parse_source(path, r, patches):
    if r == ENCRYPTED:
        return None
    data = path.read_bytes()
    entry = patches.get(r)
    if entry:
        try:
            data = repair.apply(data, entry[1], expect_sha=entry[0])
        except repair.PatchError:
            return None
    try:
        return ET.fromstring(data)
    except ET.XMLSyntaxError:
        return None


def sigla(app):
    return tuple(e.siglum for e in app.entries if e.siglum)


def next_line_frag(div1, block):
    seen = False
    for node in div1.iter():
        if node is block:
            seen = True
            continue
        if not seen or lname(node) != "lb":
            continue
        ref = lineref.parse(node.get("lnr"))
        return ref.frag, ref.frags
    return "", ()


def main() -> int:
    patches = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    nested_rows = []
    docs = 0
    statements = 0
    entries = 0
    nested_with_line_after = 0
    nested_line_matches_nested = 0
    nested_line_matches_parent = 0

    for path in sorted(CORPUS.rglob("*.xml")):
        r = rel(path)
        root = parse_source(path, r, patches)
        if root is None:
            continue
        div1 = root.find("body/div1")
        if div1 is None:
            continue
        all_blocks = [n for n in div1.iter() if lname(n) == "Manuscripts"]
        nested = [
            b for b in all_blocks
            if any(lname(a) == "Manuscripts" for a in b.iterancestors())
        ]
        if not nested:
            continue
        docs += 1
        for block in nested:
            app = manuscripts.parse(block)
            entries += len(app.entries)
            statements += len(app.statements)
            parent = next(
                (a for a in block.iterancestors() if lname(a) == "Manuscripts"), None
            )
            parent_app = manuscripts.parse(parent) if parent is not None else None
            raw_frag, parts = next_line_frag(div1, block)
            if raw_frag:
                nested_with_line_after += 1
                nested_keys = set(sigla(app))
                parent_keys = set(sigla(parent_app)) if parent_app else set()
                if any(p in nested_keys for p in parts):
                    nested_line_matches_nested += 1
                if any(p in parent_keys for p in parts):
                    nested_line_matches_parent += 1
            nested_rows.append(
                (
                    r,
                    all_blocks.index(block) + 1,
                    all_blocks.index(parent) + 1 if parent in all_blocks else None,
                    tuple((e.kind, e.label, e.siglum) for e in app.entries),
                    tuple((s.kind, s.encoding, s.raw, s.left, s.right, s.resolved) for s in app.statements),
                    sigla(parent_app) if parent_app else (),
                    raw_frag,
                    parts,
                    " ".join("".join(block.itertext()).split())[:300],
                )
            )

    print(f"documents_with_nested_blocks: {docs:,}")
    print(f"nested_blocks: {len(nested_rows):,}")
    print(f"nested_entries: {entries:,}")
    print(f"nested_statements: {statements:,}")
    print(f"nested_with_following_line_frag: {nested_with_line_after:,}")
    print(f"following_line_matches_nested: {nested_line_matches_nested:,}")
    print(f"following_line_matches_parent: {nested_line_matches_parent:,}")
    print("nested block records:")
    for row in nested_rows:
        print(f"  {row!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
