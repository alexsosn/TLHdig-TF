"""Shared source preparation contract for reviewed #12 crossing-tag files.

This module deliberately stops before tolerant structural recovery. It separates the
immutable source from patches that remain proven byte-local ("mechanical") and patches
that belong to a reviewed structural-recovery decision. Consumers must not treat
mechanical_bytes as a repaired XML document: for reviewed malformed files it is expected
to remain structurally invalid until the recovery layer handles the recorded events.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from . import repair
from .paths import CORPUS, PATCHES, PROGRAMS


PATCH_POLICY = PROGRAMS / "source_recovery_patch_policy.json"


class PreparedSourceError(RuntimeError):
    pass


class NotReviewed(PreparedSourceError):
    """The source path has no reviewed #12 structural-recovery policy."""


class PolicyDrift(PreparedSourceError):
    """Reviewed policy no longer matches source bytes or ordered patch manifest."""


@dataclass(frozen=True)
class PreparedSource:
    path: str
    source_sha256: str
    original_bytes: bytes
    mechanical_bytes: bytes
    mechanical_patch_ordinals: tuple[int, ...]
    recovery_patch_ordinals: tuple[int, ...]
    recovery_event_ids: tuple[str, ...]
    mechanical_patches: tuple[repair.Patch, ...]
    recovery_patches: tuple[repair.Patch, ...]

    @property
    def mechanical_offset_map(self) -> repair.OffsetMap:
        return repair.OffsetMap(self.original_bytes, list(self.mechanical_patches))


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def manifest_context_fingerprint(patches: list[repair.Patch]) -> str:
    """Match the research inventory digest of the complete ordered patch sequence."""
    canonical = json.dumps(
        [[_b64(p.old), _b64(p.new), p.reason] for p in patches],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf8")
    return hashlib.sha256(canonical).hexdigest()


def _load_policy(path: Path = PATCH_POLICY) -> dict:
    doc = json.loads(path.read_text(encoding="utf8"))
    if doc.get("schema") != 1 or not isinstance(doc.get("files"), dict):
        raise PolicyDrift(f"unsupported prepared-source policy schema: {path}")
    return doc


def reviewed_paths(policy_path: Path = PATCH_POLICY) -> tuple[str, ...]:
    return tuple(sorted(_load_policy(policy_path)["files"]))


def prepare(
    rel: str,
    *,
    corpus: Path = CORPUS,
    manifest: Path = PATCHES,
    policy_path: Path = PATCH_POLICY,
) -> PreparedSource:
    """Partition a reviewed source manifest into mechanical and recovery lanes.

    The partition is explicit reviewed policy. It is validated against both immutable
    source SHA and a digest of the complete ordered manifest before any patch is applied.
    A changed or novel source/manifest therefore fails closed.
    """
    policy = _load_policy(policy_path)["files"]
    entry = policy.get(rel)
    if entry is None:
        raise NotReviewed(rel)

    manifest_entries = repair.read_manifest(manifest)
    if rel not in manifest_entries:
        raise PolicyDrift(f"{rel}: reviewed path missing from manifest")
    expected_sha, patches = manifest_entries[rel]

    src = corpus / rel
    if not src.is_file():
        raise PolicyDrift(f"{rel}: reviewed source file missing")
    original = src.read_bytes()
    actual_sha = repair.sha256(original)

    policy_sha = entry.get("source_sha256")
    if actual_sha != expected_sha or actual_sha != policy_sha:
        raise PolicyDrift(
            f"{rel}: source SHA drift ({actual_sha}; manifest={expected_sha}; "
            f"policy={policy_sha})"
        )

    actual_manifest_fp = manifest_context_fingerprint(patches)
    if actual_manifest_fp != entry.get("manifest_context_fingerprint"):
        raise PolicyDrift(f"{rel}: ordered patch manifest drift")

    mechanical_ordinals = tuple(entry.get("mechanical_patch_ordinals", ()))
    recovery_ordinals = tuple(entry.get("recovery_patch_ordinals", ()))
    all_ordinals = set(range(1, len(patches) + 1))
    mechanical_set = set(mechanical_ordinals)
    recovery_set = set(recovery_ordinals)
    if (
        mechanical_ordinals != tuple(sorted(mechanical_ordinals))
        or recovery_ordinals != tuple(sorted(recovery_ordinals))
        or len(mechanical_set) != len(mechanical_ordinals)
        or len(recovery_set) != len(recovery_ordinals)
        or mechanical_set & recovery_set
        or mechanical_set | recovery_set != all_ordinals
    ):
        raise PolicyDrift(
            f"{rel}: patch partition is not exact manifest-order partition"
        )

    mechanical_patches = tuple(patches[i - 1] for i in mechanical_ordinals)
    recovery_patches = tuple(patches[i - 1] for i in recovery_ordinals)

    try:
        mechanical_bytes = repair.apply(
            original, list(mechanical_patches), expect_sha=expected_sha
        )
    except repair.PatchError as exc:
        raise PolicyDrift(
            f"{rel}: mechanical lane no longer applies independently: {exc}"
        ) from exc

    event_ids = tuple(entry.get("recovery_event_ids", ()))
    if not event_ids:
        raise PolicyDrift(f"{rel}: reviewed recovery path has no recovery events")

    return PreparedSource(
        path=rel,
        source_sha256=actual_sha,
        original_bytes=original,
        mechanical_bytes=mechanical_bytes,
        mechanical_patch_ordinals=mechanical_ordinals,
        recovery_patch_ordinals=recovery_ordinals,
        recovery_event_ids=event_ids,
        mechanical_patches=mechanical_patches,
        recovery_patches=recovery_patches,
    )
