#!/usr/bin/env python
"""Inspect AO:Manuscripts blocks that occur after a line has begun (#18 research)."""
from __future__ import annotations

from pathlib import Path
import sys

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tlhdig import manuscripts, repair
from tlhdig.paths import CORPUS, ENCRYPTED, PATCHES, rel


def lname(node):
    return ET.QName(node).localname if isinstance(node.tag, str) else "?"


def main() -> int:
    patches = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    found = 0
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
        div1 = root.find("body/div1")
        if div1 is None:
            continue
        seen_line = False
        last_line = ""
        block_no = 0
        for node in div1.iter():
            name = lname(node)
            if name == "lb":
                seen_line = True
                last_line = node.get("lnr") or ""
            elif name == "Manuscripts":
                block_no += 1
                if not seen_line:
                    continue
                found += 1
                app = manuscripts.parse(node)
                following = node.xpath("following::*[local-name()='lb'][1]")
                next_line = (following[0].get("lnr") or "") if following else ""
                path_shape = "/".join(lname(x) for x in (list(node.iterancestors())[::-1] + [node]))
                print(f"file: {r}")
                print(f"  block: {block_no} path={path_shape}")
                print(f"  previous_line: {last_line!r}")
                print(f"  next_line: {next_line!r}")
                print(f"  entries: {[(e.kind, e.label, e.siglum) for e in app.entries]!r}")
                print(f"  statements: {[(s.kind, s.encoding, s.raw, s.left, s.right, s.resolved) for s in app.statements]!r}")
                print(f"  text: {' '.join(''.join(node.itertext()).split())[:500]!r}")
    print(f"post-line Manuscripts blocks: {found}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
