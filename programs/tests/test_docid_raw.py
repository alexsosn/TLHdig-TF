"""Phase 4 TDD contract for source-derived ``docid_raw`` (issue #10).

These tests intentionally precede the converter change. ``docid`` remains the normalized
section/grouping identifier; ``docid_raw`` must become the parsed source text before
normalization or filename fallback.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import convert


def xml(header: str, txtid: str = "KUB 21.8") -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<AOxml xmlns:AO="http://hethiter.net/ns/AO/1.0">
<AOHeader>{header}<meta/></AOHeader>
<body><div1 type="transliteration"><text xml:lang="Hit">
<AO:Manuscripts><AO:TxtPubl>{txtid}</AO:TxtPubl></AO:Manuscripts>
<lb txtid="{txtid}" lnr="Vs. I 1" lg="Hit" cu="&#x12000;"/>
<w trans="x">x</w>
</text></div1></body></AOxml>
'''


def build_one(tmp_path, header: str, filename: str = "KUB 21.8.xml"):
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / filename).write_text(xml(header), encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None
    docs = api.F.otype.s("document")
    assert len(docs) == 1
    return api, docs[0]


def test_docid_raw_preserves_trailing_space_while_docid_stays_normalized(tmp_path):
    api, doc = build_one(tmp_path, "<docID>KBo 50.89 </docID>", "KBo 50.89 .xml")
    assert api.F.docid.v(doc) == "KBo 50.89"
    assert api.F.docid_raw.v(doc) == "KBo 50.89 "


def test_docid_raw_preserves_leading_and_trailing_space(tmp_path):
    api, doc = build_one(tmp_path, "<docID>  KUB 21.8 </docID>")
    assert api.F.docid.v(doc) == "KUB 21.8"
    assert api.F.docid_raw.v(doc) == "  KUB 21.8 "


def test_missing_docid_keeps_filename_fallback_but_omits_docid_raw(tmp_path):
    api, doc = build_one(tmp_path, "", "Fallback Name.xml")
    assert api.F.docid.v(doc) == "Fallback Name"
    # Text-Fabric omits a node feature entirely when no node in the tiny dataset has
    # any value for it. That is the expected serialization of a missing source value.
    assert not hasattr(api.F, "docid_raw")


def test_empty_docid_keeps_filename_fallback_but_omits_docid_raw(tmp_path):
    api, doc = build_one(tmp_path, "<docID/>", "Fallback Name.xml")
    assert api.F.docid.v(doc) == "Fallback Name"
    assert not hasattr(api.F, "docid_raw")


def test_whitespace_only_docid_preserves_existing_docid_behavior_and_raw_text(tmp_path):
    api, doc = build_one(tmp_path, "<docID>  </docID>", "Fallback Name.xml")
    # The existing expression treats a non-empty whitespace string as truthy and then
    # strips it to empty. This oddity is explicitly out of scope for issue #10.
    assert api.F.docid.v(doc) == ""
    assert api.F.docid_raw.v(doc) == "  "


def test_duplicate_grouping_remains_keyed_by_normalized_docid(tmp_path):
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "one.xml").write_text(xml("<docID> KUB 1 </docID>", "KUB 1"), encoding="utf8")
    (src / "two.xml").write_text(xml("<docID>KUB 1</docID>", "KUB 1"), encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None

    docs = api.F.otype.s("document")
    assert len(docs) == 2
    assert {api.F.docid.v(d) for d in docs} == {"KUB 1"}
    groups = api.F.otype.s("docgroup")
    assert len(groups) == 1
    assert api.F.docid.v(groups[0]) == "KUB 1"
    assert set(api.E.edition.f(d)[0] for d in docs) == {groups[0]}
