"""RED for unresolved manuscript source-reference preservation (issue #18)."""
from __future__ import annotations

import sys
from pathlib import Path

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import convert, manuscripts

AO = "http://hethiter.net/ns/AO/1.0"


def test_targetless_status_parser_preserves_reference_without_inventing_endpoint():
    root = ET.fromstring(
        f'<text xmlns:AO="{AO}"><AO:Manuscripts>KBo 31.5++</AO:Manuscripts></text>'.encode()
    )
    apparatus = manuscripts.parse(root[0])
    assert apparatus.entries == ()
    assert len(apparatus.statements) == 1
    statement = apparatus.statements[0]
    assert statement.kind == "direct-multi"
    assert statement.raw == "++"
    assert statement.left is None and statement.right is None
    assert statement.resolved is False
    assert statement.context == "KBo 31.5"


def test_spaced_targetless_status_preserves_reference_context():
    # Real production shapes: CTH 580 / KBo 24.129+.xml and
    # CTH 790 / KBo 33.116+.xml. The whitespace-delimited trailing plus is a
    # status marker, not a binary relation: there is no serialized fragment entry.
    root = ET.fromstring(
        f'<text xmlns:AO="{AO}"><AO:Manuscripts>KBo 24.129 +</AO:Manuscripts></text>'.encode()
    )
    apparatus = manuscripts.parse(root[0])
    assert apparatus.entries == ()
    assert len(apparatus.statements) == 1
    statement = apparatus.statements[0]
    assert statement.kind == "direct"
    assert statement.raw == "+"
    assert statement.left is None and statement.right is None
    assert statement.resolved is False
    assert statement.context == "KBo 24.129"


def test_siglum_bearing_fragment_plus_is_not_reclassified_as_status_context():
    # A serialized fragment occurrence remains an endpoint even when the opposite
    # endpoint is absent. The status shortcut is only for targetless block text.
    root = ET.fromstring(
        f'<text xmlns:AO="{AO}"><AO:Manuscripts>KBo 1.1 {{€1}} +</AO:Manuscripts></text>'.encode()
    )
    apparatus = manuscripts.parse(root[0])
    assert [(entry.label, entry.siglum) for entry in apparatus.entries] == [("KBo 1.1", "€1")]
    assert len(apparatus.statements) == 1
    statement = apparatus.statements[0]
    assert statement.kind == "direct"
    assert statement.left == 1 and statement.right is None
    assert statement.resolved is False
    assert statement.context == ""


def _source() -> str:
    return '''<?xml version="1.0" encoding="UTF-8"?>
<AOxml xmlns:AO="http://hethiter.net/ns/AO/1.0">
<AOHeader><docID>GRAPH+</docID><meta><creation-date date="2026-01-01"/></meta></AOHeader>
<body><div1 type="transliteration"><text xml:lang="Hit">
<AO:Manuscripts>KBo 31.5++</AO:Manuscripts>
<lb txtid="GRAPH+" lnr="Vs. I 1" lg="Hit" cu="&#x12000;"/>
<w trans="wa" mrp0sel=" 1 " mrp1="wa=@x@@ N@">wa</w>
</text></div1></body></AOxml>
'''


def test_targetless_status_graph_keeps_reference_on_joinstmt_only(tmp_path):
    src = tmp_path / "corpus" / "CTH 999_XML_TLH"
    src.mkdir(parents=True)
    (src / "GRAPH.xml").write_text(_source(), encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None

    assert api.F.otype.s("fragment") == ()
    (stmt,) = api.F.otype.s("joinstmt")
    assert api.F.join_kind.v(stmt) == "direct-multi"
    assert api.F.join_raw.v(stmt) == "++"
    assert api.F.join_resolved.v(stmt) == 0
    assert api.F.join_context.v(stmt) == "KBo 31.5"
    assert not getattr(api.E, "joinLeft", None) or not api.E.joinLeft.f(stmt)
    assert not getattr(api.E, "joinRight", None) or not api.E.joinRight.f(stmt)
    assert getattr(api.E, "joined", None) is None
