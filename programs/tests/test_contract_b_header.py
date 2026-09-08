"""Contract B must cover AOHeader elements and attributes, not only body markup."""
import sys
from pathlib import Path

import lxml.etree as LE

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_tags
from tlhdig import convert, tags


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
    assert tags.HEADER_DESTINATION["ann"] == "malformed-unpreserved"
    for attr in ("date", "editor", "part"):
        assert tags.HEADER_ATTR_DESTINATION[("ann", attr)] == "malformed-unpreserved"
    assert "raw" not in tags.HEADER_KINDS


def test_observed_header_attribute_snapshot_is_exact_and_closed():
    assert len(tags.HEADER_ATTR_DESTINATION) == 73
    assert tags.header_attrs_undeclared(tags.HEADER_ATTR_DESTINATION) == []
    assert tags.header_attrs_undeclared([("annot", "new-field")]) == [
        ("annot", "new-field")
    ]


def test_converter_edit_contract_cannot_drift_from_contract_b():
    assert convert._EDIT_KINDS == tags.EDIT_KINDS
    assert convert._EDIT_ATTRS == tags.EDIT_ATTRS


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


def test_namespaced_header_attribute_cannot_masquerade_as_declared_local_name():
    root = LE.fromstring(
        DOC.replace(
            b'<AOxml>', b'<AOxml xmlns:x="urn:future">'
        ).replace(
            b'data="opaque"', b'data="opaque" x:data="different-semantics"'
        )
    )
    inv = check_tags.inventory_root(root)
    assert ("annot", "{urn:future}data") in inv.header_attrs
    assert tags.header_attrs_undeclared(inv.header_attrs) == [
        ("annot", "{urn:future}data")
    ]


def test_namespaced_header_element_cannot_masquerade_as_declared_local_name():
    root = LE.fromstring(
        DOC.replace(
            b'<AOxml>', b'<AOxml xmlns:x="urn:future">'
        ).replace(
            b'<kor date="2026-01-01"/>', b'<x:kor date="2026-01-01"/>'
        )
    )
    inv = check_tags.inventory_root(root)
    assert "{urn:future}kor" in inv.header_elements
    assert tags.header_undeclared(inv.header_elements) == ["{urn:future}kor"]


def test_declaration_drift_reports_missing_and_speculative_entries():
    missing, extra = check_tags.declaration_drift(
        observed={"AOHeader", "docID", "FutureHeaderThing"},
        declared={"AOHeader", "docID", "NeverObserved"},
    )
    assert missing == ["FutureHeaderThing"]
    assert extra == ["NeverObserved"]


def test_second_header_block_cannot_hide_undeclared_metadata():
    root = LE.fromstring(
        DOC.replace(
            b"</AOHeader>",
            b"</AOHeader><AOHeader><FutureHeaderThing secret=\"x\"/></AOHeader>",
            1,
        )
    )
    inv = check_tags.inventory_root(root)
    assert inv.header_elements["AOHeader"] == 2
    assert inv.header_elements["FutureHeaderThing"] == 1
    assert inv.header_attrs[("FutureHeaderThing", "secret")] == 1
    assert tags.header_undeclared(inv.header_elements) == ["FutureHeaderThing"]


def test_duplicate_header_with_only_known_fields_is_structural_failure():
    root = LE.fromstring(
        DOC.replace(
            b"</AOHeader>",
            b"</AOHeader><AOHeader><docID>KBo 9.9</docID></AOHeader>",
            1,
        )
    )
    assert check_tags.header_structure_problems(root) == [
        "expected exactly one direct AOHeader, found 2"
    ]


def test_docid_must_be_direct_child_of_the_single_header():
    root = LE.fromstring(b"""<AOxml>
      <AOHeader><meta><docID>KBo 1.1</docID></meta></AOHeader>
      <body><div1><text><w>nu</w></text></div1></body>
    </AOxml>""")
    assert check_tags.header_structure_problems(root) == [
        "expected exactly one direct AOHeader/docID, found 0",
        "misplaced docID outside direct AOHeader/docID path",
    ]


def test_known_edit_event_outside_direct_meta_is_structural_failure():
    root = LE.fromstring(b"""<AOxml>
      <AOHeader>
        <docID>KBo 1.1</docID>
        <kor date="2026-01-01"/>
        <meta/>
      </AOHeader>
      <body><div1><text><w>nu</w></text></div1></body>
    </AOxml>""")
    assert check_tags.header_structure_problems(root) == [
        "edit event kor outside direct AOHeader/meta"
    ]


def test_report_visibly_separates_header_loss_from_body_raw():
    root = LE.fromstring(DOC)
    report = check_tags.render_report(check_tags.inventory_root(root))
    assert "## Body `<text>` element inventory" in report
    assert "## `AOHeader` element inventory" in report
    assert "## `AOHeader` attribute inventory" in report
    assert "known-unpreserved" in report
    assert "does not mean preserved" in report
