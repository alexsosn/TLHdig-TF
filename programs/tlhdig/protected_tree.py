"""Deterministic Git-backed identity for certification-relevant repository inputs.

The protected-tree digest deliberately hashes Git object identities rather than reading
large corpus payloads again.  Correctness also requires a clean protected index/worktree:
a dirty checkout must never inherit the identity of its committed HEAD.
"""
from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
import subprocess
from typing import Iterable

ALGORITHM = "tlhdig-protected-git-tree-v1"
PROFILE = "release-source-v1"


class ProtectedTreeError(RuntimeError):
    """The requested protected repository identity cannot be established safely."""


def _run(root: Path, *args: str) -> bytes:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise ProtectedTreeError(f"cannot execute Git: {exc}") from exc
    if proc.returncode:
        detail = proc.stderr.decode("utf8", errors="replace").strip()
        raise ProtectedTreeError(
            f"Git command failed ({' '.join(args)}): {detail or proc.returncode}"
        )
    return proc.stdout


def _repository_root(root: Path) -> Path:
    root = Path(root).resolve()
    if not root.is_dir():
        raise ProtectedTreeError(f"repository root does not exist: {root}")
    raw = _run(root, "rev-parse", "--show-toplevel")
    try:
        actual = Path(raw.decode("utf8").strip()).resolve()
    except UnicodeDecodeError as exc:
        raise ProtectedTreeError("Git repository root is not valid UTF-8") from exc
    if actual != root:
        raise ProtectedTreeError(
            f"Git repository root mismatch: expected {root}, Git reports {actual}"
        )
    return root


def _protected(path: str, profile: str) -> bool:
    if profile != PROFILE:
        raise ProtectedTreeError(f"unknown protected-tree profile: {profile!r}")
    p = PurePosixPath(path)
    parts = p.parts
    if not parts:
        return False
    if parts[0] in {"corpus", "app"}:
        return len(parts) > 1
    if parts[0] == "programs":
        if len(parts) < 2:
            return False
        if parts[1] == "tests":
            return False
        if len(parts) == 2 and parts[1] == "shard.txt":
            return False
        if len(parts) == 2 and parts[1].startswith("research_") and parts[1].endswith(".py"):
            return False
        return True
    if path == "requirements.txt":
        return True
    return path == ".github/workflows/certify-dataset.yml"


def _decode_paths(raw: bytes) -> Iterable[str]:
    for item in raw.split(b"\0"):
        if not item:
            continue
        try:
            yield item.decode("utf8")
        except UnicodeDecodeError as exc:
            raise ProtectedTreeError("Git path is not valid UTF-8") from exc


def _dirty_paths(root: Path) -> list[str]:
    """Return protected staged/unstaged/untracked paths, with renames de-sugared."""
    commands = (
        ("diff", "--name-only", "--no-renames", "-z", "HEAD", "--"),
        ("diff", "--cached", "--name-only", "--no-renames", "-z", "HEAD", "--"),
        ("ls-files", "--others", "--exclude-standard", "-z", "--"),
    )
    dirty: set[str] = set()
    for args in commands:
        for path in _decode_paths(_run(root, *args)):
            if _protected(path, PROFILE):
                dirty.add(path)
    return sorted(dirty)


def _entries(root: Path, profile: str) -> list[tuple[str, str, str, str]]:
    """Return (path, mode, type, oid) for protected tracked HEAD entries."""
    raw = _run(root, "ls-tree", "-r", "-z", "--full-tree", "HEAD")
    entries: list[tuple[str, str, str, str]] = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        try:
            meta, path_raw = item.split(b"\t", 1)
            mode_raw, type_raw, oid_raw = meta.split(b" ", 2)
            path = path_raw.decode("utf8")
            mode = mode_raw.decode("ascii")
            obj_type = type_raw.decode("ascii")
            oid = oid_raw.decode("ascii")
        except (ValueError, UnicodeDecodeError) as exc:
            raise ProtectedTreeError("cannot parse Git tree entry") from exc
        if _protected(path, profile):
            entries.append((path, mode, obj_type, oid))
    entries.sort(key=lambda row: row[0])
    if not entries:
        raise ProtectedTreeError("protected-tree profile selected no tracked entries")
    return entries


def identity(root: Path, *, profile: str = PROFILE) -> dict[str, str]:
    """Return the clean HEAD identity for one immutable protected profile.

    ``root`` must be the repository top level exactly; we never walk parents looking for
    some other checkout.  Any staged, unstaged, or untracked protected path makes the
    identity unavailable rather than allowing HEAD to certify different local bytes.
    """
    if profile != PROFILE:
        raise ProtectedTreeError(f"unknown protected-tree profile: {profile!r}")
    root = _repository_root(Path(root))
    dirty = _dirty_paths(root)
    if dirty:
        sample = ", ".join(dirty[:8])
        more = " ..." if len(dirty) > 8 else ""
        raise ProtectedTreeError(f"protected repository state is dirty: {sample}{more}")

    h = hashlib.sha256()
    h.update(ALGORITHM.encode("ascii"))
    h.update(b"\0")
    h.update(profile.encode("ascii"))
    h.update(b"\0")
    for path, mode, obj_type, oid in _entries(root, profile):
        for value in (path, mode, obj_type, oid):
            h.update(value.encode("utf8"))
            h.update(b"\0")
        h.update(b"\xff")
    return {
        "algorithm": ALGORITHM,
        "profile": profile,
        "digest": "sha256:" + h.hexdigest(),
    }
