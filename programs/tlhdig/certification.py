"""Full release certification for one immutable Text-Fabric artifact.

A release records a named set of independent gates against the same artifact and release
inputs.  Release-v6 additionally records a Git-backed protected-tree identity before the
gates and requires the same clean identity afterwards, so later source/config/code drift
cannot inherit stale evidence merely because TF bytes stayed unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Callable, Mapping, Sequence

from . import protected_tree, release_policy, stamp

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
    evidence: Mapping[str, object] | None = None


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
    policy_name: str,
    contract: release_policy.PolicyContract,
    mode: str,
    source_version: str,
    tf_version: str,
    code_commit: str,
    digest: str,
    features: int,
    inputs: Mapping[str, str],
    known_defects: Mapping[str, int],
    gates: Sequence[Gate],
    protected_identity: Mapping[str, str] | None,
) -> dict:
    payload = {
        "schema": contract.manifest_schema,
        "policy": policy_name,
        "mode": mode,
        "sourceVersion": source_version,
        "tfVersion": tf_version,
        "codeCommit": code_commit,
        "dataset": {
            "algorithm": release_policy.ARTIFACT_DIGEST_ALGORITHM,
            "digest": f"sha256:{digest}",
            "features": features,
        },
        "inputs": dict(sorted(inputs.items())),
        "knownDefects": dict(sorted(known_defects.items())),
        "requiredGates": [gate.name for gate in gates],
        "gates": [],
        "artifactStable": True,
        "success": False,
    }
    if protected_identity is not None:
        payload["protectedTree"] = dict(protected_identity)
    return payload


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
    repo_root: Path | None = None,
) -> int:
    """Run required gates and write a full BUILD-COMPLETE only on total success.

    The state machine deliberately permits non-canonical gate lists for focused tests;
    the full verifier rejects them as publication evidence.  Under a protected-tree
    policy, canonical certification always requires explicit Git repository context.
    Focused non-canonical calls may omit it, but the resulting manifest is intentionally
    non-publishable because it lacks protected-tree evidence.
    """
    out = Path(out)
    report_path = Path(report_path)
    stamp_path = out / stamp.STAMP
    manifest_path = out / MANIFEST
    policy_name = release_policy.POLICY
    contract = release_policy.policy_contract(policy_name)
    if contract is None:  # a programming/configuration error must fail closed
        _write_json(
            report_path,
            {"schema": 1, "success": False, "error": f"unknown release policy: {policy_name}"},
        )
        return 1
    schema = contract.manifest_schema
    canonical = tuple(gate.name for gate in gates) == contract.required_gates

    for stale in (stamp_path, manifest_path):
        try:
            stale.unlink()
        except FileNotFoundError:
            pass

    def fail(error: str, **extra) -> int:
        payload = {"schema": schema, "policy": policy_name, "success": False, "error": error}
        payload.update(extra)
        _write_json(report_path, payload)
        return 1

    if mode not in MODES:
        return fail(f"unknown mode: {mode}")
    if not out.is_dir():
        return fail(f"dataset missing: {out}")
    if not gates:
        return fail("no required gates configured")
    if not code_commit:
        return fail("code commit identity is missing")

    protected_identity = None
    if contract.protected_tree_algorithm or contract.protected_tree_profile:
        if repo_root is None:
            if canonical:
                return fail("protected-tree certification requires explicit repository root")
        else:
            try:
                protected_identity = protected_tree.identity(
                    Path(repo_root),
                    profile=contract.protected_tree_profile or "",
                )
            except protected_tree.ProtectedTreeError as exc:
                return fail(f"cannot identify protected tree before gates: {exc}")
            if (
                protected_identity.get("algorithm") != contract.protected_tree_algorithm
                or protected_identity.get("profile") != contract.protected_tree_profile
            ):
                return fail("protected-tree implementation disagrees with release policy")

    try:
        inputs = _hash_inputs(input_files)
    except OSError as exc:
        return fail(f"cannot identify release input: {exc}")

    before, features = stamp.full_digest(out)
    payload = _base_payload(
        policy_name=policy_name,
        contract=contract,
        mode=mode,
        source_version=source_version,
        tf_version=tf_version,
        code_commit=code_commit,
        digest=before,
        features=features,
        inputs=inputs,
        known_defects=known_defects,
        gates=gates,
        protected_identity=protected_identity,
    )

    for gate in gates:
        try:
            outcome = runner(gate)
        except Exception as exc:
            outcome = GateOutcome("failed", 1)
            payload["runnerError"] = f"{gate.name}: {type(exc).__name__}: {exc}"
        row = {
            "name": gate.name,
            "command": list(gate.command),
            "status": outcome.status,
            "returncode": int(outcome.returncode),
        }
        if outcome.evidence is not None:
            row["evidence"] = dict(outcome.evidence)
        payload["gates"].append(row)
        if outcome.status != PASSED or outcome.returncode != 0:
            _write_json(report_path, payload)
            return 1

    after, final_features = stamp.full_digest(out)
    stable = before == after and features == final_features
    payload["artifactStable"] = stable
    if not stable:
        payload["finalDataset"] = {
            "algorithm": release_policy.ARTIFACT_DIGEST_ALGORITHM,
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

    if protected_identity is not None:
        try:
            final_protected = protected_tree.identity(
                Path(repo_root),
                profile=contract.protected_tree_profile or "",
            )
        except protected_tree.ProtectedTreeError as exc:
            payload["protectedTreeStable"] = False
            payload["protectedTreeError"] = str(exc)
            _write_json(report_path, payload)
            return 1
        protected_stable = final_protected == protected_identity
        payload["protectedTreeStable"] = protected_stable
        if not protected_stable:
            payload["finalProtectedTree"] = final_protected
            _write_json(report_path, payload)
            return 1

    if mode == "research-ready" and any(int(value) != 0 for value in known_defects.values()):
        payload["policyFailure"] = "research-ready requires zero designated fidelity defects"
        _write_json(report_path, payload)
        return 1

    payload["success"] = True
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
