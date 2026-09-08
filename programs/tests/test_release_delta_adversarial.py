"""Independent adversarial RED cases for predecessor-aware certification (#38)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

PROGRAMS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROGRAMS))

from tlhdig import TF_VERSION, release_delta, release_policy, stamp
from tlhdig.paths import ROOT


def _tf(body: str) -> str:
    return "@node\n\n" + body


def _write_pair(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "root"
    old = root / "tf" / "1.0.0"
    new = root / "tf" / "1.1.0"
    old.mkdir(parents=True)
    new.mkdir(parents=True)
    for directory in (old, new):
        (directory / "otype.tf").write_text(_tf("1\tsign\n"), encoding="utf8")
        (directory / "sym.tf").write_text(_tf("1\ta\n"), encoding="utf8")
    return root, old, new


def _spec(path: Path, *, predecessor: str, digest: str, expected: list[str]) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema": 1,
                "tfVersion": "1.1.0",
                "predecessorVersion": predecessor,
                "predecessorDigest": digest,
                "expectedChanges": expected,
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf8",
    )
    return path


def test_declared_added_malformed_tf_feature_is_a_hard_failure(tmp_path):
    root, old, new = _write_pair(tmp_path)
    predecessor_digest, _ = stamp.full_digest(old)
    # Added/removed files used to be classified by name without parsing the existing
    # side, so a malformed new feature could be declared and pass the delta gate.
    (new / "broken.tf").write_text("@node\nno-metadata-body-separator\n", encoding="utf8")
    spec = _spec(
        tmp_path / "delta.json",
        predecessor="1.0.0",
        digest="sha256:" + predecessor_digest,
        expected=["main:broken.tf"],
    )
    with pytest.raises(release_delta.DeltaError, match="malformed"):
        release_delta.check(spec, root=root, current_version="1.1.0")


def test_predecessor_version_cannot_escape_the_version_component(tmp_path):
    root, old, _new = _write_pair(tmp_path)
    predecessor_digest, _ = stamp.full_digest(old)
    # This path resolves to the same old artifact on POSIX, but a release identifier is
    # not a filesystem path and must not be able to traverse the expected version slot.
    spec = _spec(
        tmp_path / "delta.json",
        predecessor="../tf/1.0.0",
        digest="sha256:" + predecessor_digest,
        expected=[],
    )
    with pytest.raises(release_delta.DeltaError, match="predecessorVersion"):
        release_delta.check(spec, root=root, current_version="1.1.0")


def test_value_type_change_with_identical_body_counts_as_delta(tmp_path):
    root, old, new = _write_pair(tmp_path)
    (old / "sym.tf").write_text(
        "@node\n@valueType=str\n@version=1.0.0\n@dateWritten=old\n\n1\t1\n",
        encoding="utf8",
    )
    predecessor_digest, _ = stamp.full_digest(old)
    (new / "sym.tf").write_text(
        "@node\n@valueType=int\n@version=1.1.0\n@dateWritten=new\n\n1\t1\n",
        encoding="utf8",
    )
    spec = _spec(
        tmp_path / "delta.json",
        predecessor="1.0.0",
        digest="sha256:" + predecessor_digest,
        expected=["main:sym.tf"],
    )
    evidence = release_delta.check(spec, root=root, current_version="1.1.0")
    assert evidence["actualChanges"] == ["main:sym.tf"]


def test_node_vs_edge_change_with_identical_body_counts_as_delta(tmp_path):
    root, old, new = _write_pair(tmp_path)
    (old / "sym.tf").write_text(
        "@node\n@valueType=str\n\n1\t2\n",
        encoding="utf8",
    )
    predecessor_digest, _ = stamp.full_digest(old)
    (new / "sym.tf").write_text(
        "@edge\n@valueType=str\n\n1\t2\n",
        encoding="utf8",
    )
    spec = _spec(
        tmp_path / "delta.json",
        predecessor="1.0.0",
        digest="sha256:" + predecessor_digest,
        expected=["main:sym.tf"],
    )
    evidence = release_delta.check(spec, root=root, current_version="1.1.0")
    assert evidence["actualChanges"] == ["main:sym.tf"]


def test_documentary_ordinary_metadata_can_change_without_data_delta(tmp_path):
    root, old, new = _write_pair(tmp_path)
    (old / "sym.tf").write_text(
        "@node\n@valueType=str\n@description=old wording\n@version=1.0.0\n@dateWritten=old\n\n1\ta\n",
        encoding="utf8",
    )
    predecessor_digest, _ = stamp.full_digest(old)
    (new / "sym.tf").write_text(
        "@node\n@valueType=str\n@description=new wording\n@version=1.1.0\n@dateWritten=new\n\n1\ta\n",
        encoding="utf8",
    )
    spec = _spec(
        tmp_path / "delta.json",
        predecessor="1.0.0",
        digest="sha256:" + predecessor_digest,
        expected=[],
    )
    evidence = release_delta.check(spec, root=root, current_version="1.1.0")
    assert evidence["actualChanges"] == []


def test_baseline_adoption_is_pinned_to_current_artifact_digest(tmp_path):
    root = tmp_path / "root"
    current = root / "tf" / release_policy.DELTA_BASELINE_TF_VERSION
    current.mkdir(parents=True)
    (current / "otype.tf").write_text(_tf("1\tsign\n"), encoding="utf8")
    spec = tmp_path / "delta.json"
    spec.write_text(
        json.dumps(
            {
                "schema": 1,
                "tfVersion": release_policy.DELTA_BASELINE_TF_VERSION,
                "baseline": True,
                "baselineDigest": "sha256:" + "0" * 64,
            }
        )
        + "\n",
        encoding="utf8",
    )
    with pytest.raises(release_delta.DeltaError, match="baselineDigest"):
        release_delta.check(
            spec,
            root=root,
            current_version=release_policy.DELTA_BASELINE_TF_VERSION,
        )


def test_committed_release_declaration_matches_shipped_artifact():
    if not (ROOT / "tf" / TF_VERSION).is_dir():
        pytest.skip("current TF release is not materialized yet")
    evidence = release_delta.check(
        PROGRAMS / "release-delta.json",
        root=ROOT,
        current_version=TF_VERSION,
    )
    assert evidence == {
        "baseline": False,
        "tfVersion": "0.4.0",
        "predecessorVersion": "0.3.0",
        "predecessorDigest": release_policy.DELTA_BASELINE_DIGEST,
        "expectedChanges": ["main:lang.tf"],
        "actualChanges": ["main:lang.tf"],
    }


def _v4_manifest(out: Path, *, evidence: dict, tf_version: str = "9.9.9") -> Path:
    contract = release_policy.policy_contract("release-v4")
    assert contract is not None
    digest, features = stamp.full_digest(out)
    gates = []
    for name in contract.required_gates:
        row = {"name": name, "command": [name], "status": "passed", "returncode": 0}
        if name == "predecessor-delta":
            row["evidence"] = evidence
        gates.append(row)
    payload = {
        "schema": 1,
        "policy": "release-v4",
        "mode": "regression-valid",
        "sourceVersion": "0.3",
        "tfVersion": tf_version,
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
        "knownDefects": {name: 0 for name in contract.fidelity_baselines},
        "requiredGates": list(contract.required_gates),
        "gates": gates,
        "artifactStable": True,
        "inputsStable": True,
        "success": True,
    }
    manifest = out / stamp.CERTIFICATION
    manifest.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf8")
    return manifest


def test_independent_stamp_verifier_rejects_unpinned_baseline_evidence(tmp_path):
    root = tmp_path / "baseline-cert-root"
    out = root / "tf" / release_policy.DELTA_BASELINE_TF_VERSION
    out.mkdir(parents=True)
    (out / "otype.tf").write_text(_tf("1\tsign\n"), encoding="utf8")
    evidence = {
        "baseline": True,
        "tfVersion": release_policy.DELTA_BASELINE_TF_VERSION,
        "baselineDigest": "sha256:" + "0" * 64,
        "expectedChanges": [],
        "actualChanges": [],
    }
    manifest = _v4_manifest(
        out,
        evidence=evidence,
        tf_version=release_policy.DELTA_BASELINE_TF_VERSION,
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
    assert problem and "predecessor" in problem.lower() and "digest" in problem.lower()


def test_independent_stamp_verifier_rejects_wildcard_change_evidence(tmp_path):
    root = tmp_path / "cert-root"
    out = root / "tf" / "9.9.9"
    out.mkdir(parents=True)
    (out / "otype.tf").write_text(_tf("1\tsign\n"), encoding="utf8")
    evidence = {
        "baseline": False,
        "tfVersion": "9.9.9",
        "predecessorVersion": "9.9.8",
        "predecessorDigest": "sha256:" + "b" * 64,
        "expectedChanges": ["main:*.tf"],
        "actualChanges": ["main:*.tf"],
    }
    manifest = _v4_manifest(out, evidence=evidence)
    stamp.write(
        out,
        "0.3",
        "9.9.9",
        certification=manifest,
        mode="regression-valid",
        commit="a" * 40,
    )
    problem = stamp.check(out, require_full=True)
    assert problem and "predecessor" in problem.lower() and "invalid" in problem.lower()
