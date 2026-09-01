"""Regression tests for the cross-release source-path research utilities."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import analyze_source_directories as asd
import analyze_source_paths as asp


def _xml(docid: str) -> bytes:
    return f"<AOxml><AOHeader><docID>{docid}</docID></AOHeader></AOxml>".encode()


def test_beta_02_top_level_grammar_has_no_project(tmp_path):
    wrapper = tmp_path / "TLHbasisONLINE25.1_ZENODO"
    source = wrapper / "CTH 241_XML" / "CTH 241.I_PTAC" / "KUB 1.1.xml"
    source.parent.mkdir(parents=True)
    source.write_bytes(_xml("KUB 1.1"))

    recs = asp.scan("Beta 0.2", tmp_path)
    assert len(recs) == 1
    rec = recs[0]
    assert rec.cth == "241"
    assert rec.project == ""
    assert rec.subdir == "CTH 241.I_PTAC"
    assert rec.rel == "CTH 241_XML/CTH 241.I_PTAC/KUB 1.1.xml"


def test_beta_03_top_level_grammar_carries_project(tmp_path):
    source = tmp_path / "CTH 18_XML_HAnn" / "KUB 26.71.xml"
    source.parent.mkdir(parents=True)
    source.write_bytes(_xml("KUB 26.71"))

    recs = asp.scan("Beta 0.3", tmp_path)
    assert len(recs) == 1
    rec = recs[0]
    assert rec.cth == "18"
    assert rec.project == "HAnn"
    assert rec.subdir == ""
    assert rec.rel == "CTH 18_XML_HAnn/KUB 26.71.xml"


def test_docid_is_recovered_even_from_otherwise_malformed_xml(tmp_path):
    source = tmp_path / "CTH 1_XML_TLH" / "KUB 1.1.xml"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"<AOxml><AOHeader><docID>KUB 1.1</docID></AOHeader><broken>")

    rec = asp.scan("Beta 0.3", tmp_path)[0]
    assert rec.docid == "KUB 1.1"


def test_macos_resource_fork_mirror_is_not_treated_as_a_second_corpus(tmp_path):
    real = tmp_path / "TLHbasisONLINE25.1_ZENODO" / "CTH 1_XML" / "KUB 1.1.xml"
    real.parent.mkdir(parents=True)
    real.write_bytes(_xml("KUB 1.1"))

    mirror = tmp_path / "__MACOSX" / "TLHbasisONLINE25.1_ZENODO" / "CTH 1_XML"
    mirror.mkdir(parents=True)
    (mirror / "._KUB 1.1.xml").write_bytes(b"resource fork metadata")

    recs = asp.scan("Beta 0.2", tmp_path)
    assert [r.rel for r in recs] == ["CTH 1_XML/KUB 1.1.xml"]


def test_directory_inventory_keeps_empty_classification_directories(tmp_path):
    root = tmp_path / "TLHbasisONLINE25.1_ZENODO"
    source = root / "CTH 241_XML" / "KUB 1.1.xml"
    source.parent.mkdir(parents=True)
    source.write_bytes(_xml("KUB 1.1"))
    (root / "CTH 241_XML" / "CTH 241.I_PTAC").mkdir()

    inv = asd.inventory(tmp_path)
    assert "CTH 241_XML/CTH 241.I_PTAC" in inv["nested_without_xml"]
    assert inv["suffixes"]["PTAC"] == 1
