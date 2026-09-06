"""Additional RED for source-faithful siglum provenance in issue #18.

The frozen design requires a normalized lookup siglum and the source spelling used to
recover it.  These tests close the remaining gap before release integration.
"""
from __future__ import annotations

from lxml import etree as ET

from tlhdig import manuscripts

AO = "http://hethiter.net/ns/AO/1.0"


def parse(inner: str):
    root = ET.fromstring(
        f'<text xmlns:AO="{AO}"><AO:Manuscripts>{inner}</AO:Manuscripts></text>'.encode()
    )
    return manuscripts.parse(root[0])


def test_raw_attribute_siglum_survives_normalization():
    got = parse('<AO:TxtPubl nr="  €1  ">KBo 1.1</AO:TxtPubl>')
    entry = got.entries[0]
    assert entry.siglum == "€1"
    assert entry.siglum_source == "attr"
    assert entry.siglum_raw == "  €1  "
    assert entry.siglum_raw_candidates == ("  €1  ",)


def test_raw_tail_siglum_keeps_source_braces():
    got = parse(
        '<AO:InvNr>Bo 123</AO:InvNr> { €2 } + '
        '<AO:TxtPubl nr="€3">KUB 2.2</AO:TxtPubl>'
    )
    entry = got.entries[0]
    assert entry.siglum == "€2"
    assert entry.siglum_source == "tail"
    assert entry.siglum_raw == "{ €2 }"
    assert entry.siglum_raw_candidates == ("{ €2 }",)


def test_conflicting_siglum_sources_preserve_both_raw_spellings_without_choice():
    got = parse(
        '<AO:TxtPubl nr="€1">A</AO:TxtPubl> { €2 } + '
        '<AO:TxtPubl nr="€3">B</AO:TxtPubl>'
    )
    entry = got.entries[0]
    assert entry.siglum == ""
    assert entry.siglum_source == "conflict"
    assert entry.siglum_raw == ""
    assert entry.siglum_candidates == ("€1", "€2")
    assert entry.siglum_raw_candidates == ("€1", "{ €2 }")
