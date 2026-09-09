"""Adversarial release-v6 manifest checks for protected-tree stability evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import protected_tree, release_policy, stamp


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


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.name", "Manifest Fixture")
    _git(root, "config", "user.email", "manifest@example.invalid")
    _write(root, "corpus/a.xml", "<a/>\n")
    _write(root, "app/config.yaml", "version: one\n")
    _write(root, "programs/checker.py", "VALUE = 1\n")
    _write(root, "requirements.txt", "text-fabric==13.1.0\n")
    _write(root, ".github/workflows/certify-dataset.yml", "name: certify\n")
    _write(root, "tf/9.9.9/otype.tf", "@node\n\n1\tsign\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "fixture")
    return root


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


def _write_manifest(root: Path, stability: bool | None) -> Path:
    out = root / "tf" / "9.9.9"
    contract = release_policy.policy_contract("release-v6")
    assert contract is not None
    digest, features = stamp.full_digest(out)
    payload = {
        "schema": 2,
        "policy": "release-v6",
        "mode": "regression-valid",
        "sourceVersion": "0.3",
        "tfVersion": "9.9.9",
        "codeCommit": _git(root, "rev-parse", "HEAD"),
        "protectedTree": protected_tree.identity(root),
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
    }
    if stability is not None:
        payload["protectedTreeStable"] = stability
    manifest = out / stamp.CERTIFICATION
    manifest.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf8")
    stamp.write(
        out,
        "0.3",
        "9.9.9",
        certification=manifest,
        mode="regression-valid",
        commit=payload["codeCommit"],
    )
    return out


@pytest.mark.parametrize("stability", [None, False])
def test_release_v6_full_verification_requires_positive_protected_tree_stability(tmp_path, stability):
    root = _repo(tmp_path)
    out = _write_manifest(root, stability)
    problem = stamp.check(out, require_full=True, repo_root=root)
    assert problem is not None
    assert "protectedTreeStable" in problem


def test_release_v6_full_verification_accepts_positive_protected_tree_stability(tmp_path):
    root = _repo(tmp_path)
    out = _write_manifest(root, True)
    assert stamp.check(out, require_full=True, repo_root=root) is None
