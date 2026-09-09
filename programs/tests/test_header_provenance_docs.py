"""Release/docs contract for whole-document provenance (#57/#58)."""
from __future__ import annotations

import sys
from pathlib import Path

import lxml.etree as LE

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build as buildmod
import check_tags
from tlhdig import PROVENANCE_DIR, TF_VERSION, tags


HEADER_WITH_PRESERVED_ONLY = b"""<AOxml>
  <AOHeader>
    <docID>KBo 1.1</docID>
    <meta>
      <annotation><annot editor="AB" data="opaque"/></annotation>
      <mDocID>KBo 2.2</mDocID>
      <ann editor="legacy"/>
    </meta>
  </AOHeader>
  <body><div1><text><w>nu</w></text></div1></body>
</AOxml>"""


def test_provenance_readme_describes_sign_and_document_values_truthfully(tmp_path, monkeypatch):
    out = tmp_path / "tf" / TF_VERSION
    out.mkdir(parents=True)
    (out / "srcxml.tf").write_text("@node\n\n1\tx\n", encoding="utf8")
    (out / "src_span.tf").write_text("@node\n\n1\t0-1\n", encoding="utf8")
    monkeypatch.setattr(buildmod, "ROOT", tmp_path)

    buildmod.split_provenance(out)
    readme = (tmp_path / PROVENANCE_DIR / TF_VERSION / "README.md").read_text(
        encoding="utf8"
    )

    assert "sign-level" in readme
    assert "document-level" in readme
    assert "AOHeader" in readme
    assert "byte range" in readme and "src_file" in readme
    assert "not semantically modelled" in readme
    assert "exact source audit" in readme
    assert "every tag inside `srcxml` is modelled" not in readme


def test_contract_b_calls_unmodelled_header_data_preserved_not_lost():
    assert tags.HEADER_DESTINATION["mDocID"] == "preserved-only"
    assert tags.HEADER_ATTR_DESTINATION[("annot", "data")] == "preserved-only"
    assert tags.HEADER_DESTINATION["ann"] == "malformed-but-preserved"
    for attr in ("date", "editor", "part"):
        assert tags.HEADER_ATTR_DESTINATION[("ann", attr)] == "malformed-but-preserved"
    assert tags.HEADER_PLACEMENT_DESTINATION[("AOHeader", "annot")] == "preserved-only"
    assert (
        tags.HEADER_PLACEMENT_ATTR_DESTINATION[("AOHeader", "annot", "data")]
        == "preserved-only"
    )


def test_contract_b_report_does_not_call_preserved_header_bytes_current_loss():
    root = LE.fromstring(HEADER_WITH_PRESERVED_ONLY)
    report = check_tags.render_report(check_tags.inventory_root(root))

    assert "preserved-only" in report
    assert "malformed-but-preserved" in report
    assert "known-unpreserved" not in report
    assert "malformed-unpreserved" not in report
    assert "current loss" not in report.lower()
    assert "preserved in document provenance" in report


def test_header_provenance_owns_the_reserved_immutable_050_release():
    """The new converter must never rebuild the already-certified 0.4.0 directory."""
    assert TF_VERSION == "0.5.0"


def test_package_level_provenance_notes_include_document_scope_without_false_completeness():
    package_init = Path(__file__).resolve().parents[1] / "tlhdig" / "__init__.py"
    text = package_init.read_text(encoding="utf8")
    assert "document-level" in text
    assert "Every tag inside" not in text


def test_one_shot_green_mutation_workflow_is_not_part_of_the_shipped_repository():
    root = Path(__file__).resolve().parents[2]
    assert not (root / ".github" / "workflows" / "apply-header-provenance-green.yml").exists()
