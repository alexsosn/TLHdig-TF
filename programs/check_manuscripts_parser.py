#!/usr/bin/env python
"""Corpus gate for the issue #18 AO:Manuscripts source parser.

The expected counts are frozen from the independent research censuses committed before
implementation.  This gate is intentionally stricter than unit examples: every source
apparatus block must parse, every explicit XML join statement must survive, all safely
binary textual relations must remain resolved, and all researched non-canonical/status
join evidence must remain explicit unresolved statements rather than disappearing into
residual text.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tlhdig import manuscripts
from tlhdig.paths import CORPUS


EXPECTED = {
    "files": 23_937,
    "blocks": 24_402,
    "unrecoverable_files": 1,
    "xml_statements": 1_242,
    "resolved_textual_statements": 1_115,
    "unresolved_textual_statements": 30,
}


def _parse(data: bytes):
    for recover in (False, True):
        try:
            root = ET.fromstring(
                data,
                parser=ET.XMLParser(
                    recover=recover,
                    huge_tree=True,
                    resolve_entities=False,
                ),
            )
        except ET.XMLSyntaxError:
            continue
        if root is not None:
            return root
    return None


def main() -> int:
    counts = Counter()
    unresolved = Counter()
    malformed_files: list[str] = []

    for path in sorted(CORPUS.rglob("*.xml")):
        counts["files"] += 1
        root = _parse(path.read_bytes())
        if root is None:
            counts["unrecoverable_files"] += 1
            malformed_files.append(path.relative_to(CORPUS).as_posix())
            continue

        for block in root.xpath("//*[local-name()='Manuscripts']"):
            counts["blocks"] += 1
            parsed = manuscripts.parse(block)
            for statement in parsed.statements:
                if statement.encoding == "xml":
                    counts["xml_statements"] += 1
                elif statement.encoding == "textual" and statement.resolved:
                    counts["resolved_textual_statements"] += 1
                elif statement.encoding == "textual":
                    counts["unresolved_textual_statements"] += 1
                    unresolved[(statement.kind, statement.raw)] += 1
                else:
                    counts["unknown_encoding"] += 1

    problems = []
    for name, expected in EXPECTED.items():
        actual = counts[name]
        print(f"{name}: {actual:,} (expected {expected:,})")
        if actual != expected:
            problems.append(f"{name}: {actual:,} != {expected:,}")
    if counts["unknown_encoding"]:
        problems.append(f"unknown statement encoding: {counts['unknown_encoding']:,}")

    print("unresolved textual kinds/raw forms:")
    for (kind, raw), n in unresolved.most_common():
        print(f"  {kind:<16} {raw!r}: {n:,}")
    if malformed_files:
        print("unrecoverable files:")
        for rel in malformed_files:
            print(f"  {rel}")

    if problems:
        print("MANUSCRIPT PARSER CONSERVATION FAILED")
        for problem in problems:
            print(f"  {problem}")
        return 1

    print("manuscript parser conservation holds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
