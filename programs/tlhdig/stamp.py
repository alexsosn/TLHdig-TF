"""The BUILD-COMPLETE stamp, bound to the bytes it certifies.

`census.py` writes the stamp after the dataset loads and every invariant holds, and
`publish_dataset.sh` refuses to stage without it.  A stamp that only records *that*
verification happened is not enough: `build.py` rebuilds in place, so an old stamp
survives a rebuild that was never verified, and the release gate accepts it.

The stamp therefore carries a digest of every `.tf` file it certifies.  Publishing
recomputes the digest and refuses on mismatch, so the question the gate answers is
"were *these bytes* verified?" rather than "was something verified here once?".
"""

from __future__ import annotations

import hashlib
from pathlib import Path

STAMP = "BUILD-COMPLETE"


def _module_dir(out: Path) -> Path:
    from . import PROVENANCE_DIR

    return out.parent.parent / PROVENANCE_DIR / out.name


def digest(out: Path) -> tuple[str, int]:
    """SHA-256 over every .tf file's name and content.  Returns (hex, file count).

    Covers the provenance module as well: the two halves are one build, and a stamp
    that certified only the main dataset would let them drift apart -- which is exactly
    how a src_span could stop describing the graph it points into.
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


def write(out: Path, source_version: str, tf_version: str) -> str:
    d, n = digest(out)
    (out / STAMP).write_text(
        f"sourceVersion={source_version}\n"
        f"tfVersion={tf_version}\n"
        f"features={n}\n"
        f"digest=sha256:{d}\n",
        encoding="utf8",
    )
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


def check(out: Path) -> str | None:
    """Return a problem description, or None when the stamp certifies these bytes."""
    fields = read(out)
    if not fields:
        return f"{STAMP} is missing (run programs/census.py to verify and stamp)"
    claimed = fields.get("digest", "")
    if not claimed.startswith("sha256:"):
        return f"{STAMP} carries no digest; it predates content binding -- re-run census.py"
    actual, n = digest(out)
    if claimed[7:] != actual:
        return (
            f"{STAMP} does not match the dataset: it certifies {claimed[7:][:12]}..., "
            f"these {n} files hash to {actual[:12]}... -- the dataset was rebuilt after "
            f"it was verified; re-run census.py"
        )
    return None
