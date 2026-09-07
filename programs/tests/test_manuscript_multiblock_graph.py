"""Multi-block graph RED for issue #18 after the source-scope research gate."""
from __future__ import annotations

from tlhdig import convert

AO = "http://hethiter.net/ns/AO/1.0"


def _build(tmp_path, div1_inner: str):
    src = tmp_path / "corpus" / "CTH 999_XML_TLH"
    src.mkdir(parents=True)
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<AOxml xmlns:AO="{AO}">
<AOHeader><docID>MULTI</docID><meta><creation-date date="2026-01-01"/></meta></AOHeader>
<body><div1 type="transliteration">{div1_inner}</div1></body></AOxml>
'''
    (src / "MULTI.xml").write_text(xml, encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None, "conversion failed"
    return api


def _line(n: int, frag: str) -> str:
    return (
        f'<lb txtid="MULTI" lnr=" {{{frag}}} Vs. I {n}" lg="Hit" cu="&#x12000;"/>'
        f'<w trans="w{n}" mrp0sel=" 1 " mrp1="w=@x@@ N@">wa</w>'
    )


def _edge_values(api, feature: str, node):
    edge = getattr(api.E, feature, None)
    return {} if edge is None else dict(edge.f(node))


def _fragment(api, label: str):
    return next(n for n in api.F.otype.s("fragment") if api.F.fragment_label.v(n) == label)


def test_sibling_block_before_text_is_emitted_and_scopes_line_witness(tmp_path):
    api = _build(
        tmp_path,
        '<AO:Manuscripts><AO:TxtPubl nr="A1">outside</AO:TxtPubl></AO:Manuscripts>'
        '<text xml:lang="Hit">' + _line(1, "A1") + '</text>',
    )
    (frag,) = api.F.otype.s("fragment")
    (line,) = api.F.otype.s("line")
    assert api.F.fragment_label.v(frag) == "outside"
    assert api.F.manuscript_block.v(frag) == 1
    assert api.F.manuscript_block.v(line) == 1
    assert set(api.E.witness.f(line)) == {frag}


def test_two_preline_blocks_are_both_ledgered_but_only_later_block_witnesses(tmp_path):
    api = _build(
        tmp_path,
        '<AO:Manuscripts><AO:TxtPubl nr="A1">old</AO:TxtPubl></AO:Manuscripts>'
        '<text xml:lang="Hit">'
        '<AO:Manuscripts><AO:TxtPubl nr="A1">new</AO:TxtPubl></AO:Manuscripts>'
        + _line(1, "A1") + '</text>',
    )
    old = _fragment(api, "old")
    new = _fragment(api, "new")
    assert api.F.manuscript_block.v(old) == 1
    assert api.F.manuscript_block.v(new) == 2
    assert api.F.fragment_order.v(old) == api.F.fragment_order.v(new) == 1
    (line,) = api.F.otype.s("line")
    assert api.F.manuscript_block.v(line) == 2
    assert set(api.E.witness.f(line)) == {new}
    assert old not in api.E.witness.f(line)


def test_midstream_block_switch_changes_witness_scope_only_for_later_lines(tmp_path):
    api = _build(
        tmp_path,
        '<text xml:lang="Hit">'
        '<AO:Manuscripts><AO:TxtPubl nr="A1">first</AO:TxtPubl></AO:Manuscripts>'
        + _line(1, "A1") +
        '<AO:Manuscripts><AO:TxtPubl nr="A1">second</AO:TxtPubl></AO:Manuscripts>'
        + _line(2, "A1") + '</text>',
    )
    first = _fragment(api, "first")
    second = _fragment(api, "second")
    lines = api.F.otype.s("line")
    assert [api.F.manuscript_block.v(n) for n in lines] == [1, 2]
    assert set(api.E.witness.f(lines[0])) == {first}
    assert set(api.E.witness.f(lines[1])) == {second}


def test_block_local_join_order_and_projection_do_not_cross_blocks(tmp_path):
    api = _build(
        tmp_path,
        '<AO:Manuscripts>'
        '<AO:TxtPubl nr="A1">A</AO:TxtPubl><AO:DirectJoin/>'
        '<AO:TxtPubl nr="A2">B</AO:TxtPubl>'
        '</AO:Manuscripts>'
        '<text xml:lang="Hit">'
        '<AO:Manuscripts>'
        '<AO:TxtPubl nr="A1">C</AO:TxtPubl><AO:InDirectJoin/>'
        '<AO:TxtPubl nr="A2">D</AO:TxtPubl>'
        '</AO:Manuscripts>'
        + _line(1, "A1") + _line(2, "A2") + '</text>',
    )
    a, b = _fragment(api, "A"), _fragment(api, "B")
    c, d = _fragment(api, "C"), _fragment(api, "D")
    statements = api.F.otype.s("joinstmt")
    assert len(statements) == 2
    assert [(api.F.manuscript_block.v(s), api.F.join_order.v(s)) for s in statements] == [(1, 1), (2, 1)]
    assert _edge_values(api, "joined", a) == {b: "direct"}
    assert _edge_values(api, "joined", c) == {d: "indirect"}
    assert c not in _edge_values(api, "joined", a)
    assert d not in _edge_values(api, "joined", b)


def test_embedded_entry_chain_emits_distinct_fragment_occurrences(tmp_path):
    api = _build(
        tmp_path,
        '<text xml:lang="Hit">'
        '<AO:Manuscripts><AO:TxtPubl>A {A1} + B {A2}</AO:TxtPubl></AO:Manuscripts>'
        + _line(1, "A1") + _line(2, "A2") + '</text>',
    )
    frags = api.F.otype.s("fragment")
    assert [api.F.fragment_label.v(n) for n in frags] == ["A", "B"]
    assert [api.F.frag.v(n) for n in frags] == ["A1", "A2"]
    assert [api.F.manuscript_block.v(n) for n in frags] == [1, 1]
    (stmt,) = api.F.otype.s("joinstmt")
    assert api.F.manuscript_block.v(stmt) == 1
    assert api.F.join_kind.v(stmt) == "direct"
    assert _edge_values(api, "joined", frags[0]) == {frags[1]: "direct"}


def test_trailing_block_is_ledgered_without_retroactive_witness(tmp_path):
    api = _build(
        tmp_path,
        '<text xml:lang="Hit">'
        '<AO:Manuscripts><AO:TxtPubl nr="A1">before</AO:TxtPubl></AO:Manuscripts>'
        + _line(1, "A1") +
        '<AO:Manuscripts><AO:TxtPubl nr="A2">trailing</AO:TxtPubl></AO:Manuscripts>'
        '</text>',
    )
    before = _fragment(api, "before")
    trailing = _fragment(api, "trailing")
    (line,) = api.F.otype.s("line")
    assert api.F.manuscript_block.v(line) == 1
    assert set(api.E.witness.f(line)) == {before}
    assert trailing not in api.E.witness.f(line)
    assert api.F.manuscript_block.v(trailing) == 2


def test_spaced_euro_siglum_normalizes_consistently_for_witness_lookup(tmp_path):
    api = _build(
        tmp_path,
        '<text xml:lang="Hit">'
        '<AO:Manuscripts><AO:TxtPubl nr="€ 2">spaced</AO:TxtPubl></AO:Manuscripts>'
        + _line(1, "€ 2") + '</text>',
    )
    (frag,) = api.F.otype.s("fragment")
    (line,) = api.F.otype.s("line")
    assert api.F.frag.v(frag) == "€2"
    assert set(api.E.witness.f(line)) == {frag}
    assert _edge_values(api, "witness_resolution", line) == {frag: "unique"}
