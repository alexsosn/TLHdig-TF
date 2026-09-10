"""Release identity contract for schema-changing immutable TF releases."""
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import SOURCE_VERSION, TF_VERSION, stamp
from tlhdig.paths import ROOT


def test_current_release_versions():
    assert SOURCE_VERSION == "0.3"
    assert TF_VERSION == "0.5.0"


def test_previous_release_artifacts_are_preserved():
    for version in ("0.1.0", "0.2.0", "0.3.0", "0.4.0"):
        assert (ROOT / "tf" / version).is_dir()
        assert (ROOT / "tf-provenance" / version).is_dir()


def test_release_delta_pins_full_predecessor_artifact():
    """Use the module-aware artifact identity, never legacy BUILD-COMPLETE digest=."""
    spec = json.loads((ROOT / "programs" / "release-delta.json").read_text(encoding="utf8"))
    predecessor = spec["predecessorVersion"]
    digest, _ = stamp.full_digest(ROOT / "tf" / predecessor)
    assert spec["predecessorDigest"] == f"sha256:{digest}"


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
