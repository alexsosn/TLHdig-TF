"""TDD gates for real-artifact impact report of mixed alignment PR #155."""
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _module():
    import research_alignment_delta
    return research_alignment_delta


def test_diff_counts_added_withdrawn_replaced_and_unchanged():
    change = _module().mapping_delta(
        {1: "𒀀", 2: "𒁀", 3: "𒀭", 4: "𒉿"},
        {1: "𒀀", 2: "𒁁", 4: "𒉿", 5: "𒋫"},
    )
    assert change["totalOld"] == 4
    assert change["totalNew"] == 4
    assert change["added"] == 1
    assert change["withdrawn"] == 1
    assert change["replaced"] == 1
    assert change["unchanged"] == 2
    assert change["nodesChanged"] == {2, 3, 5}


def test_protected_content_identity_rejects_unrelated_graph_change():
    diff = _module().changed_protected(
        {"main:otype.tf": "sha:x", "main:cu_sign.tf": "sha:y",
         "main:cu_pua_unmapped.tf": "sha:z"},
        {"main:otype.tf": "sha:different", "main:cu_sign.tf": "sha:new",
         "main:cu_pua_unmapped.tf": "sha:z"},
    )
    assert diff == ["main:otype.tf"]


def test_protected_identity_rejects_missing_existing_feature():
    changed = _module().changed_protected(
        {"main:otype.tf": "sha:x", "main:cu_sign.tf": "sha:y"},
        {"main:cu_sign.tf": "sha:z"},
    )
    assert "main:otype.tf" in changed


def test_reference_buckets_are_not_a_correction_oracle():
    from tlhdig.signrefs import References
    refs = References({"wa": {"osl": {"𒉿"}, "potnia": {"𒁀"}}})
    bucket = _module().reference_bucket
    assert bucket("wa", "𒉿", refs) == "split"
    assert bucket("wa", "𒊀", refs) == "all-disagree"
    assert bucket("unattested", "𒀀", refs) == "unknown"


def test_unevaluated_sign_is_not_voted_on():
    from tlhdig.signrefs import References
    assert _module().reference_bucket("x", "▒", References({})) == "excluded"


def test_comparison_refuses_unbound_source_text(tmp_path):
    from tlhdig import build_manifest
    old = tmp_path / "old"
    new = tmp_path / "new"
    old.mkdir()
    new.mkdir()
    (old / "cu.tf").write_text("@node\n\n1\t𒀀\n", encoding="utf8")
    (new / "cu.tf").write_text("@node\n\n1\t𒁀\n", encoding="utf8")
    assert build_manifest._output_sha256(old / "cu.tf") != build_manifest._output_sha256(new / "cu.tf")
