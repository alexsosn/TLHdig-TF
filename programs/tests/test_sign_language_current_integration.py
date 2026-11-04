"""Issue #19 integration contract for sign-level language values."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import validate_current
from tlhdig import TF_VERSION, featuremeta
from tlhdig.paths import ROOT


def test_issue19_schema_version_is_current():
    assert TF_VERSION == "0.4.0"


def test_sign_language_remains_a_required_current_validation_gate():
    configured = {gate.name: gate.command for gate in validate_current.GATES}
    assert configured["sign-language"] == ("python", "programs/check_sign_language.py")


def test_lang_feature_metadata_documents_sign_semantics():
    description = featuremeta.DESCRIPTIONS["lang"].lower()
    assert "sign" in description
    assert "word" in description
    assert "colon" in description
    assert "line" in description
    assert "text" in description
    assert "xxxlang" in description


def test_app_exposes_sign_language_and_targets_current_artifact():
    config = yaml.safe_load((ROOT / "app" / "config.yaml").read_text(encoding="utf8"))
    assert config["provenanceSpec"]["version"] == TF_VERSION
    sign_features = config["typeDisplay"]["sign"]["features"].split()
    assert "lang" in sign_features
