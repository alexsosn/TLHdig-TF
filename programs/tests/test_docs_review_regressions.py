"""Adversarial regressions for current researcher-facing documentation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_readme_does_not_present_legacy_load_cost_as_current_040_measurement():
    readme = (ROOT / "README.md").read_text(encoding="utf8")
    paragraphs = [part.strip() for part in readme.split("\n\n")]
    measured = [part for part in paragraphs if "5 GB" in part]
    assert measured, "README should keep any useful historical load-cost evidence explicit"
    for paragraph in measured:
        assert "0.1.0" in paragraph
        assert "0.4.0" in paragraph
        assert "histor" in paragraph.lower()
        assert "not" in paragraph.lower()


def test_manifest_documentation_discloses_datewritten_canonicalization():
    provenance = (ROOT / "docs" / "provenance.md").read_text(encoding="utf8")
    assert "@dateWritten" in provenance
    assert "canonical" in provenance.lower()
    assert "byte-for-byte" in provenance.lower() or "raw byte" in provenance.lower()


def test_runtime_examples_rerun_when_artifact_or_tf_dependency_changes():
    workflow = (ROOT / ".github" / "workflows" / "docs-examples.yml").read_text(
        encoding="utf8"
    )
    assert "tf/**" in workflow
    assert "requirements.txt" in workflow
