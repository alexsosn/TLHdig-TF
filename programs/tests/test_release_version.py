"""Release identity contract for the project-metadata schema change."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import SOURCE_VERSION, TF_VERSION
from tlhdig.paths import ROOT


def test_project_metadata_release_versions():
    assert SOURCE_VERSION == "0.3"
    assert TF_VERSION == "0.2.0"


def test_previous_release_artifacts_are_preserved():
    assert (ROOT / "tf" / "0.1.0").is_dir()
    assert (ROOT / "tf-provenance" / "0.1.0").is_dir()
