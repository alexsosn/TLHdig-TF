from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "build-final-19.yml"


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf8")


def _workflow_data() -> dict:
    return yaml.safe_load(_workflow_text())


def test_issue19_build_checks_out_exact_triggering_commit():
    data = _workflow_data()
    steps = data["jobs"]["build"]["steps"]
    checkout = next(step for step in steps if step.get("uses", "").startswith("actions/checkout@"))
    assert checkout.get("with", {}).get("ref") == "${{ github.sha }}"


def test_issue19_build_fails_closed_if_branch_advances_before_staging():
    text = _workflow_text()
    assert "git fetch origin research/sign-lang-19" in text
    assert 'test "$(git rev-parse origin/research/sign-lang-19)" = "$GITHUB_SHA"' in text
    assert "--force" not in text
    assert "git rebase" not in text


def test_issue19_build_removes_and_rejects_runtime_cache_before_commit():
    text = _workflow_text()
    assert "rm -rf tf/0.4.0/.tf tf-provenance/0.4.0/.tf" in text
    assert "git add -f tf/0.4.0 tf-provenance/0.4.0" in text
    assert "git diff --cached --name-only" in text
    assert "tf/0.4.0/.tf/" in text
    assert "tf-provenance/0.4.0/.tf/" in text
