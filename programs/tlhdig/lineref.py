"""Parsing `lb/@lnr` line references (research §5).

    [ "{" fragment "}" ] [ surface ] [ column ] number [ prime ] [ tail ]

678 distinct surface/column prefixes occur, and 252 values carry no number at all --
those are surface headers rather than lines.  The prime (`′`, 308,245 lines) marks
relative numbering on a broken tablet, where the absolute line number is unknown.

`collabel` is the level-2 section label.  It has to include the fragment and the column,
not just the surface: in a composite tablet several fragments each have a `Vs.`, and
several columns each have a line `1′`, so `surface` alone is not a unique address.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Named columns ("lk. Kol.", "r. col.") and Roman numerals, with optional uncertainty.
# "lk. Kol.", "r. col.", "re. Kol.", "R. col." -- left/right column, either language.
_NAMED_COL = r"(?:[lrRL][keu]?\.\s*(?:Kol|col)\.?)"
# A bare Roman numeral, optionally parenthesised when the editor inferred it,
# optionally prefixed by "Kol." -- e.g. "II", "(II)", "Kol. I".
_ROMAN = r"(?:(?:Kol\.\s*)?\(?[IVXivx]+\)?)"

# Edges are surfaces, not columns: "u. Rd." (lower edge), "lk. Rd." (left edge).
_EDGE = r"(?:[ourl]\w*\.\s*Rd\.)"
# Obverse / reverse in both languages and both cases, plus lettered sides
# ("Seite A", "side B") and the bare "a."/"b." used by some editors.
_SIDE = r"(?:[VR]s\.|[Oo]bv\.|[Rr]ev\.|(?:Seite|side)\s+[A-Z]|[a-d]\.)"

_RE = re.compile(
    rf"""^\s*
    (?:\{{(?P<frag>[^}}]*)\}}\s*)?
    (?P<surface>(?:{_EDGE}|{_SIDE})(?:\(\?\)|[!?])?\s*)?
    (?P<column>(?:{_NAMED_COL}|{_ROMAN})(?:\(\?\)|[!?])?\s*)?
    (?:
        (?P<n>\d+)
        (?P<prime>[′''’″‴´ˈ]*)
        (?P<tail>.*)
    )?
    \s*$""",
    re.X,
)

_SPLIT_FRAG = re.compile(r"[+,]")


@dataclass(slots=True)
class LineRef:
    raw: str
    frag: str = ""
    surface: str = ""
    column: str = ""
    ln: int | None = None
    prime: str = ""
    tail: str = ""

    @property
    def is_line(self) -> bool:
        return self.ln is not None

    @property
    def frags(self) -> tuple[str, ...]:
        """A composite siglum such as `€1+2` names several witnesses."""
        if not self.frag:
            return ()
        parts = [p.strip() for p in _SPLIT_FRAG.split(self.frag) if p.strip()]
        if not parts:
            return ()
        head = parts[0]
        prefix = head[0] if head and not head[0].isdigit() else ""
        return tuple(p if not p.isdigit() else prefix + p for p in parts)

    @property
    def lnno(self) -> str:
        """The citation form of the line within its column."""
        if self.ln is None:
            return ""
        return f"{self.ln}{self.prime}{self.tail}"

    @property
    def collabel(self) -> str:
        """Level-2 section label: unique within a document."""
        return " ".join(x for x in (self.frag, self.surface, self.column) if x)


def parse(value: str | None) -> LineRef:
    raw = value or ""
    m = _RE.match(raw)
    if not m:
        return LineRef(raw=raw)
    n = m.group("n")
    return LineRef(
        raw=raw,
        frag=(m.group("frag") or "").strip(),
        surface=(m.group("surface") or "").strip(),
        column=(m.group("column") or "").strip(),
        ln=int(n) if n is not None else None,
        prime=(m.group("prime") or ""),
        tail=(m.group("tail") or "").strip(),
    )
