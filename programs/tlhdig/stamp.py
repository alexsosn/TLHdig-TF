"""The BUILD-COMPLETE stamp, bound to artifact bytes and release evidence.

Legacy stamps contain only the historical digest over `.tf` basenames/content. They
remain readable so historical releases can be checked without rewriting them. Full
release stamps additionally bind a module-aware artifact digest and the successful
`RELEASE-CERTIFICATION.json` manifest.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import release_policy

STAMP = "BUILD-COMPLETE"
CERTIFICATION = "RELEASE-CERTIFICATION.json"


def _module_dir(out: Path) -> Path:
    from . import PROVENANCE_DIR

    return out.parent.parent / PROVENANCE_DIR / out.name


def digest(out: Path) -> tuple[str, int]:
    """Historical SHA-256 over every .tf basename/content; returns (hex, count).

    This algorithm intentionally remains byte-for-byte compatible with published legacy
    stamps. It does *not* bind module membership; full release certification therefore
    uses :func:`full_digest` in addition to this compatibility digest.
    """
    h = hashlib.sha256()
    files = sorted((p for p in out.glob("*.tf") if p.is_file()), key=lambda p: p.name)
    prov = _module_dir(out)
    if prov.is_dir():
        files += sorted((p for p in prov.glob("*.tf") if p.is_file()), key=lambda p: p.name)
    for p in files:
        h.update(p.name.encode("utf8"))
        h.update(b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest(), len(files)


def full_digest(out: Path) -> tuple[str, int]:
    """Module-aware identity for a full TF artifact.

    The main and provenance modules are semantically distinct Text-Fabric locations. The
    historical digest cannot distinguish some file moves across that boundary, so the
    full-release identity hashes a version tag, each module label, and then each feature
    basename/content hash in deterministic order.
    """
    h = hashlib.sha256()
    h.update(release_policy.ARTIFACT_DIGEST_ALGORITHM.encode("utf8"))
    h.update(b"\0")
    count = 0
    modules = (("main", Path(out)), ("provenance", _module_dir(Path(out))))
    for label, directory in modules:
        h.update(label.encode("utf8"))
        h.update(b"\0")
        files = sorted(
            (p for p in directory.glob("*.tf") if p.is_file()),
            key=lambda p: p.name,
        ) if directory.is_dir() else []
        for p in files:
            h.update(p.name.encode("utf8"))
            h.update(b"\0")
            h.update(hashlib.sha256(p.read_bytes()).digest())
            count += 1
        h.update(b"\xff")  # explicit end-of-module boundary
    return h.hexdigest(), count


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_hex(value: object, size: int) -> bool:
    if not isinstance(value, str) or len(value) != size:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and value.startswith("sha256:") and _is_hex(value[7:], 64)


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
        full, full_n = full_digest(out)
        if full_n != n:
            raise ValueError("legacy and module-aware artifact feature counts disagree")
        lines.extend(
            [
                f"artifactDigestAlgorithm={release_policy.ARTIFACT_DIGEST_ALGORITHM}",
                f"artifactDigest=sha256:{full}",
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


def _check_full(out: Path, fields: dict[str, str], legacy_n: int) -> str | None:
    claimed_cert = fields.get("certification", "")
    if not _is_sha256(claimed_cert):
        return f"{STAMP} is legacy census-only certification; run programs/release_check.py"

    algorithm = fields.get("artifactDigestAlgorithm")
    claimed_artifact = fields.get("artifactDigest", "")
    if algorithm != release_policy.ARTIFACT_DIGEST_ALGORITHM or not _is_sha256(claimed_artifact):
        return f"{STAMP} has no valid module-aware full artifact digest"
    actual_artifact, artifact_n = full_digest(out)
    if artifact_n != legacy_n or claimed_artifact[7:] != actual_artifact:
        return (
            f"{STAMP} module-aware artifact digest does not match current TF module layout/bytes"
        )

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
    if manifest.get("policy") != release_policy.POLICY:
        return (
            f"{CERTIFICATION} does not use the canonical release gate policy "
            f"{release_policy.POLICY}"
        )
    mode = manifest.get("mode")
    if mode not in release_policy.MODES:
        return f"{CERTIFICATION} has invalid release mode {mode!r}"
    if manifest.get("success") is not True:
        return f"{CERTIFICATION} does not record a successful certification"
    if manifest.get("artifactStable") is not True:
        return f"{CERTIFICATION} does not record a stable artifact"
    if manifest.get("inputsStable") is not True:
        return f"{CERTIFICATION} does not record stable release inputs"

    dataset = manifest.get("dataset")
    if not isinstance(dataset, dict):
        return f"{CERTIFICATION} has no dataset identity"
    if dataset.get("algorithm") != release_policy.ARTIFACT_DIGEST_ALGORITHM:
        return f"{CERTIFICATION} has the wrong module-aware artifact digest algorithm"
    if (
        dataset.get("digest") != f"sha256:{actual_artifact}"
        or dataset.get("features") != artifact_n
    ):
        return f"{CERTIFICATION} describes different TF module layout/bytes"
    if manifest.get("sourceVersion") != fields.get("sourceVersion"):
        return f"{CERTIFICATION} sourceVersion differs from {STAMP}"
    if manifest.get("tfVersion") != fields.get("tfVersion"):
        return f"{CERTIFICATION} tfVersion differs from {STAMP}"
    if mode != fields.get("mode"):
        return f"{CERTIFICATION} mode differs from {STAMP}"
    commit = manifest.get("codeCommit")
    if not _is_hex(commit, 40) or not _is_hex(fields.get("commit"), 40):
        return f"{CERTIFICATION} has an invalid code commit identity"
    if commit != fields.get("commit"):
        return f"{CERTIFICATION} code commit differs from {STAMP}"

    required = manifest.get("requiredGates")
    canonical = list(release_policy.REQUIRED_GATES)
    if required != canonical:
        return (
            f"{CERTIFICATION} required gates do not match canonical release gate policy "
            f"{release_policy.POLICY}"
        )
    gates = manifest.get("gates")
    if not isinstance(gates, list):
        return f"{CERTIFICATION} has no gate results"
    names = [row.get("name") for row in gates if isinstance(row, dict)]
    if names != canonical:
        return f"{CERTIFICATION} gate results do not match the required gate set"
    for row in gates:
        if not isinstance(row, dict) or row.get("status") != "passed" or row.get("returncode") != 0:
            return f"{CERTIFICATION} contains a required gate that did not pass"

    inputs = manifest.get("inputs")
    if not isinstance(inputs, dict):
        return f"{CERTIFICATION} has no release input identities"
    missing_inputs = [name for name in release_policy.REQUIRED_INPUTS if name not in inputs]
    if missing_inputs:
        return (
            f"{CERTIFICATION} is missing required release inputs: "
            + ", ".join(missing_inputs)
        )
    if any(not _is_sha256(value) for value in inputs.values()):
        return f"{CERTIFICATION} contains an invalid release input identity"

    defects = manifest.get("knownDefects")
    if not isinstance(defects, dict):
        return f"{CERTIFICATION} has no known-defect baseline record"
    missing_defects = [name for name in release_policy.FIDELITY_BASELINES if name not in defects]
    if missing_defects:
        return (
            f"{CERTIFICATION} is missing fidelity baselines: "
            + ", ".join(missing_defects)
        )
    for name in release_policy.FIDELITY_BASELINES:
        value = defects.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return f"{CERTIFICATION} has invalid fidelity baseline {name}={value!r}"
    if mode == "research-ready" and any(
        defects[name] != 0 for name in release_policy.FIDELITY_BASELINES
    ):
        return f"{CERTIFICATION} claims research-ready with non-zero known defects"
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
    if not _is_sha256(claimed):
        return f"{STAMP} carries no valid digest; it predates content binding or is malformed"
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
        return _check_full(out, fields, n)
    return None
