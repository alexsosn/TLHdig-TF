"""Issue #19 release integration contract for sign-level language values."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import release_check
from tlhdig import TF_VERSION, featuremeta, release_policy
from tlhdig.paths import ROOT


def test_issue19_release_remains_available_in_040():
    """#19 owns the 0.4.0 language release, not the repository's forever-current version."""
    assert (ROOT / "tf" / "0.4.0" / "lang.tf").is_file()
    assert (ROOT / "tf" / "0.4.0" / "BUILD-COMPLETE").is_file()


def test_issue19_has_a_versioned_release_gate():
    assert release_policy.POLICY == "release-v5"
    assert "sign-language" in release_policy.REQUIRED_GATES
    assert "predecessor-delta" in release_policy.REQUIRED_GATES
    assert "releaseDelta" in release_policy.REQUIRED_INPUTS
    configured = {gate.name: gate.command for gate in release_check.GATES}
    assert configured["sign-language"] == ("python", "programs/check_sign_language.py")
    assert tuple(configured) == release_policy.REQUIRED_GATES

    historical_v4 = release_policy.policy_contract("release-v4")
    assert historical_v4 is not None
    assert "predecessor-delta" in historical_v4.required_gates
    assert "releaseDelta" in historical_v4.required_inputs
    assert "sign-language" not in historical_v4.required_gates


def test_plan_records_release_v5_rebase_amendment():
    plan = (ROOT / "docs" / "plan-sign-language.md").read_text(encoding="utf8")
    assert "## 13. Release-policy rebase amendment" in plan
    assert "release-v5" in plan
    assert "release-v4 had already landed" in plan


def test_lang_feature_metadata_documents_sign_semantics():
    description = featuremeta.DESCRIPTIONS["lang"].lower()
    assert "sign" in description
    assert "word" in description
    assert "colon" in description
    assert "line" in description
    assert "text" in description
    assert "xxxlang" in description


def test_app_keeps_sign_language_exposed_on_the_current_artifact():
    config = yaml.safe_load((ROOT / "app" / "config.yaml").read_text(encoding="utf8"))
    assert config["provenanceSpec"]["version"] == TF_VERSION
    sign_features = config["typeDisplay"]["sign"]["features"].split()
    assert "lang" in sign_features
