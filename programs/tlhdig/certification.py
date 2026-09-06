"""Full release certification for one immutable Text-Fabric artifact.

The old BUILD-COMPLETE stamp proved that the bytes had passed census.py. A release
needs a stronger statement: a named set of independent gates all passed against the
same artifact, with the source/reference identities and known-defect policy recorded.

This module contains no subprocess policy. The command-line orchestrator supplies a
runner, which keeps the state machine small and adversarially testable.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Callable, Mapping, Sequence

from . import release_policy, stamp

MANIFEST = stamp.CERTIFICATION
MODES = release_policy.MODES
PASSED = "passed"


@dataclass(frozen=True)
class Gate:
    name: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class GateOutcome:
    status: str
    returncode: int


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return "sha256:" + h.hexdigest()


def _hash_inputs(input_files: Mapping[str, Path]) -> dict[str, str]:
    return {
        name: _sha256_file(Path(path))
        for name, path in sorted(input_files.items())
    }


def _json_bytes(payload: Mapping) -> bytes:
    return (json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf8")


def _write_json(path: Path, payload: Mapping) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(payload))


def _base_payload(
    *,
    mode: str,
    source_version: str,
    tf_version: str,
    code_commit: str,
    digest: str,
    features: int,
    inputs: Mapping[str, str],
    known_defects: Mapping[str, int],
    gates: Sequence[Gate],
) -> dict:
    return {
        "schema": 1,
        "policy": release_policy.POLICY,
        "mode": mode,
        "sourceVersion": source_version,
        "tfVersion": tf_version,
        "codeCommit": code_commit,
        "dataset": {"digest": f"sha256:{digest}", "features": features},
        "inputs": dict(sorted(inputs.items())),
        "knownDefects": dict(sorted(known_defects.items())),
        "requiredGates": [gate.name for gate in gates],
        "gates": [],
        "artifactStable": True,
        "success": False,
    }


def certify(
    *,
    out: Path,
    source_version: str,
    tf_version: str,
    mode: str,
    gates: Sequence[Gate],
    runner: Callable[[Gate], GateOutcome],
    input_files: Mapping[str, Path],
    known_defects: Mapping[str, int],
    code_commit: str,
    report_path: Path,
) -> int:
    """Run required gates and write a full BUILD-COMPLETE only on total success.

    A required gate succeeds only when it reports status ``passed`` *and* return code
    zero. This is intentionally stricter than shell convention: an external-data
    checker may use exit 0 for an explicit ordinary-CI availability skip, but a release
    must never convert that skip into a pass.
    """
    out = Path(out)
    report_path = Path(report_path)
    stamp_path = out / stamp.STAMP
    manifest_path = out / MANIFEST

    # Any failed attempt invalidates previous certification immediately. The dataset
    # digest ignores these two metadata files, so deleting them cannot perturb the
    # artifact identity we are about to check.
    for stale in (stamp_path, manifest_path):
        try:
            stale.unlink()
        except FileNotFoundError:
            pass

    if mode not in MODES:
        _write_json(report_path, {"schema": 1, "success": False, "error": f"unknown mode: {mode}"})
        return 1
    if not out.is_dir():
        _write_json(report_path, {"schema": 1, "success": False, "error": f"dataset missing: {out}"})
        return 1
    if not gates:
        _write_json(report_path, {"schema": 1, "success": False, "error": "no required gates configured"})
        return 1
    if not code_commit:
        _write_json(report_path, {"schema": 1, "success": False, "error": "code commit identity is missing"})
        return 1

    try:
        inputs = _hash_inputs(input_files)
    except OSError as exc:
        _write_json(
            report_path,
            {"schema": 1, "success": False, "error": f"cannot identify release input: {exc}"},
        )
        return 1

    before, features = stamp.digest(out)
    payload = _base_payload(
        mode=mode,
        source_version=source_version,
        tf_version=tf_version,
        code_commit=code_commit,
        digest=before,
        features=features,
        inputs=inputs,
        known_defects=known_defects,
        gates=gates,
    )

    for gate in gates:
        try:
            outcome = runner(gate)
        except Exception as exc:  # runner failure is a gate failure, never an implicit skip
            outcome = GateOutcome("failed", 1)
            payload["runnerError"] = f"{gate.name}: {type(exc).__name__}: {exc}"
        row = {
            "name": gate.name,
            "command": list(gate.command),
            "status": outcome.status,
            "returncode": int(outcome.returncode),
        }
        payload["gates"].append(row)
        if outcome.status != PASSED or outcome.returncode != 0:
            _write_json(report_path, payload)
            return 1

    after, final_features = stamp.digest(out)
    stable = before == after and features == final_features
    payload["artifactStable"] = stable
    if not stable:
        payload["finalDataset"] = {
            "digest": f"sha256:{after}",
            "features": final_features,
        }
        _write_json(report_path, payload)
        return 1

    try:
        final_inputs = _hash_inputs(input_files)
    except OSError as exc:
        payload["inputsStable"] = False
        payload["finalInputsError"] = str(exc)
        _write_json(report_path, payload)
        return 1
    inputs_stable = inputs == final_inputs
    payload["inputsStable"] = inputs_stable
    if not inputs_stable:
        payload["finalInputs"] = final_inputs
        _write_json(report_path, payload)
        return 1

    # Both modes run the same release gates. Research-ready adds a stricter policy only
    # after those gates have established the state of this exact artifact, so its failed
    # report remains a complete audit of the common release validation.
    if mode == "research-ready" and any(int(value) != 0 for value in known_defects.values()):
        payload["policyFailure"] = "research-ready requires zero designated fidelity defects"
        _write_json(report_path, payload)
        return 1

    payload["success"] = True
    # The exact successful manifest is copied to the reports directory for audit and to
    # the artifact directory for cryptographic binding by BUILD-COMPLETE.
    _write_json(manifest_path, payload)
    _write_json(report_path, payload)
    stamp.write(
        out,
        source_version,
        tf_version,
        certification=manifest_path,
        mode=mode,
        commit=code_commit,
    )
    return 0
