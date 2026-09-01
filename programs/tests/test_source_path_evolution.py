"""Regression tests for the cross-release source-path research utility."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
