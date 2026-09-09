"""RED contract for fail-closed release-v6 certification freshness (#69).

The tests deliberately use tiny synthetic Git repositories.  They freeze the public
freshness boundary without depending on the real corpus size or mutating published TF
artifacts.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import certification, release_policy, stamp

ALGORITHM = "tlhdig-protected-git-tree-v1"
PROFILE = "release-source-v1"


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf8")


def _commit(root: Path, message: str = "fixture") -> str:
    _git(root, "add", "-A")
    _git(root, "commit", "-m", message)
    return _git(root, "rev-parse", "HEAD")


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.name", "Freshness Fixture")
    _git(root, "config", "user.email", "freshness@example.invalid")

    # Protected profile v1 inputs.
    _write(root, "corpus/a.xml", "<a>one</a>\n")
    _write(root, "app/config.yaml", "version: one\n")
    _write(root, "programs/checker.py", "VALUE = 1\n")
    _write(root, "programs/patches.yaml", "{}\n")
    _write(root, "requirements.txt", "text-fabric==13.1.0\n")
    _write(root, ".github/workflows/certify-dataset.yml", "name: certify\n")

    # Explicitly excluded development/generated material.
    _write(root, "programs/tests/test_dev_only.py", "VALUE = 1\n")
    _write(root, "programs/research_probe.py", "VALUE = 1\n")
    _write(root, "programs/shard.txt", "sample\n")
    _write(root, "reports/a.json", "{}\n")
    _write(root, "docs/a.md", "docs\n")
    _write(root, "tf/9.9.9/otype.tf", "@node\n\n1\tsign\n")
    _write(root, "tf-provenance/9.9.9/srcxml.tf", "@node\n\n1\tx\n")
    _commit(root)
    return root


def _protected_tree():
    # Local import keeps collection healthy during the RED phase: the intended
    # failure is the absent production contract, not an import-time test crash.
    from tlhdig import protected_tree

    return protected_tree


def _identity(root: Path) -> dict[str, str]:
    return dict(_protected_tree().identity(root, profile=PROFILE))


def test_current_policy_is_release_v6_with_frozen_protected_profile():
    assert release_policy.POLICY == "release-v6"
    contract = release_policy.policy_contract("release-v6")
    assert contract is not None
    assert contract.protected_tree_algorithm == ALGORITHM
    assert contract.protected_tree_profile == PROFILE


def test_protected_commits_change_identity_but_excluded_commits_do_not(tmp_path):
    root = _repo(tmp_path)
    first = _identity(root)
    assert first == {
        "algorithm": ALGORITHM,
        "profile": PROFILE,
        "digest": first["digest"],
    }
    assert first["digest"].startswith("sha256:") and len(first["digest"]) == 71

    for rel in (
        "app/config.yaml",
        "programs/checker.py",
        "programs/patches.yaml",
        "corpus/a.xml",
        "requirements.txt",
        ".github/workflows/certify-dataset.yml",
    ):
        before = _identity(root)
        path = root / rel
        path.write_text(path.read_text(encoding="utf8") + "changed\n", encoding="utf8")
        _commit(root, f"change {rel}")
        after = _identity(root)
        assert after["digest"] != before["digest"], rel

    before = _identity(root)
    for rel in (
        "reports/a.json",
        "docs/a.md",
        "programs/tests/test_dev_only.py",
        "programs/research_probe.py",
        "programs/shard.txt",
        "tf/9.9.9/otype.tf",
        "tf-provenance/9.9.9/srcxml.tf",
    ):
        path = root / rel
        path.write_text(path.read_text(encoding="utf8") + "excluded\n", encoding="utf8")
    _commit(root, "excluded outputs and development evidence")
    assert _identity(root) == before


@pytest.mark.parametrize(
    ("kind", "rel"),
    (
        ("unstaged", "app/config.yaml"),
        ("staged", "requirements.txt"),
        ("untracked", "programs/new_release_helper.py"),
    ),
)
def test_dirty_protected_worktree_fails_closed(tmp_path, kind, rel):
    root = _repo(tmp_path)
    protected_tree = _protected_tree()
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.write_text(path.read_text(encoding="utf8") + "dirty\n", encoding="utf8")
    else:
        path.write_text("dirty\n", encoding="utf8")
    if kind == "staged":
        _git(root, "add", rel)

    with pytest.raises(protected_tree.ProtectedTreeError, match="dirty|protected"):
        protected_tree.identity(root, profile=PROFILE)


def test_dirty_excluded_output_does_not_self_invalidate_identity(tmp_path):
    root = _repo(tmp_path)
    before = _identity(root)
    (root / "reports/a.json").write_text('{"new": true}\n', encoding="utf8")
    _write(root, "reports/untracked.json", "{}\n")
    assert _identity(root) == before


def test_missing_git_and_unknown_profile_fail_closed(tmp_path):
    protected_tree = _protected_tree()
    not_repo = tmp_path / "not-repo"
    not_repo.mkdir()
    with pytest.raises(protected_tree.ProtectedTreeError, match="Git|git"):
        protected_tree.identity(not_repo, profile=PROFILE)

    root = _repo(tmp_path / "nested")
    with pytest.raises(protected_tree.ProtectedTreeError, match="profile"):
        protected_tree.identity(root, profile="unknown-profile")


def test_evidence_only_child_commit_keeps_certified_protected_identity(tmp_path):
    root = _repo(tmp_path)
    before = _identity(root)
    _write(root, "reports/release-certification.json", '{"success": true}\n')
    _write(root, "tf/9.9.9/RELEASE-CERTIFICATION.json", '{"success": true}\n')
    _write(root, "tf/9.9.9/BUILD-COMPLETE", "evidence only\n")
    _commit(root, "certification evidence")
    assert _identity(root) == before


def _gate_rows(contract, tf_version: str) -> list[dict]:
    rows = []
    for name in contract.required_gates:
        row = {"name": name, "command": [name], "status": "passed", "returncode": 0}
        if name == "predecessor-delta":
            row["evidence"] = {
                "baseline": False,
                "tfVersion": tf_version,
                "predecessorVersion": "9.9.8",
                "predecessorDigest": "sha256:" + "a" * 64,
                "expectedChanges": [],
                "actualChanges": [],
            }
        rows.append(row)
    return rows


def _write_historical_v5(out: Path) -> None:
    """A frozen schema-1 v5 fixture: this is a GREEN compatibility control in RED."""
    contract = release_policy.policy_contract("release-v5")
    assert contract is not None
    digest, features = stamp.full_digest(out)
    manifest = out / stamp.CERTIFICATION
    manifest.write_text(
        json.dumps(
            {
                "schema": 1,
                "policy": "release-v5",
                "mode": "regression-valid",
                "sourceVersion": "0.3",
                "tfVersion": "9.9.9",
                "codeCommit": "a" * 40,
                "dataset": {
                    "algorithm": release_policy.ARTIFACT_DIGEST_ALGORITHM,
                    "digest": "sha256:" + digest,
                    "features": features,
                },
                "inputs": {
                    name: "sha256:" + hashlib.sha256(name.encode()).hexdigest()
                    for name in contract.required_inputs
                },
                "knownDefects": {name: 1 for name in contract.fidelity_baselines},
                "requiredGates": list(contract.required_gates),
                "gates": _gate_rows(contract, "9.9.9"),
                "artifactStable": True,
                "inputsStable": True,
                "success": True,
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf8",
    )
    stamp.write(
        out,
        "0.3",
        "9.9.9",
        certification=manifest,
        mode="regression-valid",
        commit="a" * 40,
    )


def test_historical_release_v5_remains_valid_without_git(tmp_path):
    out = tmp_path / "artifact"
    out.mkdir()
    (out / "otype.tf").write_text("@node\n\n1\tsign\n", encoding="utf8")
    _write_historical_v5(out)
    assert stamp.check(out, require_full=True) is None


def test_certification_fails_if_a_gate_mutates_protected_code(tmp_path):
    root = _repo(tmp_path)
    out = root / "tf" / "9.9.9"
    input_path = root / "programs" / "patches.yaml"
    report = root / "reports" / "attempt.json"
    gates = (certification.Gate("mutation-probe", ("mutation-probe",)),)

    def runner(_gate):
        (root / "app/config.yaml").write_text("version: mutated during gates\n", encoding="utf8")
        return certification.GateOutcome("passed", 0)

    rc = certification.certify(
        out=out,
        source_version="0.3",
        tf_version="9.9.9",
        mode="regression-valid",
        gates=gates,
        runner=runner,
        input_files={"repairManifest": input_path},
        known_defects={"knownLossy": 1, "contractAKnown": 1, "knownWordDeficit": 1},
        code_commit=_git(root, "rev-parse", "HEAD"),
        report_path=report,
        repo_root=root,
    )
    assert rc == 1
    assert not (out / stamp.STAMP).exists()
    payload = json.loads(report.read_text(encoding="utf8"))
    assert payload["success"] is False
    assert "protected" in json.dumps(payload).lower()


def test_valid_release_v6_schema2_manifest_verifies_against_current_checkout(tmp_path):
    root = _repo(tmp_path)
    out = root / "tf" / "9.9.9"
    identity = _identity(root)
    digest, features = stamp.full_digest(out)
    contract = release_policy.policy_contract("release-v6")
    assert contract is not None
    manifest = out / stamp.CERTIFICATION
    manifest.write_text(
        json.dumps(
            {
                "schema": 2,
                "policy": "release-v6",
                "mode": "regression-valid",
                "sourceVersion": "0.3",
                "tfVersion": "9.9.9",
                "codeCommit": _git(root, "rev-parse", "HEAD"),
                "protectedTree": identity,
                "dataset": {
                    "algorithm": release_policy.ARTIFACT_DIGEST_ALGORITHM,
                    "digest": "sha256:" + digest,
                    "features": features,
                },
                "inputs": {
                    name: "sha256:" + hashlib.sha256(name.encode()).hexdigest()
                    for name in contract.required_inputs
                },
                "knownDefects": {name: 1 for name in contract.fidelity_baselines},
                "requiredGates": list(contract.required_gates),
                "gates": _gate_rows(contract, "9.9.9"),
                "artifactStable": True,
                "inputsStable": True,
                "success": True,
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf8",
    )
    stamp.write(
        out,
        "0.3",
        "9.9.9",
        certification=manifest,
        mode="regression-valid",
        commit=_git(root, "rev-parse", "HEAD"),
    )
    assert stamp.check(out, require_full=True, repo_root=root) is None

    # The same artifact/evidence must stop certifying a later protected source commit.
    (root / "programs/checker.py").write_text("VALUE = 2\n", encoding="utf8")
    _commit(root, "later protected change")
    problem = stamp.check(out, require_full=True, repo_root=root)
    assert problem and "protected" in problem.lower()
