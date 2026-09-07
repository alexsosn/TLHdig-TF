"""Pure comparison rules for the issue #18 manuscript release gate.

This module intentionally knows nothing about the production graph emitter.  It receives
source-derived and graph-derived rows and checks conservation plus the limited ``joined``
projection.  Keeping these rules separate prevents the release checker from validating
the emitter by simply reusing the emitter's implementation.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable


CONFIDENT_KINDS = frozenset({"direct", "indirect"})
EDGE_TYPES = {
    "joinDocument": ("joinstmt", "document"),
    "joinLeft": ("joinstmt", "fragment"),
    "joinRight": ("joinstmt", "fragment"),
    "joined": ("fragment", "fragment"),
    "witness": ("line", "fragment"),
    "witness_resolution": ("line", "fragment"),
}


@dataclass(frozen=True, order=True)
class FragmentRow:
    """One source/graph manuscript fragment occurrence, including siglum provenance."""

    block: int
    order: int
    kind: str
    label: str
    siglum: str
    siglum_source: str
    siglum_raw: str
    siglum_candidates: tuple[str, ...]
    siglum_raw_candidates: tuple[str, ...]
    ambiguous: bool


@dataclass(frozen=True, order=True)
class StatementRow:
    """One authoritative source/graph join-statement ledger row."""

    block: int
    order: int
    kind: str
    encoding: str
    raw: str
    resolved: bool
    left: int | None
    right: int | None


def _counter_problems(label: str, expected: Iterable, actual: Iterable) -> tuple[str, ...]:
    want = Counter(expected)
    got = Counter(actual)
    problems: list[str] = []
    for row, count in sorted((want - got).items(), key=lambda item: repr(item[0])):
        problems.append(f"{label} source-only x{count}: {row!r}")
    for row, count in sorted((got - want).items(), key=lambda item: repr(item[0])):
        problems.append(f"{label} graph-only x{count}: {row!r}")
    return tuple(problems)


def validate_fragments(
    source: Iterable[FragmentRow], graph: Iterable[FragmentRow]
) -> tuple[str, ...]:
    """Require exact fragment occurrence rows, multiplicity, and raw siglum evidence."""
    return _counter_problems("fragment", source, graph)


def validate_ledger(
    source: Iterable[StatementRow], graph: Iterable[StatementRow]
) -> tuple[str, ...]:
    """Require exact statement rows and multiplicity in both directions."""
    return _counter_problems("statement", source, graph)


def validate_fragment_ownership(rows: Iterable[tuple[int, int]]) -> tuple[str, ...]:
    """Require every graph fragment node to belong to exactly one document.

    Rows are ``(fragment_node, document_count)`` so the corpus checker can derive
    ownership through TF containment without exposing TF internals to this pure module.
    """
    problems: list[str] = []
    for node, count in rows:
        if count == 0:
            problems.append(f"fragment {node}: no document owner")
        elif count > 1:
            problems.append(f"fragment {node}: multiple documents ({count})")
    return tuple(problems)


def validate_edge_types(rows: Iterable[tuple[str, str, str]]) -> tuple[str, ...]:
    """Reject manuscript graph edges whose source/target node types violate the schema."""
    problems: list[str] = []
    for name, source_type, target_type in rows:
        expected = EDGE_TYPES.get(name)
        if expected is None:
            problems.append(f"unknown manuscript edge feature {name!r}")
            continue
        if (source_type, target_type) != expected:
            problems.append(
                f"{name}: {source_type}->{target_type}, expected {expected[0]}->{expected[1]}"
            )
    return tuple(problems)


def expected_joined(statements: Iterable[StatementRow]) -> dict[tuple[int, int, int], str]:
    """Derive the only convenience edges source evidence permits.

    Projection is block-local and occurrence-order based.  Unresolved/non-confident rows
    do not project. Multiple same-kind statements collapse to one convenience edge;
    conflicting direct+indirect support suppresses that boundary entirely.
    """
    support: dict[tuple[int, int, int], set[str]] = defaultdict(set)
    for row in statements:
        if (
            not row.resolved
            or row.kind not in CONFIDENT_KINDS
            or row.left is None
            or row.right is None
        ):
            continue
        support[(row.block, row.left, row.right)].add(row.kind)
    return {
        boundary: next(iter(kinds))
        for boundary, kinds in support.items()
        if len(kinds) == 1
    }


def validate_joined(
    statements: Iterable[StatementRow],
    graph_edges: Iterable[tuple[int, int, int, str]],
) -> tuple[str, ...]:
    """Reject missing, invented, reversed, transitive, cross-block, or wrong-valued joins."""
    want = expected_joined(statements)
    rows = list(graph_edges)
    problems: list[str] = []

    counts = Counter((block, left, right) for block, left, right, _kind in rows)
    for boundary, count in sorted(counts.items()):
        if count > 1:
            problems.append(f"joined duplicate graph edge x{count}: {boundary!r}")

    got: dict[tuple[int, int, int], str] = {}
    for block, left, right, kind in rows:
        boundary = (block, left, right)
        previous = got.get(boundary)
        if previous is not None and previous != kind:
            problems.append(
                f"joined conflicting graph values at {boundary!r}: {previous!r}, {kind!r}"
            )
        got[boundary] = kind

    for boundary, kind in sorted(want.items()):
        actual = got.get(boundary)
        if actual is None:
            problems.append(f"joined missing source-backed edge: {boundary!r} -> {kind!r}")
        elif actual != kind:
            problems.append(
                f"joined wrong value at {boundary!r}: graph {actual!r} != source {kind!r}"
            )
    for boundary, kind in sorted(got.items()):
        if boundary not in want:
            problems.append(f"joined graph-only edge: {boundary!r} -> {kind!r}")
    return tuple(problems)


def validate_witnesses(
    source: Iterable[tuple[int, int, int, str]],
    graph: Iterable[tuple[int, int, int, str]],
) -> tuple[str, ...]:
    """Require exact line/block/fragment/resolution rows including ambiguity multiplicity."""
    problems = list(_counter_problems("witness", source, graph))
    for row in graph:
        if len(row) != 4:
            problems.append(f"witness malformed row: {row!r}")
            continue
        resolution = row[3]
        if resolution not in {"unique", "ambiguous"}:
            problems.append(f"witness invalid resolution {resolution!r}: {row!r}")
    return tuple(problems)
