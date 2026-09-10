"""Repository wiring for current-build validation (#116)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def test_no_dedicated_write_enabled_certification_workflow_remains():
    assert not (WORKFLOWS / "certify-dataset.yml").exists()


def test_dataset_workflow_builds_then_validates_current_artifact():
    text = (WORKFLOWS / "dataset.yml").read_text(encoding="utf8")
    assert "python programs/build.py" in text
    assert "python programs/validate_current.py" in text
    assert "release_check.py" not in text


def test_ci_verifies_current_build_manifest_not_historical_stamp():
    text = (WORKFLOWS / "ci.yml").read_text(encoding="utf8")
    assert "python programs/check_build_manifest.py" in text
    assert "check_stamp.py" not in text
    assert "BUILD-COMPLETE" not in text


def test_staging_requires_current_build_manifest():
    text = (ROOT / "programs" / "publish_dataset.sh").read_text(encoding="utf8")
    assert "check_build_manifest.py" in text
    assert "check_stamp.py" not in text
    assert "RELEASE-CERTIFICATION.json" not in text


def test_operational_docs_use_current_build_commands():
    for path in (ROOT / "README.md", ROOT / "KNOWN-ISSUES.md", ROOT / "docs" / "RELEASE.md"):
        text = path.read_text(encoding="utf8")
        assert "programs/release_check.py" not in text, path
        assert "programs/check_stamp.py" not in text, path
    release = (ROOT / "docs" / "RELEASE.md").read_text(encoding="utf8")
    assert "python programs/validate_current.py" in release
    assert "python programs/check_build_manifest.py" in release
