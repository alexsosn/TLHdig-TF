"""Second RED gate for issue #18 after the corpus scope audit.

These fixtures freeze the newly measured entry-internal grammar and document-order
apparatus scope before production conversion is revised.
"""
from __future__ import annotations

from lxml import etree as ET

from tlhdig import lineref, manuscripts

AO = "http://hethiter.net/ns/AO/1.0"


def parse(inner: str):
    root = ET.fromstring(
        f'<text xmlns:AO="{AO}"><AO:Manuscripts>{inner}</AO:Manuscripts></text>'.encode()
    )
    return manuscripts.parse(root[0])


def test_embedded_publication_chain_splits_occurrences_and_statement():
    got = parse('<AO:TxtPubl>KBo 3.45 {€1} + UBT 34 {€2}</AO:TxtPubl>')
    assert [(e.order, e.kind, e.label, e.siglum) for e in got.entries] == [
        (1, "txtpubl", "KBo 3.45", "€1"),
        (2, "txtpubl", "UBT 34", "€2"),
    ]
    assert [(s.order, s.kind, s.encoding, s.left, s.right, s.resolved) for s in got.statements] == [
        (1, "direct", "textual", 1, 2, True)
    ]


def test_embedded_mixed_chain_preserves_marker_and_local_order():
    got = parse(
        '<AO:TxtPubl>A {€1} (+) B {€2} + C {€3}</AO:TxtPubl>'
    )
    assert [(e.label, e.siglum) for e in got.entries] == [
        ("A", "€1"), ("B", "€2"), ("C", "€3")
    ]
    assert [(s.order, s.kind, s.raw, s.left, s.right) for s in got.statements] == [
        (1, "indirect", "(+)", 1, 2),
        (2, "direct", "+", 2, 3),
    ]


def test_embedded_inventory_chain_keeps_inventory_kind():
    got = parse('<AO:InvNr>Bo 3074 + Bo 8530</AO:InvNr>')
    assert [(e.kind, e.label) for e in got.entries] == [
        ("invnr", "Bo 3074"), ("invnr", "Bo 8530")
    ]
    assert [(s.kind, s.left, s.right, s.resolved) for s in got.statements] == [
        ("direct", 1, 2, True)
    ]


def test_letter_number_sigla_are_first_class_lookup_keys():
    got = parse('IBoT 3.100 {A1} + HT 71 {A2}')
    assert [(e.siglum, e.siglum_raw) for e in got.entries] == [
        ("A1", "{A1}"), ("A2", "{A2}")
    ]
    assert lineref.parse('{A1+2}1').frags == ("A1", "A2")


def test_spaced_euro_siglum_normalizes_but_preserves_raw_source():
    got = parse('A {€ 2} + B {€3}')
    assert got.entries[0].siglum == "€2"
    assert got.entries[0].siglum_raw == "{€ 2}"
    assert got.entries[0].siglum_raw_candidates == ("{€ 2}",)


def test_leading_embedded_operator_does_not_invent_left_endpoint():
    got = parse(
        '<AO:TxtPubl>+ B {€2}</AO:TxtPubl>'
        '<AO:TxtPubl>C {€3}</AO:TxtPubl>'
    )
    assert got.entries[0].label == "B"
    assert got.statements[0].kind == "direct"
    assert got.statements[0].left is None
    assert got.statements[0].resolved is False


def test_trailing_embedded_operator_can_resolve_against_following_block_entry():
    got = parse(
        '<AO:TxtPubl>A {€1} +</AO:TxtPubl>'
        '<AO:TxtPubl>B {€2}</AO:TxtPubl>'
    )
    assert [(e.label, e.siglum) for e in got.entries] == [("A", "€1"), ("B", "€2")]
    assert [(s.kind, s.left, s.right, s.resolved) for s in got.statements] == [
        ("direct", 1, 2, True)
    ]


def _doc(inner: str):
    return ET.fromstring(f'<AOxml xmlns:AO="{AO}"><body><div1>{inner}</div1></body></AOxml>'.encode())


def test_document_scope_ledgers_sibling_block_before_text_and_assigns_line():
    root = _doc(
        '<AO:Manuscripts><AO:TxtPubl nr="A1">A</AO:TxtPubl></AO:Manuscripts>'
        '<text><lb lnr="{A1}1"/></text>'
    )
    got = manuscripts.parse_document(root.find('body/div1'))
    assert len(got.blocks) == 1
    assert got.blocks[0].order == 1
    assert [line.block for line in got.lines] == [1]


def test_two_preline_blocks_are_both_ledgered_but_last_is_active():
    root = _doc(
        '<AO:Manuscripts><AO:TxtPubl nr="A1">old</AO:TxtPubl></AO:Manuscripts>'
        '<text>'
        '<AO:Manuscripts><AO:TxtPubl nr="A1">new</AO:TxtPubl></AO:Manuscripts>'
        '<lb lnr="{A1}1"/>'
        '</text>'
    )
    got = manuscripts.parse_document(root.find('body/div1'))
    assert [b.order for b in got.blocks] == [1, 2]
    assert [b.apparatus.entries[0].label for b in got.blocks] == ["old", "new"]
    assert [line.block for line in got.lines] == [2]


def test_midstream_block_switch_applies_only_to_later_lines():
    root = _doc(
        '<text>'
        '<AO:Manuscripts><AO:TxtPubl nr="A1">first</AO:TxtPubl></AO:Manuscripts>'
        '<lb lnr="{A1}1"/>'
        '<AO:Manuscripts><AO:TxtPubl nr="A1">second</AO:TxtPubl></AO:Manuscripts>'
        '<lb lnr="{A1}2"/>'
        '</text>'
    )
    got = manuscripts.parse_document(root.find('body/div1'))
    assert [line.block for line in got.lines] == [1, 2]


def test_trailing_block_is_ledgered_but_owns_no_earlier_line():
    root = _doc(
        '<text>'
        '<AO:Manuscripts><AO:TxtPubl nr="A1">first</AO:TxtPubl></AO:Manuscripts>'
        '<lb lnr="{A1}1"/>'
        '<AO:Manuscripts><AO:TxtPubl nr="A2">trailing</AO:TxtPubl></AO:Manuscripts>'
        '</text>'
    )
    got = manuscripts.parse_document(root.find('body/div1'))
    assert [b.order for b in got.blocks] == [1, 2]
    assert [line.block for line in got.lines] == [1]
