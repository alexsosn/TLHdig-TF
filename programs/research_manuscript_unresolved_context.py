#!/usr/bin/env python
"""Audit whether unresolved manuscript statements retain queryable source context (#18)."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
from xml.parsers import expat

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tlhdig import manuscripts, repair, source, sourcepath
from tlhdig.paths import CORPUS, ENCRYPTED, PATCHES, corpus_files, rel


def norm(value: str | None) -> str:
    return " ".join((value or "").split())


def main() -> int:
    patches = repair.read_manifest(PATCHES) if PATCHES.is_file() else {}
    counts = Counter()
    rows = []
    for path in corpus_files():
        src_file = rel(path)
        if src_file == ENCRYPTED:
            continue
        parsed_path = sourcepath.parse(src_file)
        if not parsed_path.parse_ok or not parsed_path.project:
            continue
        data = path.read_bytes()
        patch = patches.get(src_file)
        if patch:
            data = repair.apply(data, patch[1], expect_sha=patch[0])
        try:
            source.scan(data)
            root = ET.fromstring(data)
        except (expat.ExpatError, ET.XMLSyntaxError, ValueError):
            continue
        div1 = root.find("body/div1")
        text = div1.find("text") if div1 is not None else None
        if text is None:
            continue
        docid = norm(root.findtext("AOHeader/docID"))
        document = manuscripts.parse_document(div1)
        for block in document.blocks:
            app = block.apparatus
            block_text = norm("".join(block.element.itertext()))
            labels = tuple(entry.label for entry in app.entries)
            for stmt in app.statements:
                if stmt.resolved:
                    continue
                counts["unresolved"] += 1
                if stmt.left is None and stmt.right is None:
                    counts["no_endpoints"] += 1
                if not labels:
                    counts["no_fragment_entries"] += 1
                if app.residual_text:
                    counts["with_residual_text"] += 1
                if not labels and block_text and block_text != stmt.raw:
                    counts["context_only_in_block_text"] += 1
                    rows.append(
                        (
                            src_file,
                            docid,
                            block.order,
                            stmt.order,
                            stmt.kind,
                            stmt.raw,
                            stmt.left,
                            stmt.right,
                            block_text,
                            tuple(app.residual_text),
                        )
                    )
    for key in (
        "unresolved",
        "no_endpoints",
        "no_fragment_entries",
        "with_residual_text",
        "context_only_in_block_text",
    ):
        print(f"{key}: {counts[key]}")
    print("context-only unresolved rows:")
    for row in rows:
        print(repr(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
