"""Command-level contracts for the canonical release certifier."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
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


def test_canonical_release_ends_with_tracked_tree_stability_gate():
    assert release_check.GATES[-1].name == "code-tree-stable"


def test_code_tree_stability_gate_rejects_mutation_after_release_started(monkeypatch):
    monkeypatch.setattr(
        release_check,
        "tracked_changes",
        lambda: [" M programs/check_alignment.py"],
    )
    outcome = release_check.run_gate(
        release_check.certification.Gate("code-tree-stable", ("internal", "tracked-tree")),
        expected_commit="a" * 40,
    )
    assert outcome.status == "failed"
    assert outcome.returncode != 0


def test_code_tree_stability_gate_rejects_clean_checkout_at_different_head(monkeypatch):
    """A hard reset/checkout may change executable code while leaving git status clean."""
    monkeypatch.setattr(release_check, "tracked_changes", lambda: [])
    monkeypatch.setattr(release_check, "_git_head", lambda: "b" * 40)
    outcome = release_check.run_gate(
        release_check.certification.Gate("code-tree-stable", ("internal", "tracked-tree")),
        expected_commit="a" * 40,
    )
    assert outcome.status == "failed"
    assert outcome.returncode != 0


def test_code_tree_stability_gate_accepts_clean_checkout_at_recorded_head(monkeypatch):
    monkeypatch.setattr(release_check, "tracked_changes", lambda: [])
    monkeypatch.setattr(release_check, "_git_head", lambda: "a" * 40)
    outcome = release_check.run_gate(
        release_check.certification.Gate("code-tree-stable", ("internal", "tracked-tree")),
        expected_commit="a" * 40,
    )
    assert outcome.status == "passed"
    assert outcome.returncode == 0


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


def test_commit_override_must_be_full_sha_and_match_head(monkeypatch):
    commit = "1" * 40
    monkeypatch.setenv("TLHDIG_CODE_COMMIT", commit)
    monkeypatch.setenv("GITHUB_SHA", "2" * 40)
    monkeypatch.setattr(
        release_check.subprocess,
        "check_output",
        lambda *_args, **_kwargs: commit + "\n",
    )
    assert release_check.resolve_commit() == commit


def test_commit_override_mismatch_with_git_head_is_rejected(monkeypatch):
    monkeypatch.setenv("TLHDIG_CODE_COMMIT", "1" * 40)
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.setattr(
        release_check.subprocess,
        "check_output",
        lambda *_args, **_kwargs: "2" * 40 + "\n",
    )
    assert release_check.resolve_commit() is None


def test_commit_environment_fallback_when_git_metadata_is_unavailable(monkeypatch):
    commit = "3" * 40
    monkeypatch.setenv("TLHDIG_CODE_COMMIT", commit)
    monkeypatch.delenv("GITHUB_SHA", raising=False)

    def no_git(*_args, **_kwargs):
        raise subprocess.CalledProcessError(128, ["git", "rev-parse", "HEAD"])

    monkeypatch.setattr(release_check.subprocess, "check_output", no_git)
    assert release_check.resolve_commit() == commit


def test_tracked_changes_excludes_mutable_release_outputs_but_not_code(monkeypatch):
    def fake_check_output(command, **_kwargs):
        assert command == [
            "git",
            "status",
            "--porcelain",
            "--untracked-files=no",
            "--",
            ".",
            ":(exclude)tf/**",
            ":(exclude)tf-provenance/**",
            ":(exclude)reports/**",
        ]
        # Git itself applies the pathspecs; a code change still survives the filter.
        return " M programs/release_check.py\n"

    monkeypatch.setattr(release_check.subprocess, "check_output", fake_check_output)
    assert release_check.tracked_changes() == ["M programs/release_check.py"]


def test_main_refuses_dirty_tracked_tree_before_running_certification(monkeypatch):
    monkeypatch.setattr(release_check, "policy_problem", lambda: None)
    monkeypatch.setattr(release_check, "tracked_changes", lambda: ["M programs/release_check.py"])

    def should_not_certify(**_kwargs):
        raise AssertionError("certification ran against code not identified by the recorded commit")

    monkeypatch.setattr(release_check.certification, "certify", should_not_certify)
    assert release_check.main([]) == 1
