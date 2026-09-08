"""Issue #19 release integration contract for sign-level language values."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import release_check
from tlhdig import TF_VERSION, featuremeta, release_policy
from tlhdig.paths import ROOT


def test_issue19_bumps_tf_schema_version():
    assert TF_VERSION == "0.4.0"


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


def test_lang_feature_metadata_documents_sign_semantics():
    description = featuremeta.DESCRIPTIONS["lang"].lower()
    assert "sign" in description
    assert "word" in description
    assert "colon" in description
    assert "line" in description
    assert "text" in description
    assert "xxxlang" in description


def test_app_exposes_sign_language_and_targets_new_artifact():
    config = yaml.safe_load((ROOT / "app" / "config.yaml").read_text(encoding="utf8"))
    assert config["provenanceSpec"]["version"] == "0.4.0"
    sign_features = config["typeDisplay"]["sign"]["features"].split()
    assert "lang" in sign_features
