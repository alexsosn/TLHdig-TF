"""Contract B must cover AOHeader elements and attributes, not only body markup."""
import sys
from pathlib import Path

import lxml.etree as LE

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_tags
from tlhdig import tags


DOC = b"""<AOxml>
  <AOHeader>
    <docID>KBo 1.1</docID>
    <meta>
      <annotation><annot editor="AB" data="opaque"/></annotation>
      <kor date="2026-01-01"/>
      <mDocID>KBo 2.2</mDocID>
    </meta>
  </AOHeader>
  <body><div1><text><lb lnr="1"/><w>nu</w></text></div1></body>
</AOxml>"""


def test_unknown_header_element_is_reported():
    assert tags.header_undeclared(["AOHeader", "docID", "FutureHeaderThing"]) == [
        "FutureHeaderThing"
    ]


def test_unknown_header_attribute_is_element_qualified():
    assert tags.header_attrs_undeclared(
        [("annot", "editor"), ("annot", "future")]
    ) == [("annot", "future")]


def test_current_dropped_header_data_is_not_called_raw_or_preserved():
    assert tags.HEADER_DESTINATION["mDocID"] == "known-unpreserved"
    assert tags.HEADER_ATTR_DESTINATION[("annot", "data")] == "known-unpreserved"
    assert "raw" not in tags.HEADER_KINDS


def test_converter_edit_contract_is_canonical_in_tags_module():
    assert "annot" in tags.EDIT_KINDS
    assert "kor" in tags.EDIT_KINDS
    assert tags.EDIT_ATTRS == (
        "editor", "date", "part", "src", "frgm", "docs", "comment",
        "author", "alt", "neu",
    )


def test_inventory_keeps_body_header_and_header_attrs_separate():
    root = LE.fromstring(DOC)
    inv = check_tags.inventory_root(root)
    assert inv.body_elements["text"] == 1
    assert inv.body_elements["w"] == 1
    assert inv.header_elements["AOHeader"] == 1
    assert inv.header_elements["annot"] == 1
    assert inv.header_elements["mDocID"] == 1
    assert inv.header_attrs[("annot", "editor")] == 1
    assert inv.header_attrs[("annot", "data")] == 1
    assert ("lb", "lnr") not in inv.header_attrs


def test_new_attribute_on_known_header_element_fails_declaration_check():
    root = LE.fromstring(
        DOC.replace(b'editor="AB"', b'editor="AB" future="x"')
    )
    inv = check_tags.inventory_root(root)
    assert tags.header_attrs_undeclared(inv.header_attrs) == [("annot", "future")]


def test_report_visibly_separates_header_loss_from_body_raw():
    root = LE.fromstring(DOC)
    report = check_tags.render_report(check_tags.inventory_root(root))
    assert "## Body `<text>` element inventory" in report
    assert "## `AOHeader` element inventory" in report
    assert "## `AOHeader` attribute inventory" in report
    assert "known-unpreserved" in report
    assert "does not mean preserved" in report
