"""Sign tokenisation (plan §3.1, §4.1).

Splits a `<w>`'s source bytes into signs.  A sign is a maximal run of transliteration
characters between `-` or `.` separators, within one wrapper context.

The hard requirement is that markers keep their exact position: `del_fin` sits mid-sign
55% of the time and `laes_fin` 89% of the time (research §8.1), so a tokeniser that
snapped markers to sign boundaries would move them.  Each sign therefore records its
markers as (tag, character-offset-within-the-sign) and keeps the verbatim source slice
in `srcxml`, such that ``srcxml + after`` concatenated over a word reproduces its source
bytes exactly.

This works on raw bytes rather than a parsed tree on purpose: parse-then-serialise is
not byte-preserving (plan §2.1).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# A literal space inside a <w> separates sign groups -- an Akkadogram from the
# Sumerogram that follows, say -- exactly as '-' and '.' do.  Treating it as content
# stranded it in an empty token, which the converter's filter then dropped.
SEPARATORS = "-. "

# Wrappers change the writing system of the run they enclose.
#
# `AO:Sumgram` / `AO:Akkgram` are the long-form spellings of `sGr` / `aGr`. They are
# rare -- 30 and 18 elements, over 212 signs -- but until they were mapped here they
# were the only thing `srcxml` held that no other feature did, which is what stopped
# the provenance layer being separable from the linguistic one.
WRAPPERS = {
    "sGr": "sgr", "aGr": "agr", "d": "det", "num": "num", "c": "signname",
    "AO:Sumgram": "sgr", "AO:Akkgram": "agr",
}

# Point markers whose @c value is carried onto the sign.
VALUED = {"corr", "subscr", "materlect", "surplus", "surpl"}

_TAG = re.compile(rb"<(/?)([A-Za-z_][-\w.:]*)((?:[^<>\"']|\"[^\"]*\"|'[^']*')*)(/?)>")
_ATTR = re.compile(r"""([-\w.:]+)\s*=\s*("([^"]*)"|'([^']*)')""")

# Editorial marks that appear inside a reading and are not part of the sign:
# `(` `)` uncertain word division, `〈` `〉` editorial insertion, `˽` a spacing mark,
# `_` which only ever occurs inside `(_)`.
#
# The angle brackets come in three encodings and this set once held the wrong two.
# TLHdig writes U+2329 and U+232A, which Unicode declares canonically equivalent to
# U+3008 and U+3009 -- the same characters under a deprecated encoding -- so a set built
# from the others matched none of the 8,972 brackets actually present. They stayed inside
# 963 distinct readings, where `〈aš〉` and `aš` were two different words to every query
# and neither could match a sign list. 4,326 signs.
#
# U+2039 and U+203A, the single guillemets, occur 16 times in the same role and are
# included on the same reasoning.
EDITORIAL_MARKS = frozenset(
    "()˽_"
    "\u3008\u3009"      # 〈 〉  ANGLE BRACKET
    "\u2329\u232a"      # 〈 〉  ANGLE BRACKET, deprecated; what this corpus writes
    "\u27e8\u27e9"      # ⟨ ⟩  MATHEMATICAL ANGLE BRACKET
    "\u2039\u203a"      # ‹ ›  SINGLE ANGLE QUOTATION MARK
)

_UNKNOWN = {"x", "X"}
_ELLIPSIS = {"…", "..."}


@dataclass(slots=True)
class Sign:
    """One sign slot."""

    srcxml: str = ""                 # verbatim source, markers in place
    sym: str = ""                    # clean reading, markers stripped
    after: str = ""                  # separator to the next sign
    type: str = "reading"
    sgr: int = 0
    agr: int = 0
    det: int = 0
    num: int = 0
    corr: str = ""
    subscr: str = ""
    materlect: str = ""
    surplus: str = ""
    space_count: int = 0
    symmark: str = ""                # editorial marks removed from `sym`, verbatim
    markers: list[tuple[str, int]] = field(default_factory=list)
    # <note n="1" c="..."/> carries a footnote; kept so the converter can build a
    # `note` node anchored to this sign rather than losing it in the marker list.
    note_attrs: list[dict] = field(default_factory=list)

    def _finish(self) -> None:
        if self.type != "reading":
            return
        s = self.sym.strip()
        if self.num:
            self.type = "numeral"
        elif s in _UNKNOWN:
            self.type = "unknown"
        elif s in _ELLIPSIS:
            self.type = "ellipsis"
        elif not s:
            self.type = "empty"


def _attrs(blob: str) -> dict[str, str]:
    return {m.group(1): (m.group(3) if m.group(3) is not None else m.group(4))
            for m in _ATTR.finditer(blob)}


def tokenise_word(data: bytes) -> list[Sign]:
    """Tokenise the inner bytes of one `<w>` element."""
    signs: list[Sign] = []
    cur = Sign()
    stack: list[str] = []            # active wrapper flags
    carry = ""                       # bytes belonging to the sign that follows
    carry_marks: list[tuple[str, int]] = []
    # Notes belong to whichever sign the carried bytes end up on.  They used to be
    # dropped here while markers were carried, costing 3,848 note nodes.
    carry_notes: list[dict] = []
    carry_vals: dict[str, str] = {}
    pending_space = 0
    pos = 0
    n = len(data)

    def flush(sep: str = "") -> None:
        """Emit the current sign, or defer it if it carries nothing of its own.

        Two shapes would otherwise strand a contentless sign, inventing a slot that
        corresponds to no sign on the tablet:

        * `<d>ḪI.A</d>-ia` -- the separator arrives just after a wrapper closed, so the
          current sign is empty.  The separator belongs to the sign that just ended.
        * `<aGr>-LIM</aGr>` and word-initial `-z...` -- the current sign holds only an
          opening tag, or nothing at all, before a separator.  Its bytes belong to the
          sign that *follows*, so they are carried forward rather than emitted.

        A token holding only *markers* is carried forward too.  It is not content --
        `<laes_in/>` before `<d>m</d>` belongs at offset 0 of the sign `m` -- and
        leaving it as its own empty token would let the converter's empty-token filter
        drop it, losing 1,707,240 bytes of editorial annotation across 130,028 words.
        Only a token with text or with its own layout space is emitted.
        """
        nonlocal cur, pending_space, carry, carry_marks, carry_vals, carry_notes
        # Editorial marks ride along inside the reading: `ta(-)la` tokenises to `ta(`
        # and `)la`, `〈ka〉` to `〈ka〉`. They are not part of the sign, they make `sym`
        # unmatchable against any sign table, and the cuneiform has no codepoint for a
        # bracket -- so they broke alignment before it started.
        #
        # This runs BEFORE `own_content` is decided. Doing it in `_finish()` left a
        # marks-only token looking like content, which then turned empty and was
        # dropped by the converter's filter along with its bytes: the filtered
        # round-trip failed on 6,368 files. Stripped here, such a token is contentless
        # like any other and carries forward.
        marks = [c for c in cur.sym if c in EDITORIAL_MARKS]
        if marks:
            cur.symmark = "".join(marks)
            cur.sym = "".join(c for c in cur.sym if c not in EDITORIAL_MARKS)
        # A space-only token carries too: leading space becomes the next sign's
        # space_count, and a trailing one is appended to the previous sign's `after`
        # so its bytes survive the empty-token filter.
        own_content = bool(cur.sym)
        if not own_content:
            if sep and signs and not cur.srcxml and not carry:
                signs[-1].after += sep       # separator belongs to the previous sign
            else:
                # Once bytes are being carried forward, the separator must join them.
                # Attaching it backwards would hoist it in front of the carried tags:
                # `pé<sGr>.</sGr>-an` would rebuild as `pé-<sGr>.</sGr>an`.
                carry_marks.extend(cur.markers)
                carry_notes.extend(cur.note_attrs)
                if cur.space_count:
                    pending_space += cur.space_count
                for f in ("corr", "subscr", "materlect", "surplus", "symmark"):
                    v = getattr(cur, f)
                    if v:
                        carry_vals[f] = v
                carry += cur.srcxml + sep
        else:
            cur.after = sep
            cur._finish()
            signs.append(cur)
        cur = Sign()
        for flag in stack:
            setattr(cur, flag, 1)
        if pending_space:
            cur.space_count = pending_space
            pending_space = 0

    if pending_space:
        cur.space_count = pending_space

    while pos < n:
        m = _TAG.search(data, pos)
        text_end = m.start() if m else n
        # --- literal text up to the next tag ---
        chunk = data[pos:text_end].decode("utf8")
        for ch in chunk:
            if ch in SEPARATORS:
                flush(ch)
            else:
                if carry:
                    cur.srcxml = carry + cur.srcxml
                    cur.markers = [(t, 0) for t, _ in carry_marks] + cur.markers
                    cur.note_attrs = carry_notes + cur.note_attrs
                    for f, v in carry_vals.items():
                        if not getattr(cur, f):
                            setattr(cur, f, v)
                    carry, carry_marks, carry_vals, carry_notes = "", [], {}, []
                cur.srcxml += ch
                cur.sym += ch
        if not m:
            break

        raw = m.group(0).decode("utf8")
        closing = m.group(1) == b"/"
        tag = m.group(2).decode("utf8")
        attrs = _attrs(m.group(3).decode("utf8"))
        pos = m.end()

        if tag in WRAPPERS and not closing:
            # a wrapper starts a new sign run
            if cur.srcxml:
                flush()
            flag = WRAPPERS[tag]
            if flag == "signname":
                cur.type = "signname"
            else:
                stack.append(flag)
                setattr(cur, flag, 1)
            cur.srcxml += raw
        elif tag in WRAPPERS and closing:
            cur.srcxml += raw
            flag = WRAPPERS[tag]
            if flag != "signname" and flag in stack:
                stack.remove(flag)
            flush()
        elif tag == "space":
            try:
                pending_space += int(attrs.get("c", "0") or 0)
            except ValueError:
                pass
            if cur.srcxml:
                cur.srcxml += raw
            else:
                cur.srcxml += raw
                cur.space_count = pending_space
                pending_space = 0
        else:
            # a point or range marker: record its offset inside this sign
            if carry:
                cur.srcxml = carry + cur.srcxml
                cur.markers = [(t, 0) for t, _ in carry_marks] + cur.markers
                cur.note_attrs = carry_notes + cur.note_attrs
                for f, v in carry_vals.items():
                    if not getattr(cur, f):
                        setattr(cur, f, v)
                carry, carry_marks, carry_vals, carry_notes = "", [], {}, []
            cur.markers.append((tag, len(cur.sym)))
            if tag == "note":
                cur.note_attrs.append({"n": attrs.get("n", ""), "c": attrs.get("c", "")})
            cur.srcxml += raw
            if tag in VALUED:
                val = attrs.get("c", "")
                if tag == "corr":
                    cur.corr = val
                elif tag == "subscr":
                    cur.subscr = val
                elif tag == "materlect":
                    cur.materlect = val
                else:
                    cur.surplus = val

    flush()
    if carry:
        if signs:
            # Trailing markers belong to the sign just emitted.  They go on `after`,
            # after any separator, so the byte order of srcxml + after is preserved.
            last = signs[-1]
            last.after += carry
            pending_space = 0
            last.markers.extend((t, len(last.sym)) for t, _ in carry_marks)
            last.note_attrs.extend(carry_notes)
            for f, v in carry_vals.items():
                if not getattr(last, f):
                    setattr(last, f, v)
        else:
            # a word made of nothing but markers: the converter turns this into a
            # layout node rather than dropping it
            tail = Sign(srcxml=carry, type="empty", markers=list(carry_marks),
                        note_attrs=list(carry_notes))
            # flush() hands pending_space straight to the fresh `cur`, so by now the
            # count may sit on either of them.
            tail.space_count = cur.space_count or pending_space
            for f, v in carry_vals.items():
                setattr(tail, f, v)
            for flag in stack:
                setattr(tail, flag, 1)
            signs.append(tail)
    return signs
