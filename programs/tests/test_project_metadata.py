"""TDD contract for source-path metadata on document nodes."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import convert


DOC = """<?xml version="1.0" encoding="UTF-8"?>
<AOxml xmlns:AO="http://hethiter.net/ns/AO/1.0">
<AOHeader><docID>{docid}</docID><meta/></AOHeader>
<body><div1 type="transliteration"><text xml:lang="Hit">
<lb txtid="{docid}" lnr="Vs. 1" lg="Hit" cu="𒉡"/><w trans="nu">nu</w>
</text></div1></body></AOxml>
"""


def _build(tmp_path, rel: str):
    root = tmp_path / "corpus"
    path = root / rel
    path.parent.mkdir(parents=True)
    path.write_text(DOC.format(docid=path.stem), encoding="utf8")
    api = convert.build(root, tmp_path / "tf")
    assert api is not None
    return api


def _document(api):
    docs = api.F.otype.s("document")
    assert len(docs) == 1
    return docs[0]


def test_converter_emits_canonical_project_metadata_and_legacy_alias(tmp_path):
    rel = "CTH 101_XML_TLH/KUB 21.8.xml"
    api = _build(tmp_path, rel)
    d = _document(api)

    assert api.F.docid.v(d) == "KUB 21.8"
    assert api.F.lang.v(d) == "Hit"
    assert api.F.src_file.v(d) == rel
    assert api.F.cth.v(d) == "101"
    assert api.F.project.v(d) == "TLH"
    assert api.F.subcorpus.v(d) == api.F.project.v(d) == "TLH"
    assert api.F.source_subdir.v(d) == ""
    assert api.F.source_stem.v(d) == "KUB 21.8"
    assert not (tmp_path / "tf" / "project_name.tf").exists()


def test_converter_preserves_nested_source_directory_without_reinterpreting_it(tmp_path):
    rel = "CTH 670_XML_HFR/CTH 670-0076-0100/11_c.xml"
    api = _build(tmp_path, rel)
    d = _document(api)

    assert api.F.project.v(d) == "HFR"
    assert api.F.subcorpus.v(d) == "HFR"
    assert api.F.source_subdir.v(d) == "CTH 670-0076-0100"
    assert api.F.source_stem.v(d) == "11_c"


def test_converter_rejects_unparseable_source_path_instead_of_blank_metadata(tmp_path):
    root = tmp_path / "corpus"
    path = root / "CTH 473_XM" / "KBo 27.130.xml"
    path.parent.mkdir(parents=True)
    path.write_text(DOC.format(docid="KBo 27.130"), encoding="utf8")

    with pytest.raises(ValueError, match="invalid_top_directory"):
        convert.build(root, tmp_path / "tf")
