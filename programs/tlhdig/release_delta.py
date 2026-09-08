"""Exact predecessor-delta validation for release certification.

This module has deliberately no network behavior. A release workflow must materialize
any retired predecessor at the normal ``tf/<version>`` / ``tf-provenance/<version>``
layout before invoking the checker. The pinned module-aware digest makes substitution of
other predecessor bytes a hard failure.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Iterable

from . import release_policy, stamp

_SHA256 = re.compile(r"^sha256:[0-9a-fA-F]{64}$")
_CHANGE = re.compile(r"^(main|provenance):([^/\\:*?\[\]]+\.tf)$")


class DeltaError(ValueError):
    pass


def _read_spec(path: Path) -> dict:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeltaError(f"cannot read release delta spec: {exc}") from exc
    if not isinstance(payload, dict):
        raise DeltaError("release delta spec must be a JSON object")
    if payload.get("schema") != 1:
        raise DeltaError("release delta spec requires schema=1")
    return payload


def _require_text(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DeltaError(f"release delta spec requires non-empty {key}")
    return value.strip()


def _require_version_component(payload: dict, key: str) -> str:
    value = _require_text(payload, key)
    if value in {".", ".."} or "/" in value or "\\" in value or Path(value).name != value:
        raise DeltaError(f"{key} must be a single version path component")
    return value


def _expected_changes(payload: dict) -> list[str]:
    values = payload.get("expectedChanges")
    if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
        raise DeltaError("expectedChanges must be a list of module-qualified feature names")
    if values != sorted(values):
        raise DeltaError("expectedChanges must be sorted")
    if len(values) != len(set(values)):
        raise DeltaError("expectedChanges must not contain duplicates")
    for item in values:
        if not _CHANGE.fullmatch(item):
            raise DeltaError(
                f"invalid expected change {item!r}; use main:<feature>.tf or provenance:<feature>.tf"
            )
    return list(values)


def _feature_names(directory: Path) -> set[str]:
    if not directory.is_dir():
        return set()
    return {path.name for path in directory.glob("*.tf") if path.is_file()}


def _ordinary_body(path: Path) -> bytes:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise DeltaError(f"cannot read TF feature {path}: {exc}") from exc
    marker = b"\n\n"
    at = data.find(marker)
    if at < 0:
        raise DeltaError(f"malformed TF feature without metadata/body separator: {path}")
    return data[at + len(marker):]


def _otext_semantics(path: Path) -> bytes:
    try:
        text = path.read_text(encoding="utf8")
    except (OSError, UnicodeDecodeError) as exc:
        raise DeltaError(f"cannot read otext config {path}: {exc}") from exc
    lines = text.splitlines()
    if not lines or lines[0] != "@config":
        raise DeltaError(f"malformed otext config: {path}")
    kept = [
        line
        for line in lines
        if not line.startswith("@version=") and not line.startswith("@dateWritten=")
    ]
    return ("\n".join(kept) + "\n").encode("utf8")


def _payload(path: Path) -> bytes:
    return _otext_semantics(path) if path.name == "otext.tf" else _ordinary_body(path)


def _module_changes(old: Path, new: Path, label: str) -> Iterable[str]:
    old_names = _feature_names(old)
    new_names = _feature_names(new)
    for name in sorted(old_names | new_names):
        old_path = old / name
        new_path = new / name
        if name not in old_names:
            # Added/removed features are changes, but the side that exists must still be
            # a structurally readable TF feature. A declaration may not bless arbitrary
            # malformed bytes merely because the basename is new.
            _payload(new_path)
            yield f"{label}:{name}"
            continue
        if name not in new_names:
            _payload(old_path)
            yield f"{label}:{name}"
            continue
        if _payload(old_path) != _payload(new_path):
            yield f"{label}:{name}"


def _actual_changes(root: Path, predecessor: str, current: str) -> list[str]:
    changes = [
        *_module_changes(root / "tf" / predecessor, root / "tf" / current, "main"),
        *_module_changes(
            root / "tf-provenance" / predecessor,
            root / "tf-provenance" / current,
            "provenance",
        ),
    ]
    return sorted(changes)


def check(spec_path: Path | str, *, root: Path | str, current_version: str) -> dict:
    """Validate the release delta declaration and return manifest-ready evidence."""
    root = Path(root)
    spec = _read_spec(Path(spec_path))
    tf_version = _require_text(spec, "tfVersion")
    if tf_version != current_version:
        raise DeltaError(
            f"release delta tfVersion {tf_version!r} does not match current TF_VERSION {current_version!r}"
        )

    current = root / "tf" / current_version
    if not current.is_dir():
        raise DeltaError(f"current TF artifact is missing: {current}")

    if spec.get("baseline") is True:
        if current_version != release_policy.DELTA_BASELINE_TF_VERSION:
            raise DeltaError(
                "baseline release-delta mode is allowed only for "
                f"TF {release_policy.DELTA_BASELINE_TF_VERSION}"
            )
        return {
            "baseline": True,
            "tfVersion": current_version,
            "expectedChanges": [],
            "actualChanges": [],
        }

    predecessor = _require_version_component(spec, "predecessorVersion")
    if predecessor == current_version:
        raise DeltaError("predecessorVersion must differ from tfVersion")
    predecessor_digest = spec.get("predecessorDigest")
    if not isinstance(predecessor_digest, str) or not _SHA256.fullmatch(predecessor_digest):
        raise DeltaError("predecessorDigest must be sha256:<64 hex>")
    expected = _expected_changes(spec)

    old = root / "tf" / predecessor
    if not old.is_dir():
        raise DeltaError(f"predecessor TF artifact is missing: {old}")
    actual_digest, _ = stamp.full_digest(old)
    actual_digest = "sha256:" + actual_digest
    if actual_digest.lower() != predecessor_digest.lower():
        raise DeltaError(
            f"predecessor digest mismatch: expected {predecessor_digest}, got {actual_digest}"
        )

    actual = _actual_changes(root, predecessor, current_version)
    if actual != expected:
        raise DeltaError(
            "release delta mismatch: "
            f"expected changes {expected!r}, actual changes {actual!r}"
        )

    return {
        "baseline": False,
        "tfVersion": current_version,
        "predecessorVersion": predecessor,
        "predecessorDigest": predecessor_digest.lower(),
        "expectedChanges": expected,
        "actualChanges": actual,
    }
