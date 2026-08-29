"""The CV director (plan §7.7).

Builds a tiny TF dataset from synthetic AOxml and checks the graph shape: node types,
section addressing, analyses as nodes rather than edges, and the empty-token policy.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import convert

DOC = """<?xml version="1.0" encoding="UTF-8"?>
<AOxml xmlns:AO="http://hethiter.net/ns/AO/1.0">
<AOHeader><docID>KUB 21.8</docID><meta>
  <creation-date date="2024-12-30T23:01:04"/>
  <kor2 editor="BK" date="2025-01-31T22:33:48"/>
</meta></AOHeader>
<body><div1 type="transliteration"><text xml:lang="Hit">
<AO:Manuscripts><AO:TxtPubl>KUB 21.8</AO:TxtPubl></AO:Manuscripts>
<lb txtid="KUB 21.8" lnr="Vs. II 1&#8242;" lg="Hit" cu="&#x12079;&#x1212F;"/>
<w><space c="7"/></w>
<w trans="pait" mrp0sel=" 1 " mrp1="pai-/p&#257;-@gehen@3SG.PST@I.11@">pa-it</w>
<w trans="nuza" mrp0sel=" 1 " mrp1="nu=z@@ CONNn=REFL@@ ">nu-za</w>
<parsep/>
<lb txtid="KUB 21.8" lnr="Vs. II 2&#8242;" lg="Hit" cu="&#x12000;"/>
<w trans="kat" mrp0sel=" " mrp1="katta@unten@@ ADV@" mrp2="katta@unter@@ POSP@">ka-at</w>
</text></div1></body></AOxml>
"""


def build(tmp_path, **kw):
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(DOC, encoding="utf8")
    out = tmp_path / "tf"
    api = convert.build(src.parent, out, **kw)
    assert api is not None, "conversion failed"
    return api


def test_node_types_present(tmp_path):
    api = build(tmp_path)
    types = set(api.F.otype.all)
    for t in ("sign", "word", "analysis", "line", "column", "surface", "document"):
        assert t in types, t
    assert api.F.otype.slotType == "sign"


def test_words_and_signs(tmp_path):
    api = build(tmp_path)
    words = [api.F.trans.v(w) for w in api.F.otype.s("word")]
    assert "pait" in words and "nuza" in words
    n = api.L.d(api.F.otype.s("word")[0], otype="sign")
    assert len(n) >= 1


def test_analyses_are_nodes_not_edges(tmp_path):
    """A word with two candidate lemmas must keep both (plan §3.4)."""
    api = build(tmp_path)
    kat = next(w for w in api.F.otype.s("word") if api.F.trans.v(w) == "kat")
    got = api.E.analyses.f(kat)
    assert len(got) == 2
    lemmas = sorted(api.F.lemma.v(a) for a in got)
    assert lemmas == ["katta", "katta"]
    assert sorted(api.F.pos.v(a) for a in got) == ["ADV", "POSP"]


def test_analysis_index_is_the_attribute_number(tmp_path):
    api = build(tmp_path)
    kat = next(w for w in api.F.otype.s("word") if api.F.trans.v(w) == "kat")
    assert sorted(api.F.index.v(a) for a in api.E.analyses.f(kat)) == [1, 2]


def test_section_addressing(tmp_path):
    api = build(tmp_path)
    n = api.T.nodeFromSection(("KUB 21.8", "Vs. II", "1′"))
    assert n is not None
    assert api.T.sectionFromNode(n)[0] == "KUB 21.8"


def test_line_carries_cuneiform(tmp_path):
    api = build(tmp_path)
    lines = api.F.otype.s("line")
    assert any(api.F.cu.v(ln) for ln in lines)


def test_document_features(tmp_path):
    api = build(tmp_path)
    d = api.F.otype.s("document")[0]
    assert api.F.docid.v(d) == "KUB 21.8"
    assert api.F.cth.v(d) == "101"
    assert api.F.subcorpus.v(d) == "TLH"
    assert api.F.lang.v(d) == "Hit"


def test_edit_events_become_nodes(tmp_path):
    api = build(tmp_path)
    edits = api.F.otype.s("edit")
    kinds = {api.F.kind.v(e) for e in edits}
    assert "kor2" in kinds
    e = next(x for x in edits if api.F.kind.v(x) == "kor2")
    assert api.F.editor.v(e) == "BK"


def test_empty_tokens_excluded_by_default(tmp_path):
    """Default policy: contentless tokens are not slots (plan §2.2)."""
    api = build(tmp_path)
    assert all(api.F.type.v(s) != "empty" for s in api.F.otype.s("sign"))


def test_empty_tokens_included_when_asked(tmp_path):
    api = build(tmp_path, keep_empty=True)
    assert any(api.F.type.v(s) == "empty" for s in api.F.otype.s("sign"))


DOC_LAYOUT = DOC.replace(
    '<w><space c="7"/></w>',
    '<w><space c="7"/></w>\n<w><del_in/></w>',
)


def build_layout(tmp_path, **kw):
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(DOC_LAYOUT, encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf", **kw)
    assert api is not None
    return api


def test_contentless_words_become_layout_nodes(tmp_path):
    """Excluding empty tokens must not delete the <w> itself (plan §2.2).

    A contentless <w> carries layout and damage markers; dropping it would break
    Contract B while claiming nothing is lost.
    """
    api = build_layout(tmp_path)
    layouts = api.F.otype.s("layout")
    assert len(layouts) == 2
    assert any(api.F.space_count.v(n) == 7 for n in layouts)


def test_layout_nodes_are_not_signs(tmp_path):
    api = build_layout(tmp_path)
    assert all(api.F.type.v(s) != "empty" for s in api.F.otype.s("sign"))
    assert "layout" in set(api.F.otype.all)
