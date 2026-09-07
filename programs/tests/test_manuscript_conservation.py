"""Independent conservation/projection RED for issue #18.

These tests describe the release gate's pure comparison layer.  They intentionally do
not call the production graph emitter: the checker must be able to reject an emitter
that invents reverse/transitive/cross-block joins or loses source-ledger multiplicity.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig.manuscript_conservation import (
    FragmentRow,
    StatementRow,
    expected_joined,
    validate_fragments,
    validate_joined,
    validate_ledger,
    validate_witnesses,
)


def stmt(block, order, kind, left, right, *, resolved=True):
    return StatementRow(
        block=block,
        order=order,
        kind=kind,
        encoding="textual",
        raw="+" if kind == "direct" else "(+)",
        resolved=resolved,
        left=left,
        right=right,
    )


def fragment(block, order, *, label="A", siglum="€1", raw="{€1}", ambiguous=False):
    return FragmentRow(
        block=block,
        order=order,
        kind="txtpubl",
        label=label,
        siglum=siglum,
        siglum_source="tail",
        siglum_raw=raw,
        siglum_candidates=(siglum,),
        siglum_raw_candidates=(raw,),
        ambiguous=ambiguous,
    )


def test_fragment_ledger_preserves_occurrence_multiplicity_and_raw_provenance():
    source = [
        fragment(1, 1, label="A", raw="{ €1 }"),
        fragment(1, 2, label="A-copy", raw="{€1}", ambiguous=True),
    ]
    assert validate_fragments(source, list(source)) == ()
    assert validate_fragments(source, source[:1]) != (), "occurrence multiplicity is authoritative"
    changed_raw = [source[0], fragment(1, 2, label="A-copy", raw="{ €1 }", ambiguous=True)]
    assert validate_fragments(source, changed_raw) != (), "raw source spelling is provenance"


def test_expected_joined_collapses_same_kind_multiplicity_only_in_projection():
    source = [stmt(1, 1, "direct", 1, 2), stmt(1, 2, "direct", 1, 2)]
    assert expected_joined(source) == {(1, 1, 2): "direct"}
    assert validate_ledger(source, list(source)) == ()
    assert validate_ledger(source, [source[0]]) != (), "authoritative ledger keeps multiplicity"


def test_conflicting_direct_and_indirect_source_suppresses_joined_projection():
    source = [stmt(1, 1, "direct", 1, 2), stmt(1, 2, "indirect", 1, 2)]
    assert expected_joined(source) == {}
    assert validate_joined(source, []) == ()
    assert validate_joined(source, [(1, 1, 2, "direct")]) != ()


def test_reverse_and_transitive_edges_are_rejected_without_direct_source_support():
    source = [stmt(1, 1, "direct", 1, 2), stmt(1, 2, "direct", 2, 3)]
    assert validate_joined(
        source,
        [
            (1, 1, 2, "direct"),
            (1, 2, 3, "direct"),
            (1, 2, 1, "direct"),
            (1, 1, 3, "direct"),
        ],
    ) != ()


def test_cross_block_join_is_rejected_even_when_occurrence_numbers_match():
    source = [stmt(1, 1, "direct", 1, 2), stmt(2, 1, "direct", 1, 2)]
    assert validate_joined(
        source,
        [(1, 1, 2, "direct"), (2, 1, 2, "direct")],
    ) == ()
    assert validate_joined(source, [(1, 1, 2, "direct"), (1, 2, 1, "direct")]) != ()


def test_unresolved_or_nonconfident_statement_never_projects_joined():
    source = [
        stmt(1, 1, "direct", 1, None, resolved=False),
        stmt(1, 2, "uncertain", 1, 2, resolved=False),
    ]
    assert expected_joined(source) == {}
    assert validate_joined(source, []) == ()


def test_witness_validation_is_block_scoped_and_preserves_ambiguity():
    # Rows are (source-line-order, block, fragment-order, resolution).
    expected = [
        (1, 1, 1, "unique"),
        (2, 2, 1, "ambiguous"),
        (2, 2, 2, "ambiguous"),
    ]
    assert validate_witnesses(expected, list(expected)) == ()
    assert validate_witnesses(
        expected,
        [
            (1, 1, 1, "unique"),
            # Same siglum in block 1 must not satisfy a block-2 line.
            (2, 1, 1, "unique"),
        ],
    ) != ()


def test_ledger_comparison_rejects_source_or_graph_only_statement_rows():
    source = [stmt(1, 1, "direct", 1, 2)]
    graph = [stmt(1, 1, "direct", 1, 2), stmt(1, 2, "indirect", 2, 3)]
    problems = validate_ledger(source, graph)
    assert problems
    assert any("graph-only" in problem for problem in problems)
