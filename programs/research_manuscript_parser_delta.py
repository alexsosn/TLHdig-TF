#!/usr/bin/env python
"""Independently reconstruct the textual-statement delta for issue #18.

This deliberately does not use the parser's marker regex to count the new source forms.
It combines the frozen legacy textual inventory with two independently measured grammar
extensions: markers inside entry element text and canonical tails whose braced siglum was
outside the legacy euro-only grammar.  Parser output is consulted only afterwards as the
quantity being checked and to print unresolved-delta diagnostics.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tlhdig import manuscripts
from tlhdig.paths import CORPUS, REPORTS

ENTRY = {"TxtPubl", "TextPubl", "InvNr"}
LEGACY_SIGLUM = re.compile(r"\{\s*€\d+\s*\}")
EXTENDED_SIGLUM = re.compile(r"\{\s*(?:€\s*\d+|[A-Za-z]\d+|\d+)\s*\}")
CANONICAL_MARKER = re.compile(r"^(?:\(\+\)|\+)$")
ENTRY_MARKER = re.compile(r"\(\+\)|\+")


def lname(node) -> str:
    return ET.QName(node).localname if isinstance(node.tag, str) else ""


def parse_source(data: bytes):
    for recover in (False, True):
        try:
            root = ET.fromstring(
                data,
                parser=ET.XMLParser(recover=recover, huge_tree=True, resolve_entities=False),
            )
        except ET.XMLSyntaxError:
            continue
        if root is not None:
            return root
    return None


def marker_allowed(text: str, match) -> bool:
    """Independent lexical boundary: whitespace or a siglum brace may touch a join."""
    start, end = match.span()
    left = text[start - 1] if start else ""
    right = text[end] if end < len(text) else ""
    return (
        (not left or left.isspace() or left == "}")
        and (not right or right.isspace() or right == "{")
    )


def main() -> int:
    legacy_path = REPORTS / "joins-textual-research.json"
    if not legacy_path.is_file():
        raise SystemExit("run research_joins_textual.py first")
    legacy = json.loads(legacy_path.read_text(encoding="utf8"))
    legacy_relations = legacy["relations"]
    legacy_unresolved = legacy["unresolved"]
    legacy_total = len(legacy_relations) + len(legacy_unresolved)

    legacy_unresolved_by_block = Counter(
        (row["src_file"], int(row["block"])) for row in legacy_unresolved
    )

    independent = Counter()
    extended_tail_rows = []
    parser = Counter()
    parser_unresolved_by_block = Counter()
    parser_unresolved_rows = defaultdict(list)

    for path in sorted(CORPUS.rglob("*.xml")):
        rel = path.relative_to(CORPUS).as_posix()
        root = parse_source(path.read_bytes())
        if root is None:
            continue
        for block_index, block in enumerate(root.xpath("//*[local-name()='Manuscripts']")):
            # New family 1: join operators serialized inside entry element text.  The
            # legacy textual census looked only at block text and element tails.
            for child in block:
                if lname(child) not in ENTRY:
                    continue
                text = "".join(child.itertext())
                for match in ENTRY_MARKER.finditer(text):
                    if marker_allowed(text, match):
                        independent["entry_internal_markers"] += 1

                # New family 2: a canonical tail relation whose siglum prefix could not
                # be removed by the legacy euro-only grammar but can be removed by the
                # independently stated expanded source grammar.
                tail = " ".join((child.tail or "").split())
                if not tail:
                    continue
                old_remainder = " ".join(LEGACY_SIGLUM.sub("", tail).split())
                new_remainder = " ".join(EXTENDED_SIGLUM.sub("", tail).split())
                if (
                    old_remainder != new_remainder
                    and CANONICAL_MARKER.fullmatch(new_remainder)
                    and not CANONICAL_MARKER.fullmatch(old_remainder)
                ):
                    independent["extended_siglum_tail_markers"] += 1
                    if len(extended_tail_rows) < 100:
                        extended_tail_rows.append(
                            (rel, block_index, lname(child), tail, old_remainder, new_remainder)
                        )

            parsed = manuscripts.parse(block)
            for statement in parsed.statements:
                if statement.encoding != "textual":
                    continue
                parser["textual_total"] += 1
                if statement.resolved:
                    parser["resolved"] += 1
                else:
                    parser["unresolved"] += 1
                    key = (rel, block_index)
                    parser_unresolved_by_block[key] += 1
                    parser_unresolved_rows[key].append(
                        (statement.kind, statement.raw, statement.left, statement.right)
                    )

    expected_total = (
        legacy_total
        + independent["entry_internal_markers"]
        + independent["extended_siglum_tail_markers"]
    )
    print(f"legacy_relations: {len(legacy_relations):,}")
    print(f"legacy_unresolved: {len(legacy_unresolved):,}")
    print(f"legacy_total: {legacy_total:,}")
    print(f"entry_internal_markers: {independent['entry_internal_markers']:,}")
    print(f"extended_siglum_tail_markers: {independent['extended_siglum_tail_markers']:,}")
    print(f"independently_reconstructed_total: {expected_total:,}")
    print(f"parser_textual_total: {parser['textual_total']:,}")
    print(f"parser_resolved: {parser['resolved']:,}")
    print(f"parser_unresolved: {parser['unresolved']:,}")
    print("extended-siglum tail records:")
    for row in extended_tail_rows:
        print(f"  {row}")

    changed_unresolved = []
    for key in sorted(set(legacy_unresolved_by_block) | set(parser_unresolved_by_block)):
        old = legacy_unresolved_by_block[key]
        new = parser_unresolved_by_block[key]
        if old != new:
            changed_unresolved.append((key, old, new, parser_unresolved_rows.get(key, [])))
    print("blocks with changed unresolved cardinality:")
    for row in changed_unresolved:
        print(f"  {row}")

    problems = []
    if expected_total != parser["textual_total"]:
        problems.append(
            f"independent textual total {expected_total} != parser {parser['textual_total']}"
        )
    if independent["entry_internal_markers"] != 1_242:
        problems.append(
            f"entry-internal marker census changed: {independent['entry_internal_markers']} != 1242"
        )
    if independent["extended_siglum_tail_markers"] != 10:
        problems.append(
            f"extended-siglum tail census changed: {independent['extended_siglum_tail_markers']} != 10"
        )
    if problems:
        print("PARSER DELTA AUDIT FAILED")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print("expanded parser textual total is independently reconstructed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
