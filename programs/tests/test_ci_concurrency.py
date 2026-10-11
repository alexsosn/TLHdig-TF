"""Workflow-level RED contract for ordinary PR CI concurrency (#147)."""
from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CI = ROOT / ".github" / "workflows" / "ci.yml"


def _group(workflow: str, event_name: str, ref: str, run_id: str) -> str:
    """Model the selected #147 expression for collision tests."""
    identity = ref if event_name == "pull_request" else run_id
    return f"{workflow}-{identity}"


def test_ci_declares_pr_scoped_cancellation() -> None:
    doc = yaml.safe_load(CI.read_text(encoding="utf8"))
    concurrency = doc.get("concurrency")

    assert isinstance(concurrency, dict)
    assert concurrency.get("cancel-in-progress") is True

    group = concurrency.get("group")
    assert isinstance(group, str)
    assert "github.workflow" in group
    assert "github.event_name == 'pull_request'" in group
    assert "github.ref" in group
    assert "github.run_id" in group
    assert "github.head_ref" not in group


def test_selected_group_identity_cancels_only_the_same_pr() -> None:
    pr144_a = _group("CI", "pull_request", "refs/pull/144/merge", "1001")
    pr144_b = _group("CI", "pull_request", "refs/pull/144/merge", "1002")
    pr146 = _group("CI", "pull_request", "refs/pull/146/merge", "1003")
    main_a = _group("CI", "push", "refs/heads/main", "2001")
    main_b = _group("CI", "push", "refs/heads/main", "2002")

    assert pr144_a == pr144_b
    assert pr144_a != pr146
    assert pr144_a != main_a
    assert pr146 != main_a
    assert main_a != main_b


def test_workflow_namespace_prevents_cross_workflow_cancellation() -> None:
    ci = _group("CI", "pull_request", "refs/pull/144/merge", "1001")
    docs = _group(
        "Researcher docs examples", "pull_request", "refs/pull/144/merge", "1001"
    )
    assert ci != docs
