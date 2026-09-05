"""Release identity and immutability contract for the current TF artifact."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import SOURCE_VERSION, TF_VERSION
from tlhdig.paths import ROOT


def test_current_release_versions():
    assert SOURCE_VERSION == "0.3"
    assert TF_VERSION == "0.2.1"


def test_previous_release_artifacts_are_preserved():
    for version in ("0.1.0", "0.2.0"):
        assert (ROOT / "tf" / version).is_dir()
        assert (ROOT / "tf-provenance" / version).is_dir()


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
