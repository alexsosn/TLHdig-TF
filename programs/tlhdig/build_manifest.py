"""Direct identity and verification for the one current pre-alpha TF artifact."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Mapping, Sequence

MANIFEST = "BUILD-MANIFEST.json"
SCHEMA = 1
OUTPUT_ALGORITHM = "tlhdig-current-tree-v1"
CODE_ALGORITHM = "tlhdig-current-code-v1"

_SHA40 = re.compile(r"^[0-9a-fA-F]{40}$")


class ManifestError(ValueError):
    """The current build cannot be identified safely."""


def _sha256(path: Path) -> str:
    path = Path(path)
    if path.is_symlink():
        raise ManifestError(f"symlink is not allowed in build identity: {path}")
    if not path.is_file():
        raise ManifestError(f"identity input is missing or not a regular file: {path}")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def _relative(path: Path, root: Path) -> str:
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError as exc:
        raise ManifestError(f"path is outside repository root: {path}") from exc


def _identity(algorithm: str, files: Mapping[str, Path]) -> dict[str, object]:
    h = hashlib.sha256()
    h.update(algorithm.encode("utf8"))
    h.update(b"\0")
    digests: dict[str, str] = {}
    for name, path in sorted(files.items()):
        if not isinstance(name, str) or not name or "\0" in name:
            raise ManifestError(f"invalid logical identity path: {name!r}")
        digest = _sha256(Path(path))
        digests[name] = digest
        h.update(name.encode("utf8"))
        h.update(b"\0")
        h.update(digest.encode("ascii"))
        h.update(b"\0")
    return {
        "algorithm": algorithm,
        "digest": "sha256:" + h.hexdigest(),
        "files": digests,
    }


def code_identity(code_files: Mapping[str, Path] | None = None) -> dict[str, object]:
    """Hash the executable/config files that define the current conversion/validation."""
    return _identity(CODE_ALGORITHM, code_files or {})


def _module_files(directory: Path, label: str, *, required: bool) -> dict[str, Path]:
    directory = Path(directory)
    if not directory.exists():
        if required:
            raise ManifestError(f"current {label} module is missing: {directory}")
        return {}
    if directory.is_symlink() or not directory.is_dir():
        raise ManifestError(f"current {label} module is not a regular directory: {directory}")

    files: dict[str, Path] = {}
    for path in sorted(directory.rglob("*"), key=lambda p: p.as_posix()):
        rel = path.relative_to(directory)
        if path.is_symlink():
            raise ManifestError(f"symlink is not allowed in current output: {path}")
        if ".tf" in rel.parts:
            # Text-Fabric's compiled cache is derived, platform-specific output.
            continue
        if path.is_dir():
            continue
        if not path.is_file():
            raise ManifestError(f"non-regular current output is not allowed: {path}")
        if label == "main" and rel.as_posix() == MANIFEST:
            continue
        files[f"{label}:{rel.as_posix()}"] = path
    return files


def output_identity(main_dir: Path, provenance_dir: Path) -> dict[str, object]:
    """Return a closed-world, module-aware identity for the current generated output."""
    files = _module_files(Path(main_dir), "main", required=True)
    files.update(_module_files(Path(provenance_dir), "provenance", required=False))
    return _identity(OUTPUT_ALGORITHM, files)


def input_identities(input_files: Mapping[str, Path]) -> dict[str, str]:
    """Return exact SHA-256 identities for named reproducibility inputs."""
    identities: dict[str, str] = {}
    for name, path in sorted(input_files.items()):
        if not isinstance(name, str) or not name:
            raise ManifestError(f"invalid input name: {name!r}")
        identities[name] = _sha256(Path(path))
    return identities


def _paths(main_dir: Path, provenance_dir: Path, root: Path) -> dict[str, str]:
    return {
        "main": _relative(main_dir, root),
        "provenance": _relative(provenance_dir, root),
    }


def _payload(
    *,
    source_version: str,
    tf_version: str,
    code_commit: str,
    main_dir: Path,
    provenance_dir: Path,
    input_files: Mapping[str, Path],
    code_files: Mapping[str, Path] | None,
    gate_names: Sequence[str],
    root: Path,
) -> dict[str, object]:
    if not _SHA40.fullmatch(code_commit):
        raise ManifestError("codeCommit must be a full 40-character Git SHA")
    names = list(gate_names)
    if any(not isinstance(name, str) or not name for name in names):
        raise ManifestError("validation gate names must be non-empty strings")
    if len(names) != len(set(names)):
        raise ManifestError("validation gate names must be unique")
    return {
        "schema": SCHEMA,
        "sourceVersion": source_version,
        "tfVersion": tf_version,
        "codeCommit": code_commit.lower(),
        "paths": _paths(main_dir, provenance_dir, root),
        "inputs": input_identities(input_files),
        "code": code_identity(code_files),
        "outputs": output_identity(main_dir, provenance_dir),
        "validation": {"success": True, "gates": names},
    }


def write_manifest(
    path: Path,
    *,
    source_version: str,
    tf_version: str,
    code_commit: str,
    main_dir: Path,
    provenance_dir: Path,
    input_files: Mapping[str, Path],
    gate_names: Sequence[str],
    root: Path,
    code_files: Mapping[str, Path] | None = None,
) -> None:
    """Write the current build manifest atomically after validation has succeeded."""
    path = Path(path)
    main_dir = Path(main_dir)
    expected = main_dir / MANIFEST
    if path != expected:
        raise ManifestError(f"manifest must be written at {expected}")
    payload = _payload(
        source_version=source_version,
        tf_version=tf_version,
        code_commit=code_commit,
        main_dir=main_dir,
        provenance_dir=Path(provenance_dir),
        input_files=input_files,
        code_files=code_files,
        gate_names=gate_names,
        root=Path(root),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf8",
    )
    temporary.replace(path)


def _sha256_problem(value: object, where: str) -> str | None:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        return f"{where} is not a SHA-256 identity"
    digest = value[7:]
    if len(digest) != 64:
        return f"{where} is not a SHA-256 identity"
    try:
        int(digest, 16)
    except ValueError:
        return f"{where} is not a SHA-256 identity"
    return None


def _identity_problem(
    recorded: object,
    actual: dict[str, object],
    *,
    label: str,
    algorithm: str,
) -> str | None:
    if not isinstance(recorded, dict):
        return f"manifest has no {label} identity"
    if recorded.get("algorithm") != algorithm:
        return f"manifest {label} identity uses the wrong algorithm"
    problem = _sha256_problem(recorded.get("digest"), f"manifest {label} digest")
    if problem:
        return problem
    files = recorded.get("files")
    if not isinstance(files, dict):
        return f"manifest has no {label} file identities"
    if any(not isinstance(k, str) or _sha256_problem(v, f"{label} file {k}") for k, v in files.items()):
        return f"manifest contains an invalid {label} file identity"
    if recorded != actual:
        return f"current {label} identity does not match BUILD-MANIFEST.json"
    return None


def verify_manifest(
    path: Path,
    *,
    source_version: str,
    tf_version: str,
    main_dir: Path,
    provenance_dir: Path,
    input_files: Mapping[str, Path],
    gate_names: Sequence[str],
    root: Path,
    code_files: Mapping[str, Path] | None = None,
) -> str | None:
    """Return a problem description, or None when the current manifest matches reality."""
    path = Path(path)
    if path.is_symlink():
        return f"{MANIFEST} must not be a symlink"
    if not path.is_file():
        return f"{MANIFEST} is missing; run programs/validate_current.py"
    try:
        payload = json.loads(path.read_text(encoding="utf8"))
    except (OSError, json.JSONDecodeError) as exc:
        return f"{MANIFEST} is unreadable: {exc}"
    if not isinstance(payload, dict):
        return f"{MANIFEST} must contain a JSON object"
    if payload.get("schema") != SCHEMA:
        return f"{MANIFEST} has unsupported schema {payload.get('schema')!r}"
    if payload.get("sourceVersion") != source_version:
        return f"{MANIFEST} describes a different source version"
    if payload.get("tfVersion") != tf_version:
        return f"{MANIFEST} describes a different TF version"
    code_commit = payload.get("codeCommit")
    if not isinstance(code_commit, str) or not _SHA40.fullmatch(code_commit):
        return f"{MANIFEST} has an invalid codeCommit"

    try:
        expected_paths = _paths(main_dir, provenance_dir, root)
    except ManifestError as exc:
        return str(exc)
    if payload.get("paths") != expected_paths:
        return f"{MANIFEST} describes different current artifact paths"

    validation = payload.get("validation")
    expected_gates = list(gate_names)
    if validation != {"success": True, "gates": expected_gates}:
        return f"{MANIFEST} validation gate contract does not match the current validator"

    try:
        actual_inputs = input_identities(input_files)
    except ManifestError as exc:
        return f"current input identity cannot be computed: {exc}"
    recorded_inputs = payload.get("inputs")
    if not isinstance(recorded_inputs, dict):
        return f"{MANIFEST} has no input identities"
    if any(
        not isinstance(name, str) or _sha256_problem(value, f"input {name}")
        for name, value in recorded_inputs.items()
    ):
        return f"{MANIFEST} contains an invalid input identity"
    if recorded_inputs != actual_inputs:
        return f"current input identity does not match {MANIFEST}"

    try:
        actual_code = code_identity(code_files)
    except ManifestError as exc:
        return f"current code identity cannot be computed: {exc}"
    problem = _identity_problem(
        payload.get("code"),
        actual_code,
        label="code",
        algorithm=CODE_ALGORITHM,
    )
    if problem:
        return problem

    try:
        actual_outputs = output_identity(main_dir, provenance_dir)
    except ManifestError as exc:
        return f"current output identity cannot be computed: {exc}"
    problem = _identity_problem(
        payload.get("outputs"),
        actual_outputs,
        label="output",
        algorithm=OUTPUT_ALGORITHM,
    )
    if problem:
        return problem
    return None
