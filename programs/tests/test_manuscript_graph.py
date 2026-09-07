"""Graph RED for issue #18.

These tests use the real Text-Fabric conversion harness.  The pure source parser is
already frozen by test_manuscripts.py + check_manuscripts_parser.py; this shard asserts
the graph contract from docs/plan-manuscript-joins.md before converter production code
is changed.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import convert


def _doc(manuscripts: str, line_fragments: tuple[str, ...] = ()) -> str:
    lines = []
    if not line_fragments:
        line_fragments = ("",)
    for i, frag in enumerate(line_fragments, 1):
        prefix = f" {{{frag}}}" if frag else ""
        lines.append(
            f'<lb txtid="GRAPH" lnr="{prefix} Vs. I {i}" lg="Hit" cu="&#x12000;"/>'
            f'<w trans="w{i}" mrp0sel=" 1 " mrp1="w=@x@@ N@">wa</w>'
        )
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<AOxml xmlns:AO="http://hethiter.net/ns/AO/1.0">
<AOHeader><docID>GRAPH</docID><meta><creation-date date="2026-01-01"/></meta></AOHeader>
<body><div1 type="transliteration"><text xml:lang="Hit">
<AO:Manuscripts>{manuscripts}</AO:Manuscripts>
{"".join(lines)}
</text></div1></body></AOxml>
'''


def _build(tmp_path, manuscripts: str, line_fragments: tuple[str, ...] = ()):
    src = tmp_path / "corpus" / "CTH 999_XML_TLH"
    src.mkdir(parents=True)
    (src / "GRAPH.xml").write_text(_doc(manuscripts, line_fragments), encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None, "conversion failed"
    return api


def _fragments_by_label(api):
    return {api.F.fragment_label.v(n): n for n in api.F.otype.s("fragment")}


def _edge_values(api, feature: str, node):
    """Normalize Text-Fabric's valued-edge tuple API for semantic assertions."""
    edge = getattr(api.E, feature, None)
    return {} if edge is None else dict(edge.f(node))


def _edge_targets(api, feature: str, node):
    """An edge feature is absent from a subset build when that fixture emits none."""
    edge = getattr(api.E, feature, None)
    return () if edge is None else edge.f(node)


def test_every_apparatus_entry_becomes_a_fragment_occurrence(tmp_path):
    api = _build(
        tmp_path,
        '<AO:TxtPubl nr="€1">KBo 1.1</AO:TxtPubl>'
        '<AO:InvNr>Bo 1234</AO:InvNr>'
        '<AO:TxtPubl>KUB 2.2</AO:TxtPubl>',
        ("€1",),
    )
    frags = api.F.otype.s("fragment")
    assert len(frags) == 3
    assert [api.F.fragment_order.v(n) for n in frags] == [1, 2, 3]
    assert [api.F.fragment_kind.v(n) for n in frags] == ["txtpubl", "invnr", "txtpubl"]
    assert [api.F.fragment_label.v(n) for n in frags] == ["KBo 1.1", "Bo 1234", "KUB 2.2"]


def test_unique_line_siglum_has_explicit_unique_witness_resolution(tmp_path):
    api = _build(
        tmp_path,
        '<AO:TxtPubl nr="€1">KBo 1.1</AO:TxtPubl>',
        ("€1",),
    )
    (line,) = api.F.otype.s("line")
    (frag,) = api.E.witness.f(line)
    resolution = _edge_values(api, "witness_resolution", line)
    assert resolution == {frag: "unique"}


def test_duplicate_siglum_preserves_both_fragments_and_marks_ambiguous_witness(tmp_path):
    api = _build(
        tmp_path,
        '<AO:TxtPubl nr="€1">KBo 1.1</AO:TxtPubl>'
        '<AO:TxtPubl nr="€1">KBo 1.1 duplicate</AO:TxtPubl>',
        ("€1",),
    )
    frags = api.F.otype.s("fragment")
    assert len(frags) == 2, "duplicate sigla must not overwrite entry occurrences"
    assert all(api.F.frag.v(n) == "€1" for n in frags)
    assert all(api.F.siglum_ambiguous.v(n) == 1 for n in frags)

    (line,) = api.F.otype.s("line")
    targets = set(api.E.witness.f(line))
    assert targets == set(frags)
    resolution = _edge_values(api, "witness_resolution", line)
    assert resolution == {n: "ambiguous" for n in frags}


def test_confident_direct_statement_has_ledger_endpoints_and_joined_edge(tmp_path):
    api = _build(
        tmp_path,
        '<AO:TxtPubl nr="€1">A</AO:TxtPubl>'
        '<AO:DirectJoin/>'
        '<AO:TxtPubl nr="€2">B</AO:TxtPubl>',
        ("€1", "€2"),
    )
    by_label = _fragments_by_label(api)
    a, b = by_label["A"], by_label["B"]
    (stmt,) = api.F.otype.s("joinstmt")
    assert api.F.join_kind.v(stmt) == "direct"
    assert api.F.join_encoding.v(stmt) == "xml"
    assert api.F.join_resolved.v(stmt) == 1
    assert set(api.E.joinLeft.f(stmt)) == {a}
    assert set(api.E.joinRight.f(stmt)) == {b}
    (doc,) = api.F.otype.s("document")
    assert set(api.E.joinDocument.f(stmt)) == {doc}
    assert _edge_values(api, "joined", a) == {b: "direct"}


def test_unresolved_targetless_statement_stays_queryable_without_joined_edge(tmp_path):
    api = _build(
        tmp_path,
        '<AO:TxtPubl nr="€1">A</AO:TxtPubl> +',
        ("€1",),
    )
    (stmt,) = api.F.otype.s("joinstmt")
    assert api.F.join_kind.v(stmt) == "direct"
    assert api.F.join_raw.v(stmt) == "+"
    assert api.F.join_resolved.v(stmt) == 0
    (doc,) = api.F.otype.s("document")
    assert set(api.E.joinDocument.f(stmt)) == {doc}
    assert not _edge_targets(api, "joinRight", stmt)
    (frag,) = api.F.otype.s("fragment")
    assert not _edge_values(api, "joined", frag)


def test_joined_edges_preserve_source_order_without_reverse_or_transitive_edges(tmp_path):
    api = _build(
        tmp_path,
        '<AO:TxtPubl nr="€1">A</AO:TxtPubl>'
        '<AO:DirectJoin/>'
        '<AO:TxtPubl nr="€2">B</AO:TxtPubl>'
        '<AO:DirectJoin/>'
        '<AO:TxtPubl nr="€3">C</AO:TxtPubl>',
        ("€1", "€2", "€3"),
    )
    n = _fragments_by_label(api)
    assert _edge_values(api, "joined", n["A"]) == {n["B"]: "direct"}
    assert _edge_values(api, "joined", n["B"]) == {n["C"]: "direct"}
    assert not _edge_values(api, "joined", n["C"])
    assert n["A"] not in _edge_values(api, "joined", n["B"])
    assert n["C"] not in _edge_values(api, "joined", n["A"]), "no transitive closure"


def test_duplicate_same_kind_statements_keep_two_ledger_nodes_but_one_joined_edge(tmp_path):
    api = _build(
        tmp_path,
        '<AO:TxtPubl nr="€1">A</AO:TxtPubl> + '
        '<AO:DirectJoin/>'
        '<AO:TxtPubl nr="€2">B</AO:TxtPubl>',
        ("€1", "€2"),
    )
    n = _fragments_by_label(api)
    statements = api.F.otype.s("joinstmt")
    assert len(statements) == 2
    assert {api.F.join_encoding.v(s) for s in statements} == {"textual", "xml"}
    assert all(api.F.join_kind.v(s) == "direct" for s in statements)
    assert _edge_values(api, "joined", n["A"]) == {n["B"]: "direct"}
