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
    4  aligned after deriving a numeral

`methods` says which mechanisms actually ran, because the level cannot: a compound line
that also absorbed damage is level 3 and used two mechanisms, and 9,326 of the 39,689
level-3 lines in the previous build were of that kind (research §7).

Everything the aligner decides with is *structural* -- how many codepoints there are,
which of them are placeholders, and which signs are transliterated `x`. It never
consults the learned reading -> sign tables for single signs. That is deliberate: those
tables, and Oracc's independent sign list, are what the result is measured against, and
a validator the aligner has already consumed cannot measure anything (research §8).

A caller wanting only the safest material takes level 1. Nothing here guesses to fill a
gap: a line that no mechanism explains is left unaligned, a position that two readings
would explain equally well is left unassigned, and absence of an assignment means
unknown, never "no sign".
"""

from __future__ import annotations

import unicodedata
from typing import NamedTuple, Sequence

# U+2592 MEDIUM SHADE. The cuneiform writes one per unreadable sign; the transliteration
# writes one bracketed lacuna for the whole gap.
PLACEHOLDER = "▒"


# Editorial annotation the source puts inside the cuneiform string. These are not
# signs, there is no sign for them to belong to, and they accounted for 4,721 of the
# codepoints no sign could claim. Dropping them from the alignment view loses nothing:
# `cu` still carries the line verbatim. `▒` is deliberately NOT here -- it stands for a
# lost sign and has to keep counting.
CU_MARKS = frozenset("?|°")

# The transliteration of a trace too damaged to identify. It is not a reading, and the
# cuneiform edition prints the shade for it: 93,526 of 93,544 observations.
ILLEGIBLE = "x"


class Alignment(NamedTuple):
    """One line's result. `values` holds one entry per sign, `None` where undecided."""

    level: int
    values: list[str | None]
    methods: tuple[str, ...] = ()


def is_sign(seq: str) -> bool:
    """Is this something a grapheme query could mean?

    For several numbers `cu` carries the Latin digits unrendered -- an upstream
    rendering failure, not a spelling. Letting `50` -> "5" through would put ASCII in
    `cu_sign` and pollute every query over the script.
    """
    return bool(seq) and all(
        0x12000 <= ord(c) <= 0x1254F        # cuneiform, numbers, early dynastic
        or c == PLACEHOLDER
        or 0xF0000 <= ord(c) <= 0x10FFFD    # Private Use Area, unencoded signs
        for c in seq
    )


def split_points(cu: str) -> list[str]:
    """The codepoints of a line's cuneiform that stand for signs."""
    return [
        c for c in cu
        if not c.isspace()
        and c not in CU_MARKS
        and unicodedata.category(c) != "Mn"
    ]


def _fits(point: str, sym: str) -> bool:
    """May this sign be written with this codepoint?

    The placeholder and `x` are the same statement made in two scripts, and level-1
    lines -- where the counts force the correspondence, so it cannot be argued with --
    measure the correspondence in both directions:

    * 94,026 of the 95,209 placeholders sit on an `x` (98.76%);
    * 24 of 1,511,993 legible codepoints sit on an `x` (0.002%).

    Being *inside a lacuna* is a much weaker signal and is deliberately not used: a
    restored `[an]` is restored in the cuneiform too, so a sign the source marks lost
    takes a placeholder only 0.15% of the time, and admitting all 583,289 of them as
    candidates would permit almost anything. That distinction is the whole constraint:
    absorption used to drop "the first N placeholders" wherever they fell, which put a
    legible sign on a shade and a shade on a legible sign in 14.1% of the level-2
    assignments the learned table can check (research §7).

    The 1,183 level-1 placeholders that sit on something other than `x` are the price:
    those positions are withheld rather than asserted.
    """
    return (point == PLACEHOLDER) == (sym == ILLEGIBLE)


def _expand(
    points: list[str], syms: Sequence[str], multi: dict[str, str]
) -> list[str] | None:
    """Consume `points` sign by sign, letting a compound reading take several.

    `MEŠ` is written 𒈨𒌍 and `SAGI` 𒋡𒋗𒂃 -- one reading, several signs (research §5.2).
    A reading only reaches `multi` if it was observed often enough and consistently
    enough, so this is a lookup of measured spellings, not a guess.

    A matched compound certifies only itself. The ordinary signs on either side of it
    are still held to `_fits`, because otherwise one convincing anchor at the end of a
    line vouched for everything before it.
    """
    out: list[str] = []
    i = 0
    for sym in syms:
        seq = multi.get(sym)
        if seq and points[i : i + len(seq)] == list(seq):
            out.append(seq)
            i += len(seq)
        elif i < len(points) and _fits(points[i], sym):
            out.append(points[i])
            i += 1
        else:
            return None
    return out if i == len(points) else None


def _absorb(points: list[str], syms: Sequence[str]) -> list[str | None] | None:
    """Give every sign one codepoint, dropping only placeholders, in order.

    Returns one value per sign, `None` where the valid readings of the line disagree
    about that position. Dropping placeholders greedily was the defect: this considers
    every placement `_fits` allows and asserts a value only where they all agree.
    """
    n, m = len(points), len(syms)
    # Which (codepoint, sign) states a valid reading can pass through: reachable from
    # the start, and able to reach the end.
    start = [[False] * (m + 1) for _ in range(n + 1)]
    start[0][0] = True
    for i in range(n + 1):
        for j in range(m + 1):
            if not start[i][j]:
                continue
            if i < n and j < m and _fits(points[i], syms[j]):
                start[i + 1][j + 1] = True
            if i < n and points[i] == PLACEHOLDER:
                start[i + 1][j] = True
    end = [[False] * (m + 1) for _ in range(n + 1)]
    end[n][m] = True
    for i in range(n, -1, -1):
        for j in range(m, -1, -1):
            if i < n and j < m and _fits(points[i], syms[j]) and end[i + 1][j + 1]:
                end[i][j] = True
            if i < n and points[i] == PLACEHOLDER and end[i + 1][j]:
                end[i][j] = True
    if not end[0][0]:
        return None

    choices: list[set[str]] = [set() for _ in range(m)]
    for i in range(n):
        for j in range(m):
            if start[i][j] and end[i + 1][j + 1] and _fits(points[i], syms[j]):
                choices[j].add(points[i])
    return [next(iter(c)) if len(c) == 1 else None for c in choices]


def _clean(values: Sequence[str | None]) -> list[str | None] | None:
    """Withhold anything that is not a sign. `None` if nothing survives."""
    out = [v if v is not None and is_sign(v) else None for v in values]
    return out if any(v is not None for v in out) else None


def align(
    cu: str,
    syms: Sequence[str],
    damaged: bool = False,
    multi: dict[str, str] | None = None,
) -> Alignment | None:
    """Lay a line's cuneiform out per sign, or return None when nothing explains it."""
    if not cu or not syms:
        return None
    points = split_points(cu)
    multi = multi or {}

    if len(points) == len(syms):
        # The correspondence is forced; there is no placement to choose. A codepoint
        # `_fits` rejects is still withheld -- 237 of 95,209 level-1 placeholders sit on
        # a sign nothing marks as lost, and that is a disagreement to report, not to
        # resolve -- but the rest of the line stands.
        vals = [p if _fits(p, syms[j]) else None for j, p in enumerate(points)]
        got = _clean(vals)
        return Alignment(1, got, ("zip",)) if got else None

    if multi:
        got = _expand(points, syms, multi)
        if got is not None:
            vals = _clean(got)
            return Alignment(3, vals, ("compound",)) if vals else None

    # Numerals, derived rather than looked up, so a number absent from the table still
    # aligns. Level 4: weaker than a measured spelling, stronger than nothing.
    numerals = {s_: n_ for s_ in set(syms) if (n_ := numeral(s_))}
    if numerals:
        got = _expand(points, syms, {**numerals, **multi})
        if got is not None:
            vals = _clean(got)
            return Alignment(4, vals, ("numeral",)) if vals else None

    if damaged and len(points) > len(syms):
        got = _absorb(points, syms)
        if got is not None:
            vals = _clean(got)
            if vals:
                return Alignment(2, vals, ("damage",))
        # A lacuna and a compound spelling can occur on the same line.
        if multi:
            for want in range(1, len(points) - len(syms) + 1):
                kept = _drop(points, want)
                if kept is None:
                    continue
                got = _expand(kept, syms, multi)
                if got is not None:
                    vals = _clean(got)
                    if vals:
                        return Alignment(3, vals, ("damage", "compound"))
    return None


def _drop(points: list[str], want: int) -> list[str] | None:
    """Remove exactly `want` placeholders, or fail.

    Only the combined damage-and-compound path uses this. It cannot enumerate
    placements the way `_absorb` does, because a compound spans several codepoints, so
    it takes the leading placeholders and lets `_expand` refuse the result if `_fits`
    is violated anywhere.
    """
    kept: list[str] = []
    dropped = 0
    for ch in points:
        if ch == PLACEHOLDER and dropped < want:
            dropped += 1
            continue
        kept.append(ch)
    return kept if dropped == want else None


def load_multi(path) -> dict[str, str]:
    """Read `signmap-multi.tsv`: reading -> codepoint sequence.

    A spelling containing a placeholder is rejected here as well as by the learner, so
    a table generated before that rule cannot reintroduce it. `a+na` -> 𒀀▒𒀀 was
    learned at 0.986 confidence over 146 observations: high agreement means the hole in
    the tablet recurs in the same place, not that the hole is part of the word.
    """
    out: dict[str, str] = {}
    if not path or not path.is_file():
        return out
    for line in path.read_text(encoding="utf8").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if (
            len(parts) >= 2
            and parts[0]
            and len(parts[1]) > 1
            and PLACEHOLDER not in parts[1]
            and is_sign(parts[1])
        ):
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
