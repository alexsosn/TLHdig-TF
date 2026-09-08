from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "finalize-issue19.yml"


def _text() -> str:
    return WORKFLOW.read_text(encoding="utf8")


def _data() -> dict:
    return yaml.safe_load(_text())


def test_issue19_finalizer_checks_out_exact_triggering_commit():
    data = _data()
    steps = data["jobs"]["finalize"]["steps"]
    checkout = next(step for step in steps if step.get("uses", "").startswith("actions/checkout@"))
    assert checkout.get("with", {}).get("ref") == "${{ github.sha }}"


def test_issue19_finalizer_regenerates_and_checks_feature_docs():
    text = _text()
    assert "python programs/build_feature_docs.py" in text
    assert "python programs/build_feature_docs.py --check" in text
    assert "git add docs/features/" in text


def test_issue19_finalizer_is_race_safe_and_never_stages_tf_artifacts():
    text = _text()
    assert "git fetch origin research/sign-lang-19" in text
    assert 'test "$(git rev-parse origin/research/sign-lang-19)" = "$GITHUB_SHA"' in text
    assert "git add -f tf/0.4.0" not in text
    assert "git add -f tf-provenance/0.4.0" not in text
    assert "git diff --cached --name-only" in text
