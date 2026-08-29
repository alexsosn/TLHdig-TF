"""Pinned identity of the source corpus.

TLHdig Beta 0.3 is an immutable release, but the build listed its inputs dynamically
with `rglob("*.xml")`.  Deleting a source file therefore reduced the total *and* the
converted count in step, so the ledger balanced and the build passed.  Pinning
`path -> sha256` turns that into a failure.
"""

from __future__ import annotations

import hashlib
import unicodedata
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest(root: Path) -> dict[str, str]:
    root = Path(root)
    # NFC: macOS reports NFD, git stores NFC (see paths.rel)
    return {
        unicodedata.normalize("NFC", p.relative_to(root).as_posix()): sha256(p)
        for p in sorted(root.rglob("*.xml"), key=lambda x: str(x).lower())
    }


def write_manifest(path: Path, manifest: dict[str, str], header: str = "") -> None:
    body = "\n".join(f"{sha}  {rel}" for rel, sha in sorted(manifest.items()))
    path.write_text(header + body + "\n", encoding="utf8")


def read_manifest(path: Path) -> dict[str, str]:
    out = {}
    for line in Path(path).read_text(encoding="utf8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        sha, _, rel = line.partition("  ")
        out[rel] = sha
    return out


def verify(root: Path, manifest: dict[str, str]) -> list[str]:
    """Return a list of problems; empty means the corpus is exactly as recorded."""
    root = Path(root)
    present = {
        unicodedata.normalize("NFC", p.relative_to(root).as_posix()): p
        for p in root.rglob("*.xml")
    }
    problems = []
    for rel, expect in sorted(manifest.items()):
        p = present.pop(rel, None)
        if p is None:
            problems.append(f"missing: {rel}")
        elif sha256(p) != expect:
            problems.append(f"altered: {rel}")
    problems.extend(f"unexpected: {rel}" for rel in sorted(present))
    return problems
