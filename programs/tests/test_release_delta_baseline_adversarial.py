"""Adversarial RED for the one-time release-v4 adoption baseline (#38)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

PROGRAMS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROGRAMS))

from tlhdig import release_delta, release_policy, stamp


def _tf(body: str) -> str:
    return "@node\n\n" + body


def _synthetic_baseline(tmp_path: Path) -> tuple[Path, Path, str]:
    root = tmp_path / "root"
    out = root / "tf" / release_policy.DELTA_BASELINE_TF_VERSION
    out.mkdir(parents=True)
    (out / "otype.tf").write_text(_tf("1\tsign\n"), encoding="utf8")
    digest, _ = stamp.full_digest(out)
    return root, out, "sha256:" + digest


def test_baseline_cannot_redefine_policy_identity_to_match_new_bytes(tmp_path):
    root, _out, actual_digest = _synthetic_baseline(tmp_path)
    spec = tmp_path / "release-delta.json"
    spec.write_text(
        json.dumps(
            {
                "schema": 1,
                "tfVersion": release_policy.DELTA_BASELINE_TF_VERSION,
                "baseline": True,
                # These bytes are internally self-consistent, but they are not the
                # already-adopted 0.3.0 artifact. A mutable spec must not redefine the
                # escape hatch's identity after policy adoption.
                "baselineDigest": actual_digest,
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf8",
    )
    with pytest.raises(release_delta.DeltaError, match="baseline"):
        release_delta.check(
            spec,
            root=root,
            current_version=release_policy.DELTA_BASELINE_TF_VERSION,
        )


def test_stamp_verifier_rejects_self_consistent_noncanonical_baseline(tmp_path):
    _root, out, actual_digest = _synthetic_baseline(tmp_path)
    contract = release_policy.policy_contract("release-v4")
    assert contract is not None
    gates = []
    for name in contract.required_gates:
        row = {"name": name, "command": [name], "status": "passed", "returncode": 0}
        if name == "predecessor-delta":
            row["evidence"] = {
                "baseline": True,
                "tfVersion": release_policy.DELTA_BASELINE_TF_VERSION,
                "baselineDigest": actual_digest,
                "expectedChanges": [],
                "actualChanges": [],
            }
        gates.append(row)

    digest, features = stamp.full_digest(out)
    manifest = out / stamp.CERTIFICATION
    manifest.write_text(
        json.dumps(
            {
                "schema": 1,
                "policy": "release-v4",
                "mode": "regression-valid",
                "sourceVersion": "0.3",
                "tfVersion": release_policy.DELTA_BASELINE_TF_VERSION,
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
                "knownDefects": {
                    name: 0 for name in contract.fidelity_baselines
                },
                "requiredGates": list(contract.required_gates),
                "gates": gates,
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
        release_policy.DELTA_BASELINE_TF_VERSION,
        certification=manifest,
        mode="regression-valid",
        commit="a" * 40,
    )
    problem = stamp.check(out, require_full=True)
    assert problem and "baseline" in problem.lower() and "digest" in problem.lower()
