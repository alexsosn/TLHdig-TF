"""The BUILD-COMPLETE stamp, bound to artifact bytes and release evidence.

Legacy stamps contain only a digest of every shipped `.tf` file. They remain readable
so historical releases can be checked without rewriting them. New releases add a hash
of `RELEASE-CERTIFICATION.json`, which records the complete required-gate run, source
identities, code commit and known-defect policy.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

STAMP = "BUILD-COMPLETE"
CERTIFICATION = "RELEASE-CERTIFICATION.json"


def _module_dir(out: Path) -> Path:
    from . import PROVENANCE_DIR

    return out.parent.parent / PROVENANCE_DIR / out.name


def digest(out: Path) -> tuple[str, int]:
    """SHA-256 over every .tf file's name and content. Returns (hex, file count).

    Covers the provenance module as well: the two halves are one build. The release
    manifest and BUILD-COMPLETE themselves are deliberately excluded so certification
    metadata cannot change the artifact identity it describes.
    """
    h = hashlib.sha256()
    files = sorted((p for p in out.glob("*.tf") if p.is_file()), key=lambda p: p.name)
    prov = _module_dir(out)
    if prov.is_dir():
        files += sorted((p for p in prov.glob("*.tf") if p.is_file()), key=lambda p: p.name)
    for p in files:
        # Keep the historical digest algorithm unchanged so old release stamps remain
        # verifiable. Main files are always hashed before provenance files, so the
        # module ordering itself is stable even when a feature name exists in both.
        h.update(p.name.encode("utf8"))
        h.update(b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest(), len(files)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(
    out: Path,
    source_version: str,
    tf_version: str,
    *,
    certification: Path | None = None,
    mode: str | None = None,
    commit: str | None = None,
) -> str:
    """Write a legacy digest stamp or, when supplied, a full certification stamp."""
    d, n = digest(out)
    lines = [
        f"sourceVersion={source_version}",
        f"tfVersion={tf_version}",
        f"features={n}",
        f"digest=sha256:{d}",
    ]
    if certification is not None:
        certification = Path(certification)
        if not certification.is_file():
            raise ValueError(f"certification manifest is missing: {certification}")
        if not mode or not commit:
            raise ValueError("full certification stamp requires mode and commit")
        lines.extend(
            [
                f"certification=sha256:{_file_sha256(certification)}",
                f"mode={mode}",
                f"commit={commit}",
            ]
        )
    (out / STAMP).write_text("\n".join(lines) + "\n", encoding="utf8")
    return d


def read(out: Path) -> dict[str, str]:
    path = out / STAMP
    if not path.is_file():
        return {}
    fields = {}
    for line in path.read_text(encoding="utf8").splitlines():
        key, _, value = line.partition("=")
        if key:
            fields[key.strip()] = value.strip()
    return fields


def _check_full(out: Path, fields: dict[str, str], actual: str, n: int) -> str | None:
    claimed_cert = fields.get("certification", "")
    if not claimed_cert.startswith("sha256:"):
        return f"{STAMP} is legacy census-only certification; run programs/release_check.py"
    manifest_path = out / CERTIFICATION
    if not manifest_path.is_file():
        return f"{CERTIFICATION} is missing"
    actual_cert = _file_sha256(manifest_path)
    if claimed_cert[7:] != actual_cert:
        return (
            f"{STAMP} does not match {CERTIFICATION}: it certifies "
            f"{claimed_cert[7:][:12]}..., manifest hashes to {actual_cert[:12]}..."
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf8"))
    except (OSError, json.JSONDecodeError) as exc:
        return f"{CERTIFICATION} is unreadable: {exc}"
    if not isinstance(manifest, dict) or manifest.get("schema") != 1:
        return f"{CERTIFICATION} has unsupported schema"
    if manifest.get("success") is not True:
        return f"{CERTIFICATION} does not record a successful certification"
    if manifest.get("artifactStable") is not True:
        return f"{CERTIFICATION} does not record a stable artifact"

    dataset = manifest.get("dataset")
    if not isinstance(dataset, dict):
        return f"{CERTIFICATION} has no dataset identity"
    if dataset.get("digest") != f"sha256:{actual}" or dataset.get("features") != n:
        return f"{CERTIFICATION} describes different dataset bytes"
    if manifest.get("sourceVersion") != fields.get("sourceVersion"):
        return f"{CERTIFICATION} sourceVersion differs from {STAMP}"
    if manifest.get("tfVersion") != fields.get("tfVersion"):
        return f"{CERTIFICATION} tfVersion differs from {STAMP}"
    if manifest.get("mode") != fields.get("mode"):
        return f"{CERTIFICATION} mode differs from {STAMP}"
    if manifest.get("codeCommit") != fields.get("commit"):
        return f"{CERTIFICATION} code commit differs from {STAMP}"

    required = manifest.get("requiredGates")
    gates = manifest.get("gates")
    if not isinstance(required, list) or not required:
        return f"{CERTIFICATION} has no required gate set"
    if not isinstance(gates, list):
        return f"{CERTIFICATION} has no gate results"
    names = [row.get("name") for row in gates if isinstance(row, dict)]
    if names != required:
        return f"{CERTIFICATION} gate results do not match the required gate set"
    for row in gates:
        if not isinstance(row, dict) or row.get("status") != "passed" or row.get("returncode") != 0:
            return f"{CERTIFICATION} contains a required gate that did not pass"

    inputs = manifest.get("inputs")
    if not isinstance(inputs, dict) or not inputs:
        return f"{CERTIFICATION} has no release input identities"
    if any(not isinstance(value, str) or not value.startswith("sha256:") for value in inputs.values()):
        return f"{CERTIFICATION} contains an invalid release input identity"
    return None


def check(out: Path, *, require_full: bool = False) -> str | None:
    """Return a problem description, or None when the stamp certifies these bytes.

    Digest-only historical stamps are accepted unless ``require_full`` is set. A stamp
    that advertises full certification is always checked fully even in compatibility
    mode; corrupted evidence must never fall back to legacy semantics.
    """
    fields = read(out)
    if not fields:
        return f"{STAMP} is missing (run programs/release_check.py to certify a release)"
    claimed = fields.get("digest", "")
    if not claimed.startswith("sha256:"):
        return f"{STAMP} carries no digest; it predates content binding"
    actual, n = digest(out)
    if claimed[7:] != actual:
        return (
            f"{STAMP} does not match the dataset: it certifies {claimed[7:][:12]}..., "
            f"these {n} files hash to {actual[:12]}... -- the dataset was rebuilt after "
            f"it was verified"
        )

    has_full = "certification" in fields
    if require_full and not has_full:
        return f"{STAMP} is legacy census-only certification; run programs/release_check.py"
    if has_full:
        return _check_full(out, fields, actual, n)
    return None
