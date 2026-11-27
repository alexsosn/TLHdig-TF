"""New Beta 0.4 editorial constructs must remain queryable without becoming signs."""
from pathlib import Path
import sys
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tlhdig import convert, repair, structure, tags
from tlhdig.paths import CORPUS, PATCHES

def test_new_header_and_body_declarations():
    assert tags.DESTINATION["LineNrExpl"] == "structure"
    assert tags.HEADER_DESTINATION["Colon"] == "edit"
    for pair in (("Colon","editor"),("Colon","date"),("join","comment"),
                 ("kolfot","comment"),("koltaf","comment"),("kor2","comment"),
                 ("val","comment")):
        assert tags.HEADER_ATTR_DESTINATION[pair] == "edit"


def test_editorial_explanations_are_not_readings_or_footnotes(tmp_path):
    root = tmp_path / "corpus" / "CTH 999_XML_TLH"
    root.mkdir(parents=True)
    raw = b'''<AOxml xmlns:AO="http://hethiter.net/ns/AO/1.0">
<AOHeader><docID>editorial</docID><meta><Colon editor="AB" date="2024-01-01"/>
<join editor="AB" comment="keep me"/></meta></AOHeader>
<body><div1><text xml:lang="Hit"><AO:Manuscripts><AO:TxtPubl>editorial</AO:TxtPubl></AO:Manuscripts>
<P___Standard><AO:LineNrExpl> "obv." </AO:LineNrExpl></P___Standard>
<lb lnr="Vs. I 1"/><w>a</w><AO:LineNrExpl>m<del_in/></AO:LineNrExpl><w>b<del_fin/></w>
<AO:LineNrExpl><laes_fin/></AO:LineNrExpl></text></div1></body></AOxml>'''
    (root/"editorial.xml").write_bytes(raw)
    api = convert.build(root.parent,tmp_path/"tf")
    assert api
    F = api.F
    nodes = sorted(F.otype.s("lineexpl"),key=F.order.v)
    assert len(nodes) == structure.count_document(raw)["lineexpl"] == 3
    assert [F.line_explanation.v(n) or "" for n in nodes] == [' "obv." ', "m", ""]
    assert [F.sym.v(s) for s in F.otype.s("sign") if not getattr(F,"anchor",None) or not F.anchor.v(s)] == ["a","b"]
    for node in nodes:
        a,b = map(int,F.src_span.v(node).split("-"))
        assert raw[a:b].startswith(b"<AO:LineNrExpl>")
        assert raw[a:b].endswith(b"</AO:LineNrExpl>")
    edits = {F.kind.v(n):n for n in F.otype.s("edit")}
    assert F.editor.v(edits["Colon"]) == "AB"
    assert F.date.v(edits["Colon"]) == "2024-01-01"
    assert F.comment.v(edits["join"]) == "keep me"


def test_real_beta04_line_explanation_nodes_and_markers(tmp_path):
    names = ("CTH 562_XML_HDivT/KBo 48.25.xml",
             "CTH 570_XML_HDivT/KUB 50.123.xml")
    manifest = repair.read_manifest(PATCHES)
    ledger = convert.Ledger()
    out = tmp_path/"tf"
    assert convert.build(CORPUS,out,files=[CORPUS/n for n in names],
                         patches=manifest,ledger=ledger,load=False)
    assert ledger.converted == 2
    assert ledger.marker_src == ledger.marker_fed == ledger.marker_out
    assert structure.graph_counts(out)["lineexpl"] == 7
    from tf.fabric import Fabric
    api = Fabric(locations=str(out),silent="deep").load("otype oslots src_file line_explanation order",silent="deep")
    assert api
    for doc in api.F.otype.s("document"):
        rel = api.F.src_file.v(doc)
        raw = (CORPUS/rel).read_bytes()
        if rel in manifest:
            sha, patches = manifest[rel]
            raw = repair.apply(raw,patches,expect_sha=sha)
        expected = ["".join(el.itertext()) for el in etree.fromstring(raw).xpath("//*[local-name()='LineNrExpl']")]
        nodes = sorted(api.L.d(doc,otype="lineexpl"),key=api.F.order.v)
        assert [api.F.line_explanation.v(n) or "" for n in nodes] == expected
