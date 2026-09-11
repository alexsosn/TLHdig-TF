#!/usr/bin/env python
"""Validate the one current pre-alpha Text-Fabric build and write its manifest."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Callable, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import PROVENANCE_DIR, SOURCE_VERSION, TF_VERSION, build_manifest
from tlhdig.paths import PATCHES, PROGRAMS, REPORTS, ROOT

STATUS = REPORTS / "signrefs-status.json"


@dataclass(frozen=True)
class Gate:
    name: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class GateOutcome:
    status: str
    returncode: int


GATES = (
    Gate("corpus-identity", ("python", "programs/check_corpus_identity.py")),
    Gate("repair-manifest", ("python", "programs/verify_patches.py")),
    Gate("sign-round-trip", ("python", "programs/check_signs.py")),
    Gate("morphology", ("python", "programs/check_morph.py")),
    Gate("structure", ("python", "programs/check_structure.py")),
    Gate("sign-language", ("python", "programs/check_sign_language.py")),
    Gate("manuscript-joins", ("python", "programs/check_manuscript_joins.py")),
    Gate("contract-a-graph", ("python", "programs/check_contract_a_graph.py")),
    Gate("marker-conservation", ("python", "programs/check_markers.py")),
    Gate("tag-inventory", ("python", "programs/check_tags.py")),
    Gate("provenance-split", ("python", "programs/check_provenance_split.py")),
    Gate("alignment", ("python", "programs/check_alignment.py")),
    Gate("fetch-signrefs", ("python", "programs/fetch_signrefs.py", "--mode", "release")),
    Gate("check-signrefs", ("python", "programs/check_signrefs.py", "--mode", "release")),
    Gate("app", ("python", "programs/check_app.py")),
    Gate("census", ("python", "programs/census.py")),
)

_SIGNREF_GATES = frozenset({"fetch-signrefs", "check-signrefs"})
_SHA40 = re.compile(r"^[0-9a-fA-F]{40}$")
_MUTABLE_OUTPUT_PATHS = (
    ":(exclude)tf/**",
    ":(exclude)tf-provenance/**",
    ":(exclude)reports/**",
)


def current_inputs() -> dict[str, Path]:
    """Named data/policy inputs that affect the current build or its validation."""
    return {
        "corpusManifest": PROGRAMS / "corpus.sha256",
        "repairManifest": PATCHES,
        "exclusions": PROGRAMS / "excluded.txt",
        "knownLossy": PROGRAMS / "known_lossy.txt",
        "contractAKnown": PROGRAMS / "contract_a_known.txt",
        "signMap": PROGRAMS / "signmap.tsv",
        "signMapMulti": PROGRAMS / "signmap-multi.tsv",
        "signrefLock": PROGRAMS / "signrefs.lock.json",
        "dependencies": ROOT / "requirements.txt",
    }


def current_code_files() -> dict[str, Path]:
    """Executable/config files whose edits make a committed current build stale."""
    paths = {
        ROOT / "programs" / "build.py",
        ROOT / "programs" / "validate_current.py",
        ROOT / "programs" / "check_build_manifest.py",
        ROOT / "app" / "config.yaml",
    }
    for gate in GATES:
        command = gate.command
        if len(command) >= 2 and command[0] == "python":
            paths.add(ROOT / command[1])
    paths.update((PROGRAMS / "tlhdig").glob("*.py"))
    return {
        path.relative_to(ROOT).as_posix(): path
        for path in sorted(paths, key=lambda p: p.as_posix())
    }


def tracked_changes() -> list[str]:
    """Return tracked source/code/config changes, excluding generated current outputs."""
    try:
        status = subprocess.check_output(
            [
                "git",
                "status",
                "--porcelain",
                "--untracked-files=no",
                "--",
                ".",
                *_MUTABLE_OUTPUT_PATHS,
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
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return value.lower() if _SHA40.fullmatch(value) else None


def resolve_commit() -> str | None:
    """Resolve source-commit provenance independently from the validation checkout."""
    for name in ("TLHDIG_CODE_COMMIT", "GITHUB_SHA"):
        value = (os.environ.get(name) or "").strip()
        if not value:
            continue
        return value.lower() if _SHA40.fullmatch(value) else None
    return _git_head()


def _signref_state() -> str | None:
    if not STATUS.is_file():
        return None
    try:
        payload = json.loads(STATUS.read_text(encoding="utf8"))
    except (OSError, json.JSONDecodeError):
        return "failed"
    state = payload.get("state") if isinstance(payload, dict) else None
    return state if isinstance(state, str) else "failed"


def run_gate(gate: Gate) -> GateOutcome:
    """Run one substantive validator; external-data skips remain explicit failures."""
    print(f"\n=== current build gate: {gate.name} ===", flush=True)
    if gate.name in _SIGNREF_GATES:
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
        return GateOutcome("failed", 1)

    if gate.name in _SIGNREF_GATES:
        state = _signref_state()
        if state is None:
            state = "failed"
        return GateOutcome(state, result.returncode)
    return GateOutcome("passed" if result.returncode == 0 else "failed", result.returncode)


def _remove_manifest(main_dir: Path) -> None:
    try:
        (Path(main_dir) / build_manifest.MANIFEST).unlink()
    except FileNotFoundError:
        pass


def validate(
    *,
    main_dir: Path,
    provenance_dir: Path,
    source_version: str,
    tf_version: str,
    code_commit: str,
    gates: Sequence[Gate],
    runner: Callable[[Gate], GateOutcome],
    input_files: Mapping[str, Path],
    root: Path,
    tracked_changes: Callable[[], list[str]],
    current_head: Callable[[], str | None],
    code_files: Mapping[str, Path] | None = None,
) -> int:
    """Validate one stable build and write a manifest only after every gate passes."""
    main_dir = Path(main_dir)
    provenance_dir = Path(provenance_dir)
    root = Path(root)
    code_files = code_files or {}
    _remove_manifest(main_dir)

    dirty = tracked_changes()
    if dirty:
        print("current build validation failed: tracked source/code/config tree is dirty")
        for change in dirty[:20]:
            print(f"  {change}")
        return 1

    # A pull_request workflow validates GitHub's synthetic merge checkout while the
    # durable provenance commit is the PR's real source head. The exact executable bytes
    # are bound separately by code_identity; here HEAD is only the checkout-stability
    # sentinel and therefore need not equal code_commit.
    start_head = current_head()
    if start_head is None:
        print("current build validation failed: cannot resolve validation checkout Git HEAD")
        return 1

    try:
        inputs_before = build_manifest.input_identities(input_files)
        code_before = build_manifest.code_identity(code_files)
        outputs_before = build_manifest.output_identity(main_dir, provenance_dir)
    except build_manifest.ManifestError as exc:
        print(f"current build validation failed before gates: {exc}")
        return 1

    for gate in gates:
        try:
            outcome = runner(gate)
        except Exception as exc:
            print(f"current build validation failed at {gate.name}: runner error: {exc}")
            return 1
        if outcome.status != "passed" or outcome.returncode != 0:
            print(
                f"current build validation failed at {gate.name}: "
                f"status={outcome.status} returncode={outcome.returncode}"
            )
            return 1

    try:
        inputs_after = build_manifest.input_identities(input_files)
        code_after = build_manifest.code_identity(code_files)
        outputs_after = build_manifest.output_identity(main_dir, provenance_dir)
    except build_manifest.ManifestError as exc:
        print(f"current build validation failed after gates: {exc}")
        return 1

    if inputs_after != inputs_before:
        print("current build validation failed: reproducibility/validation inputs changed during gates")
        return 1
    if code_after != code_before:
        print("current build validation failed: executable/config identity changed during gates")
        return 1
    if outputs_after != outputs_before:
        print("current build validation failed: generated output changed during gates")
        return 1

    dirty = tracked_changes()
    if dirty:
        print("current build validation failed: tracked source/code/config tree changed during gates")
        for change in dirty[:20]:
            print(f"  {change}")
        return 1
    end_head = current_head()
    if end_head is None or end_head.lower() != start_head.lower():
        print(
            "current build validation failed: validation checkout Git HEAD changed during gates "
            f"({start_head} != {end_head or '<unavailable>'})"
        )
        return 1

    names = tuple(gate.name for gate in gates)
    manifest_path = main_dir / build_manifest.MANIFEST
    try:
        build_manifest.write_manifest(
            manifest_path,
            source_version=source_version,
            tf_version=tf_version,
            code_commit=code_commit,
            main_dir=main_dir,
            provenance_dir=provenance_dir,
            input_files=input_files,
            code_files=code_files,
            gate_names=names,
            root=root,
        )
        problem = build_manifest.verify_manifest(
            manifest_path,
            source_version=source_version,
            tf_version=tf_version,
            main_dir=main_dir,
            provenance_dir=provenance_dir,
            input_files=input_files,
            code_files=code_files,
            gate_names=names,
            root=root,
        )
    except build_manifest.ManifestError as exc:
        _remove_manifest(main_dir)
        print(f"current build validation failed while writing manifest: {exc}")
        return 1
    if problem:
        _remove_manifest(main_dir)
        print(f"current build validation failed after manifest write: {problem}")
        return 1
    return 0


def main() -> int:
    main_dir = ROOT / "tf" / TF_VERSION
    provenance_dir = ROOT / PROVENANCE_DIR / TF_VERSION
    commit = resolve_commit()
    if commit is None:
        print(
            "current build validation failed: cannot resolve a 40-character source "
            "commit for manifest provenance"
        )
        return 1

    rc = validate(
        main_dir=main_dir,
        provenance_dir=provenance_dir,
        source_version=SOURCE_VERSION,
        tf_version=TF_VERSION,
        code_commit=commit,
        gates=GATES,
        runner=run_gate,
        input_files=current_inputs(),
        code_files=current_code_files(),
        root=ROOT,
        tracked_changes=tracked_changes,
        current_head=_git_head,
    )
    if rc:
        print(f"\nCURRENT BUILD VALIDATION FAILED -- {build_manifest.MANIFEST} was not written")
        return rc
    print(f"\ncurrent build validated: {main_dir / build_manifest.MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
