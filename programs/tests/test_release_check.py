"""Command-level contracts for the canonical release certifier."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import release_check


def test_canonical_gate_set_matches_versioned_release_policy():
    names = tuple(gate.name for gate in release_check.GATES)
    assert names == release_check.release_policy.REQUIRED_GATES
    assert release_check.policy_problem() is None


def test_policy_guard_rejects_truncated_gate_configuration(monkeypatch):
    monkeypatch.setattr(release_check, "GATES", release_check.GATES[:-1])
    problem = release_check.policy_problem()
    assert problem and release_check.release_policy.POLICY in problem


def test_external_signref_gates_are_hard_release_mode():
    external = {gate.name: gate.command for gate in release_check.GATES if "signrefs" in gate.name}
    assert set(external) == {"fetch-signrefs", "check-signrefs"}
    for command in external.values():
        assert command[-2:] == ("--mode", "release")


def test_signref_runner_uses_explicit_status_not_zero_exit(monkeypatch, tmp_path):
    status = tmp_path / "signrefs-status.json"
    monkeypatch.setattr(release_check, "STATUS", status)

    def fake_run(*_args, **_kwargs):
        status.write_text(
            json.dumps({"mode": "release", "state": "skipped-unavailable", "sources": []}),
            encoding="utf8",
        )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(release_check.subprocess, "run", fake_run)
    outcome = release_check.run_gate(
        release_check.certification.Gate(
            "fetch-signrefs", ("python", "programs/fetch_signrefs.py", "--mode", "release")
        )
    )
    assert outcome.status == "skipped-unavailable"
    assert outcome.returncode == 0


def test_signref_runner_refuses_zero_exit_without_status(monkeypatch, tmp_path):
    status = tmp_path / "signrefs-status.json"
    monkeypatch.setattr(release_check, "STATUS", status)
    monkeypatch.setattr(
        release_check.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0),
    )
    outcome = release_check.run_gate(
        release_check.certification.Gate(
            "check-signrefs", ("python", "programs/check_signrefs.py", "--mode", "release")
        )
    )
    assert outcome.status == "failed"
    assert outcome.returncode == 0


def test_commit_override_must_be_full_sha(monkeypatch):
    monkeypatch.setenv("TLHDIG_CODE_COMMIT", "1" * 40)
    monkeypatch.setenv("GITHUB_SHA", "2" * 40)
    assert release_check.resolve_commit() == "1" * 40


def test_tracked_changes_ignores_untracked_files(monkeypatch):
    def fake_check_output(command, **_kwargs):
        assert command[-1] == "--untracked-files=no"
        return " M programs/release_check.py\nM  programs/tlhdig/stamp.py\n"

    monkeypatch.setattr(release_check.subprocess, "check_output", fake_check_output)
    assert release_check.tracked_changes() == [
        "M programs/release_check.py",
        "M programs/tlhdig/stamp.py",
    ]


def test_main_refuses_dirty_tracked_tree_before_running_certification(monkeypatch):
    monkeypatch.setattr(release_check, "policy_problem", lambda: None)
    monkeypatch.setattr(release_check, "tracked_changes", lambda: ["M programs/release_check.py"])

    def should_not_certify(**_kwargs):
        raise AssertionError("certification ran against code not identified by the recorded commit")

    monkeypatch.setattr(release_check.certification, "certify", should_not_certify)
    assert release_check.main([]) == 1
