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

from tlhdig import SOURCE_VERSION, TF_VERSION, certification, structure
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
)

_SIGNREF_GATES = frozenset({"fetch-signrefs", "check-signrefs"})
_SHA40 = re.compile(r"^[0-9a-fA-F]{40}$")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("regression-valid", "research-ready"),
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


def resolve_commit() -> str | None:
    for name in ("TLHDIG_CODE_COMMIT", "GITHUB_SHA"):
        value = (os.environ.get(name) or "").strip()
        if _SHA40.fullmatch(value):
            return value.lower()
    try:
        value = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return value.lower() if _SHA40.fullmatch(value) else None


def _signref_state() -> str | None:
    if not STATUS.is_file():
        return None
    try:
        payload = json.loads(STATUS.read_text(encoding="utf8"))
    except (OSError, json.JSONDecodeError):
        return "failed"
    state = payload.get("state") if isinstance(payload, dict) else None
    return state if isinstance(state, str) else "failed"


def run_gate(gate: certification.Gate) -> certification.GateOutcome:
    if gate.name in _SIGNREF_GATES:
        # A status file from a previous command must never bless this invocation.
        try:
            STATUS.unlink()
        except FileNotFoundError:
            pass
    command = list(gate.command)
    if command and command[0] == "python":
        command[0] = sys.executable
    print(f"\n=== release gate: {gate.name} ===", flush=True)
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
    out = ROOT / "tf" / TF_VERSION
    commit = resolve_commit()
    if commit is None:
        print("release certification failed: cannot resolve a 40-character code commit SHA")
        return 1

    defects = known_defects()
    print(
        f"release certification mode={args.mode} source={SOURCE_VERSION} tf={TF_VERSION} "
        f"commit={commit[:12]}..."
    )
    print("known fidelity baselines: " + ", ".join(f"{k}={v}" for k, v in defects.items()))

    rc = certification.certify(
        out=out,
        source_version=SOURCE_VERSION,
        tf_version=TF_VERSION,
        mode=args.mode,
        gates=GATES,
        runner=run_gate,
        input_files={
            "corpusManifest": PROGRAMS / "corpus.sha256",
            "repairManifest": PATCHES,
            "signrefLock": PROGRAMS / "signrefs.lock.json",
        },
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
