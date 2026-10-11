"""Evidence-backed Private Use Area classification for line-level cuneiform.

A reading learned from cu_sign/signmap is *not* proof of a PUA crosswalk.
Unknown PUA codepoints count as unresolved; corpus gates reject undeclared ones.
"""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import re

TABLE = Path(__file__).resolve().parents[1] / "pua-status.json"
_STATUSES = frozenset({"mapped-deliberate-pua", "ambiguous-legacy-pua"})
_POINT = re.compile(r"^U\+[0-9A-F]{4,6}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def is_pua_char(c: str) -> bool:
    if len(c) != 1:
        return False
    cp = ord(c)
    return (0xE000 <= cp <= 0xF8FF
            or 0xF0000 <= cp <= 0xFFFFD
            or 0x100000 <= cp <= 0x10FFFD)


def _no_duplicates(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate mapping table key: {key}")
        obj[key] = value
    return obj


def load_status_table(path: Path | str | None = None) -> dict:
    """Validate schema, exact codepoints and the pinned *external* evidence."""
    table = json.loads(Path(path or TABLE).read_text(encoding="utf8"),
                       object_pairs_hook=_no_duplicates)
    if not isinstance(table, dict) or table.get("schema") != 1:
        raise ValueError("unsupported PUA status schema")
    codes = table.get("codepoints")
    if not isinstance(codes, dict) or not codes:
        raise ValueError("PUA codepoints must be a nonempty object")
    for key, row in codes.items():
        if (not isinstance(key, str) or not _POINT.fullmatch(key)
                or not is_pua_char(chr(int(key[2:], 16)))
                or f"U+{int(key[2:], 16):04X}" != key):
            raise ValueError(f"invalid PUA codepoint: {key!r}")
        if not isinstance(row, dict) or row.get("status") not in _STATUSES:
            raise ValueError(f"invalid status for {key!r}")
        if row["status"] == "mapped-deliberate-pua" and not row.get("externalEvidence"):
            raise ValueError(f"direct mapping lacks external evidence: {key}")
    provenance = table.get("externalSource", {})
    if not isinstance(provenance, dict) or not _SHA256.fullmatch(
        str(provenance.get("sha256", ""))
    ):
        raise ValueError("PUA evidence must pin the external source SHA-256")
    if not provenance.get("url") or not provenance.get("version"):
        raise ValueError("PUA external source version and URL required")
    return table


@lru_cache(maxsize=1)
def _table() -> dict:
    return load_status_table()


def classify_codepoint(cp: int) -> str:
    if not isinstance(cp, int) or not 0 <= cp <= 0x10FFFF:
        raise ValueError("not a Unicode codepoint")
    if not is_pua_char(chr(cp)):
        raise ValueError("not a Private Use Area codepoint")
    row = _table()["codepoints"].get(f"U+{cp:04X}")
    return row["status"] if row else "unknown-pua"


def count_pua(value: str) -> tuple[int, int]:
    """(all occurrences, unresolved occurrences) in verbatim line cu."""
    statuses = _table()["codepoints"]
    total = unmapped = 0
    for char in value:
        if is_pua_char(char):
            total += 1
            if statuses.get(f"U+{ord(char):04X}", {}).get("status") != "mapped-deliberate-pua":
                unmapped += 1
    return total, unmapped
