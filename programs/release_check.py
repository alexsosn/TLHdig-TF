#!/usr/bin/env python
"""Run every required release gate against one unchanged Text-Fabric artifact."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import SOURCE_VERSION, TF_VERSION, certification, release_policy, structure
from tlhdig.paths import PATCHES, PROGRAMS, REPORTS, ROOT

STATUS = REPORTS / "signrefs-status.json"

GATES = (
    certification.Gate("corpus-identity", ("python", "programs/check_corpus_identity.py")),
    certification.Gate("repair-manifest", ("python", "programs/verify_patches.py")),
    certification.Gate("sign-round-trip", ("python", "programs/check_signs.py")),
    certification.Gate("morphology", ("python", "programs/check_morph.py")),
    certification.Gate("structure", ("python", "programs/check_structure.py")),
    certification.Gate("contract-a-graph", ("python", "programs/check_contract_a_graph.py")),
    certification.Gate("marker-conservation", ("python", "programs/check_markers.py")),
    certification.Gate("tag-inventory", ("python", "programs/check_tags.py")),
    certification.Gate("provenance-split", ("python", "programs/check_provenance_split.py")),
    certification.Gate("alignment", ("python", "programs/check_alignment.py")),
    certification.Gate("fetch-signrefs", ("python", "programs/fetch_signrefs.py", "--mode", "release")),
    certification.Gate("check-signrefs", ("python", "programs/check_signrefs.py", "--mode", "release")),
    certification.Gate("app", ("python", "programs/check_app.py")),
    certification.Gate("census", ("python", "programs/census.py")),
    certification.Gate("code-tree-stable", ("internal", "tracked-tree")),
)

_SIGNREF_GATES = frozenset({"fetch-signrefs", "check-signrefs"})
_SHA40 = re.compile(r"^[0-9a-fA-F]{40}$")
_MUTABLE_RELEASE_PATHS = (
    ":(exclude)tf/**",
    ":(exclude)tf-provenance/**",
    ":(exclude)reports/**",
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=sorted(release_policy.MODES),
        default="regression-valid",
        help="research-ready additionally requires designated fidelity-defect baselines to be zero",
    )
    return parser


def _active_lines(path: Path) -> int:
    if not path.is_file():
        return 0
    return sum(
        1
        for line in path.read_text(encoding="utf8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def known_defects() -> dict[str, int]:
    return {
        "knownLossy": _active_lines(PROGRAMS / "known_lossy.txt"),
        "contractAKnown": _active_lines(PROGRAMS / "contract_a_known.txt"),
        "knownWordDeficit": int(structure.KNOWN_WORD_DEFICIT),
    }


def release_inputs() -> dict[str, Path]:
    return {
        "corpusManifest": PROGRAMS / "corpus.sha256",
        "repairManifest": PATCHES,
        "signrefLock": PROGRAMS / "signrefs.lock.json",
    }


def policy_problem() -> str | None:
    gate_names = tuple(gate.name for gate in GATES)
    if gate_names != release_policy.REQUIRED_GATES:
        return (
            f"configured gate names do not match {release_policy.POLICY}: "
            f"{gate_names!r} != {release_policy.REQUIRED_GATES!r}"
        )
    input_names = tuple(release_inputs())
    if input_names != release_policy.REQUIRED_INPUTS:
        return (
            f"configured input names do not match {release_policy.POLICY}: "
            f"{input_names!r} != {release_policy.REQUIRED_INPUTS!r}"
        )
    defect_names = tuple(known_defects())
    if defect_names != release_policy.FIDELITY_BASELINES:
        return (
            f"configured fidelity baselines do not match {release_policy.POLICY}: "
            f"{defect_names!r} != {release_policy.FIDELITY_BASELINES!r}"
        )
    return None


def tracked_changes() -> list[str]:
    """Return tracked source/code/config changes, excluding mutable release outputs.

    A release manifest names a commit as the code identity, so source, executable code,
    configuration and tracked inputs must still match that commit. The TF modules and
    reports are different: they are outputs that the build/certifier intentionally
    rewrites and are bound separately by the module-aware artifact digest and input/
    certification hashes. Untracked/ignored refs and caches are excluded as before.
    """
    try:
        status = subprocess.check_output(
            [
                "git",
                "status",
                "--porcelain",
                "--untracked-files=no",
                "--",
                ".",
                *_MUTABLE_RELEASE_PATHS,
            ],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        return [f"git status unavailable: {exc}"]
    return [line.strip() for line in status.splitlines() if line.strip()]


def _git_head() -> str | None:
    try:
        value = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return value.lower() if _SHA40.fullmatch(value) else None


def resolve_commit() -> str | None:
    """Resolve the code identity and reject an environment SHA that disagrees with Git.

    CI/environment metadata is useful when Git metadata is unavailable, but whenever a
    checkout has a readable HEAD that HEAD is the executable tree's identity and an
    override may not claim a different commit.
    """
    environment_commit = None
    for name in ("TLHDIG_CODE_COMMIT", "GITHUB_SHA"):
        value = (os.environ.get(name) or "").strip()
        if _SHA40.fullmatch(value):
            environment_commit = value.lower()
            break

    head = _git_head()
    if head is not None:
        if environment_commit is not None and environment_commit != head:
            return None
        return environment_commit or head
    return environment_commit


def _signref_state() -> str | None:
    if not STATUS.is_file():
        return None
    try:
        payload = json.loads(STATUS.read_text(encoding="utf8"))
    except (OSError, json.JSONDecodeError):
        return "failed"
    state = payload.get("state") if isinstance(payload, dict) else None
    return state if isinstance(state, str) else "failed"


def run_gate(
    gate: certification.Gate, *, expected_commit: str | None = None
) -> certification.GateOutcome:
    print(f"\n=== release gate: {gate.name} ===", flush=True)

    if gate.name == "code-tree-stable":
        dirty = tracked_changes()
        if dirty:
            print("tracked source/code/config tree changed during release validation")
            for change in dirty[:20]:
                print(f"  {change}")
            return certification.GateOutcome("failed", 1)
        head = _git_head()
        if expected_commit is None or head != expected_commit.lower():
            print(
                "Git HEAD changed during release validation: "
                f"expected {expected_commit or '<missing>'}, got {head or '<unavailable>'}"
            )
            return certification.GateOutcome("failed", 1)
        return certification.GateOutcome("passed", 0)

    if gate.name in _SIGNREF_GATES:
        # A status file from a previous command must never bless this invocation.
        try:
            STATUS.unlink()
        except FileNotFoundError:
            pass
    command = list(gate.command)
    if command and command[0] == "python":
        command[0] = sys.executable
    try:
        result = subprocess.run(command, cwd=ROOT, check=False)
    except OSError as exc:
        print(f"gate execution failed: {exc}")
        return certification.GateOutcome("failed", 1)

    if gate.name in _SIGNREF_GATES:
        state = _signref_state()
        if state is None:
            # Missing explicit state is a validation failure even if the process says 0.
            state = "failed"
        return certification.GateOutcome(state, result.returncode)
    return certification.GateOutcome(
        "passed" if result.returncode == 0 else "failed", result.returncode
    )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    problem = policy_problem()
    if problem:
        print(f"release certification configuration failed: {problem}")
        return 1

    dirty = tracked_changes()
    if dirty:
        print(
            "release certification failed: tracked source/code/config tree differs "
            "from the recorded commit"
        )
        for change in dirty[:20]:
            print(f"  {change}")
        return 1

    out = ROOT / "tf" / TF_VERSION
    commit = resolve_commit()
    if commit is None:
        print(
            "release certification failed: cannot resolve a 40-character code commit "
            "SHA consistent with Git HEAD"
        )
        return 1

    defects = known_defects()
    print(
        f"release certification policy={release_policy.POLICY} mode={args.mode} "
        f"source={SOURCE_VERSION} tf={TF_VERSION} commit={commit[:12]}..."
    )
    print("known fidelity baselines: " + ", ".join(f"{k}={v}" for k, v in defects.items()))

    rc = certification.certify(
        out=out,
        source_version=SOURCE_VERSION,
        tf_version=TF_VERSION,
        mode=args.mode,
        gates=GATES,
        runner=lambda gate: run_gate(gate, expected_commit=commit),
        input_files=release_inputs(),
        known_defects=defects,
        code_commit=commit,
        report_path=REPORTS / "release-certification.json",
    )
    if rc:
        print("\nRELEASE CERTIFICATION FAILED -- BUILD-COMPLETE was not written")
        return rc
    print(f"\nrelease certified: {out / certification.MANIFEST}")
    print(f"BUILD-COMPLETE now certifies the full {args.mode} gate run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
