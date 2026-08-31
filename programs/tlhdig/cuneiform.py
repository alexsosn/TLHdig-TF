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


# Editorial annotation the source puts inside the cuneiform string. These are not
# signs, there is no sign for them to belong to, and they accounted for 4,721 of the
# codepoints no sign could claim. Dropping them from the alignment view loses nothing:
# `cu` still carries the line verbatim. `▒` is deliberately NOT here -- it stands for a
# lost sign and has to keep counting.
CU_MARKS = frozenset("?|°")


def split_points(cu: str) -> list[str]:
    """The codepoints of a line's cuneiform that stand for signs."""
    return [
        c for c in cu
        if not c.isspace()
        and c not in CU_MARKS
        and unicodedata.category(c) != "Mn"
    ]


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

    # Numerals, derived rather than looked up, so a number absent from the table still
    # aligns. Level 4: weaker than a measured spelling, stronger than nothing.
    numerals = {s_: n_ for s_ in set(syms) if (n_ := numeral(s_))}
    if numerals:
        got = _expand(points, syms, {**numerals, **multi})
        if got is not None:
            return 4, got

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

# --------------------------------------------------------------------- numerals
#
# The compound table learns `2` -> 𒁹𒁹 and `12` -> 𒌋𒁹𒁹 by frequency, but a table only
# knows the numbers this release happens to contain. TLHdig is a living corpus, and a
# future version will hold numbers it has never seen. Arithmetic generalises.
#
# The primitives are what the corpus attests, not what a grammar says: 1 and 3-9 have
# dedicated signs, 2 is written with two units (7,409 observations of 𒁹𒁹), 10 is 𒌋,
# 20 is 𒌋𒌋 and 30 is 𒌍. Above 39 nothing is attested consistently -- for several
# numbers `cu` contains the Latin digits, unrendered -- so the rule refuses instead of
# inventing, and the line stays unaligned.
UNITS = {
    1: "\U00012079",                    # DISH
    2: "\U00012079\U00012079",
    3: "\U00012408", 4: "\U0001243C", 5: "\U0001240A",
    6: "\U0001240B", 7: "\U0001230C", 8: "\U0001240D", 9: "\U00012446",
}
TENS = {
    10: "\U0001230B",                   # U
    20: "\U0001230B\U0001230B",
    30: "\U0001230D",                   # U U U, one codepoint
}
MAX_NUMERAL = 39


def numeral(reading: str) -> str | None:
    """Render a numeral as cuneiform, or None when the corpus does not attest it."""
    # `str.isdigit()` is true for `₄` and `⁴` -- subscripts are digits to Python but not
    # to int(), which raises. The corpus is full of them: NA₄, SIG₅, EZEN₄. Only plain
    # ASCII digits are a numeral here.
    if not reading.isascii() or not reading.isdigit():
        return None
    n = int(reading)
    if n < 1 or n > MAX_NUMERAL:
        return None
    tens, units = divmod(n, 10)
    out = ""
    if tens:
        t = TENS.get(tens * 10)
        if t is None:
            return None
        out += t
    if units:
        u = UNITS.get(units)
        if u is None:
            return None
        out += u
    return out or None
