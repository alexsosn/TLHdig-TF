"""TDD contract for byte-exact document AOHeader provenance (#57/#58/#10).

This file is committed before production changes. The Text-Fabric escaping regression is
expected to pass immediately; the header extraction/emission/Contract-A assertions are
expected RED on the pre-feature converter.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_contract_a_graph
from tlhdig import convert, repair, source


XML = b'''<?xml version="1.0" encoding="UTF-8"?>
<AOxml xmlns:AO="http://hethiter.net/ns/AO/1.0">
<AOHeader><docID>KUB 21.8 </docID><meta><annot editor="AB" data="opaque"/></meta></AOHeader>
<body><div1 type="transliteration"><text xml:lang="Hit">
<lb txtid="KUB 21.8" lnr="Vs. 1" lg="Hit" cu="\xf0\x92\x89\xa1"/><w trans="nu">nu</w>
</text></div1></body></AOxml>
'''


def _header_helper():
    helper = getattr(convert, "_header_provenance", None)
    assert callable(helper), "converter has no document-header provenance extractor"
    return helper


def _header_bytes(data: bytes) -> bytes:
    a = data.index(b"<AOHeader")
    b = data.index(b"</AOHeader>", a) + len(b"</AOHeader>")
    return data[a:b]


def test_header_provenance_extracts_exact_original_outer_element():
    helper = _header_helper()
    span, text = helper(source.scan(XML), XML, None, "fixture.xml")
    chunk = _header_bytes(XML)
    a = XML.index(chunk)
    assert span == f"{a}-{a + len(chunk)}"
    assert text == chunk.decode("utf8", "surrogateescape")


def test_header_provenance_maps_length_changing_repair_before_header_to_original():
    original = XML.replace(b"<AOxml ", b"<AOxml  ", 1)
    patch = repair.Patch(b"<AOxml  ", b"<AOxml ", "fixture length repair before header")
    omap = repair.OffsetMap(original, [patch])
    repaired = repair.apply(original, [patch])

    helper = _header_helper()
    span, text = helper(source.scan(repaired), original, omap, "fixture.xml")
    chunk = _header_bytes(original)
    a = original.index(chunk)
    assert span == f"{a}-{a + len(chunk)}"
    assert text == chunk.decode("utf8", "surrogateescape")


def test_header_provenance_keeps_original_bytes_when_repair_changes_header_content():
    original = XML.replace(b"KUB 21.8 ", b"KUB  21.8 ", 1)
    patch = repair.Patch(b"KUB  21.8 ", b"KUB 21.8 ", "fixture repair inside header")
    omap = repair.OffsetMap(original, [patch])
    repaired = repair.apply(original, [patch])

    helper = _header_helper()
    span, text = helper(source.scan(repaired), original, omap, "fixture.xml")
    chunk = _header_bytes(original)
    assert text == chunk.decode("utf8", "surrogateescape")
    assert "KUB  21.8 " in text
    a = original.index(chunk)
    assert span == f"{a}-{a + len(chunk)}"


def test_header_provenance_fails_closed_on_missing_or_duplicate_depth1_header():
    helper = _header_helper()
    missing = b"<AOxml><body><div1><text><w>x</w></text></div1></body></AOxml>"
    duplicate = (
        b"<AOxml><AOHeader><docID>A</docID></AOHeader>"
        b"<AOHeader><docID>B</docID></AOHeader>"
        b"<body><div1><text><w>x</w></text></div1></body></AOxml>"
    )
    with pytest.raises(ValueError, match="AOHeader"):
        helper(source.scan(missing), missing, None, "missing.xml")
    with pytest.raises(ValueError, match="AOHeader"):
        helper(source.scan(duplicate), duplicate, None, "duplicate.xml")


def test_header_provenance_rejects_mapped_span_outside_original_bytes():
    helper = _header_helper()
    fake = [
        SimpleNamespace(
            tag="AOHeader", depth=1, outer_start=len(XML) + 10, outer_end=len(XML) + 20
        )
    ]
    with pytest.raises(ValueError, match="span|AOHeader"):
        helper(fake, XML, None, "outside.xml")


def test_converter_emits_document_header_provenance_and_retires_docid_raw(tmp_path):
    root = tmp_path / "corpus"
    path = root / "CTH 101_XML_TLH" / "KUB 21.8.xml"
    path.parent.mkdir(parents=True)
    path.write_bytes(XML)

    api = convert.build(root, tmp_path / "tf")
    assert api is not None
    docs = api.F.otype.s("document")
    assert len(docs) == 1
    doc = docs[0]

    # Normalized identity remains core/queryable.
    assert api.F.docid.v(doc) == "KUB 21.8"

    # Exact raw header moves to optional-provenance feature semantics.
    expected = _header_bytes(XML).decode("utf8", "surrogateescape")
    assert api.F.srcxml.v(doc) == expected
    span = api.F.src_span.v(doc)
    a, b = (int(x) for x in span.split("-", 1))
    assert XML[a:b].decode("utf8", "surrogateescape") == expected

    # The bespoke duplicate is gone from the new schema.
    assert not (tmp_path / "tf" / "docid_raw.tf").exists()


def test_text_fabric_round_trips_multiline_tab_and_backslash_feature(tmp_path):
    """Dependency proof: pinned TF writer/loader preserves a whole-header-like string."""
    from tf.convert.walker import CV
    from tf.fabric import Fabric

    value = "<AOHeader>\n\t<docID>A\\B</docID>\n</AOHeader>"
    out = tmp_path / "escape-tf"
    TF = Fabric(locations=str(out), silent="deep")
    cv = CV(TF, silent="deep")

    def director(cv_):
        doc = cv_.node("document")
        slot = cv_.slot()
        cv_.feature(doc, srcxml=value, docid="A")
        cv_.feature(slot, sym="x")
        cv_.terminate(doc)

    good = cv.walk(
        director,
        "sign",
        otext={
            "fmt:text-orig-full": "{sym}",
            "sectionTypes": "document",
            "sectionFeatures": "docid",
        },
        generic={"name": "header-escape-regression"},
        intFeatures=set(),
        featureMeta={
            "srcxml": {"description": "source xml"},
            "docid": {"description": "document id"},
            "sym": {"description": "sign"},
        },
        warn=False,
    )
    assert good
    TF2 = Fabric(locations=str(out), silent="deep")
    api = TF2.load("otype srcxml", silent="deep")
    assert api is not False and api is not None
    doc = api.F.otype.s("document")[0]
    assert api.F.srcxml.v(doc) == value


def test_contract_a_exposes_strict_document_header_source_verifier():
    verify = getattr(check_contract_a_graph, "verify_document_header", None)
    assert callable(verify), "Contract A has no document-header graph/source verifier"

    chunk = _header_bytes(XML)
    a = XML.index(chunk)
    span = f"{a}-{a + len(chunk)}"
    text = chunk.decode("utf8", "surrogateescape")
    assert verify(XML, span, text) == []

    assert verify(XML, None, text)
    assert verify(XML, span, None)
    assert verify(XML, "not-a-span", text)
    assert verify(XML, "0-999999", text)
    assert verify(XML, span, text + "x")

    body_a = XML.index(b"<body")
    body_b = XML.index(b"</body>") + len(b"</body>")
    assert verify(XML, f"{body_a}-{body_b}", XML[body_a:body_b].decode())
