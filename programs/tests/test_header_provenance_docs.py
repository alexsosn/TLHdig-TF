"""Release/docs contract for whole-document provenance (#57/#58)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import lxml.etree as LE

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build as buildmod
import check_contract_a_graph
import check_tags
from tlhdig import PROVENANCE_DIR, TF_VERSION, featuremeta, stamp, tags
from tlhdig.paths import ROOT


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


def test_provenance_readme_describes_actual_node_scopes_and_known_word_exception(
    tmp_path, monkeypatch
):
    """Raw provenance documentation must match the graph, including known span limits.

    ``srcxml`` is sign-level plus document-level. ``src_span`` is carried by source
    word/layout nodes plus documents; it is not a per-sign range. Sixteen crossing-tag
    repair documents also have word spans that cannot be mapped exactly back to source
    bytes, so the module README must not promise universal exactness.
    """
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
    assert "word/layout-level" in readme
    assert "document-level" in readme
    assert "AOHeader" in readme
    assert "byte range" in readme and "src_file" in readme
    assert "crossing-tag" in readme
    assert "not semantically modelled" in readme
    assert "exact source audit" in readme
    assert "every tag inside `srcxml` is modelled" not in readme


def test_src_span_feature_description_does_not_claim_universal_exactness():
    """Generated feature docs must retain the existing crossing-tag span limitation."""
    description = featuremeta.DESCRIPTIONS["src_span"].lower()
    assert "document" in description and "aoheader" in description
    assert "word" in description
    assert "crossing-tag" in description
    assert "exception" in description or "not exact" in description


def test_contract_a_fails_if_an_emitted_document_has_no_src_file(tmp_path, monkeypatch):
    """Complete header coverage cannot silently skip a document with no source identity."""

    class _Feature:
        def __init__(self, values):
            self.values = values

        def v(self, node):
            return self.values.get(node)

    class _Otype:
        def s(self, node_type):
            return (1,) if node_type == "document" else ()

    fake_api = SimpleNamespace(
        F=SimpleNamespace(
            otype=_Otype(),
            src_file=_Feature({1: None}),
            src_span=_Feature({}),
            srcxml=_Feature({}),
            after=_Feature({}),
        ),
        L=SimpleNamespace(d=lambda *_args, **_kwargs: ()),
    )

    class _Fabric:
        def __init__(self, *args, **kwargs):
            pass

        def load(self, *args, **kwargs):
            return fake_api

    import tf.fabric as tf_fabric

    monkeypatch.setattr(tf_fabric, "Fabric", _Fabric)
    monkeypatch.setattr(check_contract_a_graph, "REPORTS", tmp_path)
    assert check_contract_a_graph.main() == 1


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


def test_050_delta_pins_the_full_certified_040_module_identity():
    """The predecessor pin must cover core *and* provenance bytes, not the legacy digest."""
    spec = json.loads((ROOT / "programs" / "release-delta.json").read_text(encoding="utf8"))
    predecessor = ROOT / "tf" / "0.4.0"
    digest, _features = stamp.full_digest(predecessor)
    expected = "sha256:" + digest
    assert spec["predecessorVersion"] == "0.4.0"
    assert spec["predecessorDigest"] == expected

    certification = json.loads(
        (predecessor / stamp.CERTIFICATION).read_text(encoding="utf8")
    )
    assert certification["dataset"]["algorithm"] == "tlhdig-tf-modules-v2"
    assert certification["dataset"]["digest"] == expected


def test_package_level_provenance_notes_include_document_scope_without_false_completeness():
    package_init = Path(__file__).resolve().parents[1] / "tlhdig" / "__init__.py"
    text = package_init.read_text(encoding="utf8")
    assert "document-level" in text
    assert "Every tag inside" not in text


def test_one_shot_green_mutation_workflow_is_not_part_of_the_shipped_repository():
    root = Path(__file__).resolve().parents[2]
    assert not (root / ".github" / "workflows" / "apply-header-provenance-green.yml").exists()
