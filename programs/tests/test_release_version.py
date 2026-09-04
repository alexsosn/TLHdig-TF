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


def test_current_release_documentation_follows_tf_version():
    readme = (ROOT / "README.md").read_text(encoding="utf8")
    known = (ROOT / "KNOWN-ISSUES.md").read_text(encoding="utf8")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf8")
    agora = (ROOT / "docs" / "AGORA-INTEGRATION.md").read_text(encoding="utf8")

    assert f"Current TF version: `{TF_VERSION}`" in readme
    assert f'Fabric(locations="tf/{TF_VERSION}")' in readme
    assert f"tf/{TF_VERSION}/" in readme
    assert known.startswith(f"# Known issues in `tf/{TF_VERSION}`")
    assert f"current tf/{TF_VERSION} build" in citation
    assert f'Fabric(locations="tf/{TF_VERSION}")' in agora
