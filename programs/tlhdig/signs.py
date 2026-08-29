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

SEPARATORS = "-."

# Wrappers change the writing system of the run they enclose.
WRAPPERS = {"sGr": "sgr", "aGr": "agr", "d": "det", "num": "num", "c": "signname"}

# Point markers whose @c value is carried onto the sign.
VALUED = {"corr", "subscr", "materlect", "surplus", "surpl"}

_TAG = re.compile(rb"<(/?)([A-Za-z_][-\w.:]*)((?:[^<>\"']|\"[^\"]*\"|'[^']*')*)(/?)>")
_ATTR = re.compile(r"""([-\w.:]+)\s*=\s*("([^"]*)"|'([^']*)')""")

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
    markers: list[tuple[str, int]] = field(default_factory=list)

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

        Carrying forward is only safe when the sign has no text, no markers and no
        space of its own; anything else is real content and is emitted.
        """
        nonlocal cur, pending_space, carry
        own_content = bool(cur.sym) or bool(cur.markers) or bool(cur.space_count)
        if not own_content:
            if sep and signs and not cur.srcxml and not carry:
                signs[-1].after += sep       # separator belongs to the previous sign
            else:
                # Once bytes are being carried forward, the separator must join them.
                # Attaching it backwards would hoist it in front of the carried tags:
                # `pé<sGr>.</sGr>-an` would rebuild as `pé-<sGr>.</sGr>an`.
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
                    carry = ""
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
                carry = ""
            cur.markers.append((tag, len(cur.sym)))
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
        # nothing followed; keep the bytes so the round-trip stays exact
        tail = Sign(srcxml=carry, type="empty")
        for flag in stack:
            setattr(tail, flag, 1)
        signs.append(tail)
    return signs
