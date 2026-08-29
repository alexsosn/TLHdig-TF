"""Editorial bracket ranges -> cluster spans (plan §6, research §8.4).

The markers are `del_in`/`del_fin` (lacuna), `laes_in`/`laes_fin` (damaged but legible),
`ras_in`/`ras_fin` (erasure), `add_in`/`add_fin` (editorial addition) and the Hurrian
quotation pair.

What the corpus actually is, measured before this was written:

* They are **not** a matched-bracket language.  Document-scoped, 107,221 opens never
  close and 58,648 closes have no open; a naive depth counter reaches 148, which is not
  148 nested lacunae but accumulated orphans.
* Within a line they essentially never nest: `del` reaches depth >=2 in 0.06% of
  431,336 lines, `laes` in 0.03%.
* Families cross each other 248 times, so a single LIFO stack cannot pair them.

So there is no stack.  Each family carries one open slot, scoped to the line.  A close
with no open, and a line ending with one still open, are recorded as **orphan
boundaries** -- never back-projected into an invented span.

Whether a range survives the line boundary is decided by **lookahead**, not by policy.
Of the 186,648 lines that end with an unclosed `del_in`, only 40.0% are followed by a
line beginning with `del_fin`; 49.8% are followed by a fresh `del_in`, i.e. the open
marker meant "the rest of this line is broken" and was never intended to continue.
Persisting everything therefore invents 95,280 spurious reopens, and retiring
everything destroys 75,284 genuine cross-line breaks.  So a range persists only when the
next line actually opens with a matching close.
"""

from __future__ import annotations

from dataclasses import dataclass, field

OPEN = {
    "del_in": "del",
    "laes_in": "laes",
    "ras_in": "ras",
    "add_in": "add",
    "QUOT_HurInHit_in": "quot",
}
CLOSE = {
    "del_fin": "del",
    "laes_fin": "laes",
    "ras_fin": "ras",
    "add_fin": "add",
    "QUOT_HurInHit_fin": "quot",
}
FAMILIES = ("del", "laes", "ras", "add", "quot")


@dataclass(slots=True)
class Cluster:
    """One bracket range, in sign coordinates with intra-sign offsets."""

    type: str
    start_sign: int | None = None
    start_offset: int = 0        # character offset inside start_sign
    end_sign: int | None = None
    end_offset: int = 0
    start_line: int | None = None
    end_line: int | None = None
    orphan: str = "none"         # none | open | close
    nested: bool = False         # a second open of the same family was already active
    # Whether each end came from a real marker in the source, as opposed to a bound
    # synthesised from the line end, the document end, or a displacing reopen.  The
    # marker-conservation invariant counts these, not the coordinates: a synthesised
    # end is an extent, not a close.
    from_open_marker: bool = False
    from_close_marker: bool = False

    @property
    def crossesline(self) -> bool:
        return (
            self.start_line is not None
            and self.end_line is not None
            and self.start_line != self.end_line
        )


@dataclass(slots=True)
class Tracker:
    """Per-family open state, reset in a controlled way at each line boundary."""

    clusters: list[Cluster] = field(default_factory=list)
    _open: dict[str, Cluster] = field(default_factory=dict)
    _line: int | None = None
    stats: dict[str, int] = field(default_factory=dict)

    def _bump(self, k: str) -> None:
        self.stats[k] = self.stats.get(k, 0) + 1

    def start_line(self, line_no: int, continues: frozenset[str] = frozenset(),
                   last_slot: int | None = None, last_offset: int = 0) -> None:
        """Begin a new line.

        `continues` names the families whose range genuinely carries over -- in
        practice, those for which the incoming line *begins* with a matching close.
        Anything open but not continued is retired here as an orphan open rather than
        being dragged forward to collide with the next open of its family.
        """
        for fam in sorted(set(self._open) - set(continues)):
            cl = self._open.pop(fam)
            cl.orphan = "open"
            # The range has no closing marker, but its extent is known: it runs to the
            # end of the line it was opened on.  Leaving end_sign as None collapsed
            # every such cluster to its opening sign, contradicting the induced flags.
            if cl.end_sign is None and last_slot is not None:
                cl.end_sign = last_slot
                cl.end_offset = last_offset
            self.clusters.append(cl)
            self._bump(f"{fam}:retired_at_line_end")
        for fam in sorted(set(self._open) & set(continues)):
            self._bump(f"{fam}:continued_across_line")
        self._line = line_no

    def open(self, family: str, sign_idx: int | None, offset: int = 0) -> None:
        """Open a range of `family` at (sign, offset)."""
        prev = self._open.get(family)
        if prev is not None:
            # depth >= 2 within a line: ~0.06% of lines, treated as a probable
            # encoding error rather than modelled as real nesting.  The displaced
            # range never closes, so it is retired as an orphan open -- dropping it
            # would silently lose a marker that is present in the source.
            self._bump(f"{family}:reopened_while_open")
            prev.nested = True
            prev.orphan = "open"
            # The displaced range never closes, but its extent is bounded: it cannot
            # run past the marker that displaced it.  Leaving end_sign as None sent it
            # to the emitter with a single coordinate, collapsing it to one sign --
            # the same defect that was fixed for line-end orphans.
            if prev.end_sign is None and sign_idx is not None:
                prev.end_sign = sign_idx
                prev.end_offset = offset
            self.clusters.append(prev)
        cl = Cluster(
            type=family,
            start_sign=sign_idx,
            start_offset=offset,
            start_line=self._line,
            from_open_marker=True,
        )
        self._open[family] = cl
        self._bump(f"{family}:open")

    def close(self, family: str, sign_idx: int | None, offset: int = 0,
              line_start: int | None = None) -> None:
        cl = self._open.pop(family, None)
        if cl is None:
            # A close with no open: the range began before this fragment or line.
            # Recorded as a boundary, never expanded backwards into a span.
            # The opening marker is elsewhere (an earlier fragment or line), but the
            # extent within *this* line is known: it runs from the line's first sign.
            orphan = Cluster(
                type=family,
                start_sign=line_start,
                start_offset=0,
                start_line=self._line,
                end_sign=sign_idx,
                end_offset=offset,
                end_line=self._line,
                orphan="close",
                from_close_marker=True,
            )
            self.clusters.append(orphan)
            self._bump(f"{family}:orphan_close")
            return
        cl.end_sign = sign_idx
        cl.end_offset = offset
        cl.end_line = self._line
        cl.from_close_marker = True
        self.clusters.append(cl)
        self._bump(f"{family}:paired")

    def finish(self, last_slot: int | None = None, last_offset: int = 0) -> None:
        """Close the document.  Anything still open is an orphan open."""
        for fam, cl in sorted(self._open.items()):
            cl.orphan = "open"
            if cl.end_sign is None and last_slot is not None:
                cl.end_sign = last_slot
                cl.end_offset = last_offset
            self.clusters.append(cl)
            self._bump(f"{fam}:orphan_open")
        self._open.clear()

    def active(self) -> frozenset[str]:
        """Families currently open -- used to stamp induced flags on a sign."""
        return frozenset(self._open)


def feed(tracker: Tracker, tag: str, sign_idx: int | None, offset: int = 0,
         line_start: int | None = None) -> bool:
    """Route one marker tag. Returns True if the tag was a bracket marker.

    `offset` is the character position *within* the sign, which matters here: TLH
    brackets cut signs mid-way (research §8.1), so a cluster boundary is a
    (sign, offset) pair rather than a whole sign.
    """
    if tag in OPEN:
        tracker.open(OPEN[tag], sign_idx, offset)
        return True
    if tag in CLOSE:
        tracker.close(CLOSE[tag], sign_idx, offset, line_start)
        return True
    return False
