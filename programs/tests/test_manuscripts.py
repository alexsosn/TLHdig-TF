"""Source grammar contract for AO:Manuscripts (issue #18).

These tests intentionally target a pure parser. Graph emission is a later RED gate after
this source model is stable.
"""
from __future__ import annotations

from lxml import etree as ET

from tlhdig import manuscripts

AO = "http://hethiter.net/ns/AO/1.0"


def parse(inner: str):
    root = ET.fromstring(
        f'<text xmlns:AO="{AO}"><AO:Manuscripts>{inner}</AO:Manuscripts></text>'.encode()
    )
    block = root[0]
    return manuscripts.parse(block)


def test_explicit_direct_join_is_between_entry_occurrences():
    got = parse(
        '<AO:TxtPubl nr="€1">KBo 1.1</AO:TxtPubl>'
        '<AO:DirectJoin/>'
        '<AO:TxtPubl nr="€2">KUB 2.2</AO:TxtPubl>'
    )
    assert [(e.order, e.kind, e.label, e.siglum) for e in got.entries] == [
        (1, "txtpubl", "KBo 1.1", "€1"),
        (2, "txtpubl", "KUB 2.2", "€2"),
    ]
    assert [(s.kind, s.encoding, s.left, s.right, s.resolved) for s in got.statements] == [
        ("direct", "xml", 1, 2, True)
    ]


def test_explicit_indirect_join():
    got = parse(
        '<AO:TxtPubl nr="€1">A</AO:TxtPubl><AO:InDirectJoin/>'
        '<AO:TxtPubl nr="€2">B</AO:TxtPubl>'
    )
    assert [(s.kind, s.raw) for s in got.statements] == [("indirect", "InDirectJoin")]


def test_inventory_entries_are_real_endpoints():
    got = parse(
        '<AO:InvNr nr="€1">Bo 1</AO:InvNr><AO:DirectJoin/>'
        '<AO:InvNr nr="€2">Bo 2</AO:InvNr>'
    )
    assert [e.kind for e in got.entries] == ["invnr", "invnr"]
    assert (got.statements[0].left, got.statements[0].right) == (1, 2)


def test_plain_mixed_text_entry_before_xml_operator():
    got = parse(
        'KBo 10.47c {€1} <AO:DirectJoin/>'
        '<AO:TxtPubl nr="€2">KBo 10.47a</AO:TxtPubl>'
    )
    assert [(e.kind, e.label, e.siglum, e.siglum_source) for e in got.entries] == [
        ("plain", "KBo 10.47c", "€1", "plain-text"),
        ("txtpubl", "KBo 10.47a", "€2", "attr"),
    ]
    assert (got.statements[0].left, got.statements[0].right) == (1, 2)


def test_text_only_plain_entry_chain_is_preserved():
    # Eight real source relations use this legacy text-only form. They must not vanish
    # merely because neither endpoint is wrapped in an AO element.
    got = parse('KBo 12.34 {€1} + KUB 56.78 {€2}')
    assert [(e.kind, e.label, e.siglum, e.siglum_source) for e in got.entries] == [
        ("plain", "KBo 12.34", "€1", "plain-text"),
        ("plain", "KUB 56.78", "€2", "plain-text"),
    ]
    assert [(s.kind, s.encoding, s.left, s.right, s.resolved) for s in got.statements] == [
        ("direct", "textual", 1, 2, True)
    ]


def test_legacy_textual_plus_and_parenthesized_plus():
    got = parse(
        '<AO:InvNr>1198/u</AO:InvNr>{€1} + '
        '<AO:InvNr>1436/u</AO:InvNr>{€2} (+) '
        '<AO:TxtPubl>KUB 8.82</AO:TxtPubl>{€3}'
    )
    assert [(e.siglum, e.siglum_source) for e in got.entries] == [
        ("€1", "tail"), ("€2", "tail"), ("€3", "tail")
    ]
    assert [(s.kind, s.encoding, s.left, s.right) for s in got.statements] == [
        ("direct", "textual", 1, 2),
        ("indirect", "textual", 2, 3),
    ]


def test_siglum_suffix_inside_entry_text_is_split_from_label():
    got = parse(
        '<AO:TxtPubl>KBo 50.266b {€2}</AO:TxtPubl> + '
        '<AO:TxtPubl>KUB 40.15 {€3}</AO:TxtPubl>'
    )
    assert [(e.label, e.siglum, e.siglum_source) for e in got.entries] == [
        ("KBo 50.266b", "€2", "element-text"),
        ("KUB 40.15", "€3", "element-text"),
    ]


def test_multiple_join_chain_preserves_statement_and_entry_order():
    got = parse(
        '<AO:TxtPubl>A</AO:TxtPubl> + <AO:TxtPubl>B</AO:TxtPubl> + '
        '<AO:TxtPubl>C</AO:TxtPubl>'
    )
    assert [e.order for e in got.entries] == [1, 2, 3]
    assert [(s.order, s.left, s.right) for s in got.statements] == [(1, 1, 2), (2, 2, 3)]


def test_mixed_textual_then_xml_operator_is_one_ordered_apparatus():
    got = parse(
        '<AO:TxtPubl>A</AO:TxtPubl> + <AO:TxtPubl>B</AO:TxtPubl>'
        '<AO:InDirectJoin/><AO:TxtPubl>C</AO:TxtPubl>'
    )
    assert [(s.kind, s.encoding, s.left, s.right) for s in got.statements] == [
        ("direct", "textual", 1, 2),
        ("indirect", "xml", 2, 3),
    ]


def test_uncertain_multi_and_targetless_markers_are_not_confident_binary_edges():
    cases = [
        ('<AO:TxtPubl>A</AO:TxtPubl> ++ <AO:TxtPubl>B</AO:TxtPubl>', "direct-multi"),
        ('<AO:TxtPubl>A</AO:TxtPubl> +? <AO:TxtPubl>B</AO:TxtPubl>', "uncertain"),
        ('<AO:TxtPubl>A</AO:TxtPubl> (+)? <AO:TxtPubl>B</AO:TxtPubl>', "uncertain"),
        ('<AO:TxtPubl>A</AO:TxtPubl> +', "direct"),
    ]
    for inner, kind in cases:
        got = parse(inner)
        assert len(got.statements) == 1
        stmt = got.statements[0]
        assert stmt.kind == kind
        assert stmt.resolved is False


def test_targetless_block_status_suffix_is_a_statement_not_generic_residual():
    got = parse("KBo 31.5++")
    assert [(s.kind, s.encoding, s.raw, s.left, s.right, s.resolved) for s in got.statements] == [
        ("direct-multi", "textual", "++", None, None, False)
    ]
    assert "KBo 31.5" in got.residual_text


def test_repeated_targetless_indirect_status_is_preserved_as_one_raw_statement():
    got = parse("KBo 52.108(+)(+)")
    assert [(s.kind, s.raw, s.resolved) for s in got.statements] == [
        ("indirect-multi", "(+)(+)", False)
    ]


def test_malformed_textual_join_tail_is_preserved_as_unresolved_statement():
    got = parse('<AO:TxtPubl>A</AO:TxtPubl>{€1} (+')
    assert got.entries[0].siglum == "€1"
    assert [(s.kind, s.encoding, s.raw, s.left, s.right, s.resolved) for s in got.statements] == [
        ("malformed", "textual", "(+", 1, None, False)
    ]


def test_unknown_child_blocks_guessing_textual_adjacency():
    got = parse(
        '<AO:TxtPubl>A</AO:TxtPubl> + <AO:note>editorial</AO:note>'
        '<AO:TxtPubl>B</AO:TxtPubl>'
    )
    assert len(got.statements) == 1
    assert got.statements[0].resolved is False
    assert got.statements[0].right is None


def test_duplicate_siglum_never_overwrites_entry_occurrence():
    got = parse(
        '<AO:TxtPubl nr="€1">A</AO:TxtPubl><AO:DirectJoin/>'
        '<AO:TxtPubl nr="€1">B</AO:TxtPubl>'
    )
    assert len(got.entries) == 2
    assert [e.label for e in got.entries] == ["A", "B"]
    assert [e.siglum for e in got.entries] == ["€1", "€1"]
    assert got.duplicate_sigla == {"€1": (1, 2)}


def test_conflicting_siglum_sources_are_diagnostic_not_precedence_guess():
    got = parse(
        '<AO:TxtPubl nr="€1">A</AO:TxtPubl>{€2} + '
        '<AO:TxtPubl nr="€3">B</AO:TxtPubl>'
    )
    first = got.entries[0]
    assert first.siglum == ""
    assert first.siglum_source == "conflict"
    assert set(first.siglum_candidates) == {"€1", "€2"}


def test_same_boundary_duplicate_same_kind_preserves_both_source_statements():
    # Synthetic adversarial shape: textual marker followed by an explicit marker before
    # the target. It is not a normal corpus shape, but the parser must not silently
    # collapse two source statements if a future upstream revision introduces one.
    got = parse(
        '<AO:TxtPubl>A</AO:TxtPubl> + <AO:DirectJoin/>'
        '<AO:TxtPubl>B</AO:TxtPubl>'
    )
    assert len(got.statements) == 2
    assert {s.encoding for s in got.statements} == {"textual", "xml"}
    assert all(s.kind == "direct" for s in got.statements)
    assert all((s.left, s.right) == (1, 2) for s in got.statements)


def test_same_boundary_conflict_is_detectable_for_derived_edge_suppression():
    got = parse(
        '<AO:TxtPubl>A</AO:TxtPubl> + <AO:InDirectJoin/>'
        '<AO:TxtPubl>B</AO:TxtPubl>'
    )
    assert len(got.statements) == 2
    assert {s.kind for s in got.statements} == {"direct", "indirect"}
    assert got.conflicting_boundaries == {(1, 2): ("direct", "indirect")}
