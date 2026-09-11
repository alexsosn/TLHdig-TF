"""Current pre-alpha TF artifact identity contract."""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import SOURCE_VERSION, TF_VERSION
from tlhdig.paths import ROOT


def test_current_release_versions():
    assert SOURCE_VERSION == "0.3"
    assert TF_VERSION == "0.4.0"


def test_only_current_generated_artifact_directories_are_active():
    expected = {TF_VERSION}
    main_versions = {path.name for path in (ROOT / "tf").iterdir() if path.is_dir()}
    provenance_versions = {
        path.name for path in (ROOT / "tf-provenance").iterdir() if path.is_dir()
    }
    assert main_versions == expected
    assert provenance_versions == expected


def test_current_release_documentation_and_app_follow_tf_version():
    readme = (ROOT / "README.md").read_text(encoding="utf8")
    known = (ROOT / "KNOWN-ISSUES.md").read_text(encoding="utf8")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf8")
    agora = (ROOT / "docs" / "AGORA-INTEGRATION.md").read_text(encoding="utf8")
    config = yaml.safe_load((ROOT / "app" / "config.yaml").read_text(encoding="utf8"))

    assert f"Current TF version: `{TF_VERSION}`" in readme
    assert f'Fabric(locations="tf/{TF_VERSION}")' in readme
    assert f"tf/{TF_VERSION}/" in readme
    assert known.startswith(f"# Known issues in `tf/{TF_VERSION}`")
    assert f"current tf/{TF_VERSION} build" in citation
    assert f'Fabric(locations="tf/{TF_VERSION}")' in agora
    assert config["provenanceSpec"]["version"] == TF_VERSION

    plan = (ROOT / "docs" / "TF-CONVERSION-PLAN.md").read_text(encoding="utf8")
    release = (ROOT / "docs" / "RELEASE.md").read_text(encoding="utf8")
    assert "| language on the sign | `sign.lang` | done in `tf/0.4.0`" in plan
    assert "`sign.lang`: language exists at document/line/colon level, not on every sign" not in known
    assert "release-v5" in release and "sign-language" in release
