"""Laying a line's cuneiform out per sign.

`cu` is one string for a whole line and is not sign-aligned (research §1). Where the
line's codepoints and its signs correspond one to one, zipping them is correct -- and
that this is correct rather than merely plausible is established by measurement, not
assumed: one reading lands on one codepoint 99% of the time over 80,000 observations,
and 96.2% of those pairings agree with Oracc's sign list (research §3).

Where they do not correspond, four mechanisms account for the difference (research §5).
Two are handled here; the third is punctuation, already fixed in the tokeniser; the
fourth is numerals.

The result carries *how* it was reached, because the mechanisms are not equally strong:

    1  counts matched, zipped one to one
    2  aligned after absorbing damage placeholders into a recorded lacuna
    3  aligned after expanding a compound logogram

A caller wanting only the safest material takes 1. Nothing here guesses to fill a gap:
a line that no mechanism explains is left unaligned, and absence of an assignment means
unknown, never "no sign".
"""

from __future__ import annotations

import unicodedata

# U+2592 MEDIUM SHADE. The cuneiform writes one per unreadable sign; the transliteration
# writes one bracketed lacuna for the whole gap.
PLACEHOLDER = "▒"


def split_points(cu: str) -> list[str]:
    """The codepoints of a line's cuneiform, ignoring spacing and combining marks."""
    return [c for c in cu if not c.isspace() and unicodedata.category(c) != "Mn"]


def _expand(points: list[str], syms: list[str], multi: dict[str, str]) -> list[str] | None:
    """Consume `points` sign by sign, letting a compound reading take several.

    `MEŠ` is written 𒈨𒌍 and `SAGI` 𒋡𒋗𒂃 -- one reading, several signs (research §5.2).
    A reading only reaches `multi` if it was observed often enough and consistently
    enough, so this is a lookup of measured spellings, not a guess.
    """
    out: list[str] = []
    i = 0
    for sym in syms:
        seq = multi.get(sym)
        if seq and points[i : i + len(seq)] == list(seq):
            out.append(seq)
            i += len(seq)
        elif i < len(points):
            out.append(points[i])
            i += 1
        else:
            return None
    return out if i == len(points) else None


def _absorb(points: list[str], want: int) -> list[str] | None:
    """Drop exactly `want` placeholders, or fail.

    Dropping fewer or more would be forcing the line into shape; the caller only reaches
    here when the line records a lacuna that explains them.
    """
    kept: list[str] = []
    dropped = 0
    for ch in points:
        if ch == PLACEHOLDER and dropped < want:
            dropped += 1
            continue
        kept.append(ch)
    return kept if dropped == want else None


def align(
    cu: str, syms: list[str], damaged: bool = False, multi: dict[str, str] | None = None
) -> tuple[int, list[str]] | None:
    """Return (how, one cuneiform string per sign), or None when nothing explains it."""
    if not cu or not syms:
        return None
    points = split_points(cu)
    multi = multi or {}

    if len(points) == len(syms):
        return 1, points

    if multi:
        got = _expand(points, syms, multi)
        if got is not None:
            return 3, got

    if damaged and len(points) > len(syms):
        kept = _absorb(points, len(points) - len(syms))
        if kept is not None and len(kept) == len(syms):
            return 2, kept
        # A lacuna and a compound spelling can occur on the same line.
        if multi:
            for want in range(1, len(points) - len(syms) + 1):
                kept = _absorb(points, want)
                if kept is None:
                    continue
                got = _expand(kept, syms, multi)
                if got is not None:
                    return 3, got
    return None


def load_multi(path) -> dict[str, str]:
    """Read `signmap-multi.tsv`: reading -> codepoint sequence."""
    out: dict[str, str] = {}
    if not path or not path.is_file():
        return out
    for line in path.read_text(encoding="utf8").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0] and len(parts[1]) > 1:
            out[parts[0]] = parts[1]
    return out
