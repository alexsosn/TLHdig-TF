"""Byte-faithful source spans (plan §2.1, Contract A).

Structural interpretation of AOxml happens with lxml elsewhere.  This module does the
one thing lxml cannot: report exactly where in the *original bytes* each element lives,
so that a TF node can carry a `src_span` into the file it came from.

Why not lxml: it exposes `sourceline` only, not byte offsets.  `xml.parsers.expat`
exposes `CurrentByteIndex`, which is what we need.  And why byte spans at all: parsing
then re-serialising is never byte-preserving (namespace prefixes, entity spelling,
empty-element syntax and attribute quoting all drift), so reconstruction has to be done
by slicing the source, not by writing XML back out.
"""

from __future__ import annotations

from dataclasses import dataclass
from xml.parsers import expat


@dataclass(slots=True)
class Span:
    """One element's location in the source bytes.

    outer  -- from the '<' of the start tag to just past the '>' of the end tag
    inner  -- the content between the tags; None for a self-closing element,
              an empty span for `<w></w>`
    """

    tag: str
    depth: int
    order: int
    outer_start: int
    outer_end: int
    inner_start: int | None
    inner_end: int | None
    attrs: dict[str, str]
    self_closing: bool

    @property
    def outer(self) -> tuple[int, int]:
        return (self.outer_start, self.outer_end)

    @property
    def inner(self) -> tuple[int, int] | None:
        if self.inner_start is None:
            return None
        return (self.inner_start, self.inner_end)


def _tag_end(data: bytes, lt: int) -> tuple[int, bool]:
    """Given the offset of a '<', return (offset just past its '>', self_closing).

    Scans with quote awareness: a '>' inside an attribute value does not end the tag.
    AOxml does contain such values -- footnote `@c` attributes carry escaped markup --
    so a naive ``data.index(b'>', lt)`` is wrong here.
    """
    i = lt + 1
    quote = 0
    n = len(data)
    while i < n:
        c = data[i]
        if quote:
            if c == quote:
                quote = 0
        elif c in (0x22, 0x27):  # " '
            quote = c
        elif c == 0x3E:  # >
            return i + 1, data[i - 1] == 0x2F  # preceded by '/'
        i += 1
    raise ValueError(f"unterminated tag at byte {lt}")


def scan(data: bytes) -> list[Span]:
    """Return a Span for every element, in document order.

    The parser is namespace-unaware on purpose: we want the tag exactly as written
    (`AO:TxtPubl`, `text:tab`), because the span is about source text, not the infoset.
    """
    spans: list[Span] = []
    stack: list[Span] = []
    counter = [0]

    p = expat.ParserCreate()
    p.buffer_text = True

    def start(name, attrs):
        lt = p.CurrentByteIndex
        gt, self_closing = _tag_end(data, lt)
        sp = Span(
            tag=name,
            depth=len(stack),
            order=counter[0],
            outer_start=lt,
            outer_end=gt,          # provisional; fixed on end for non-self-closing
            inner_start=None if self_closing else gt,
            inner_end=None,
            attrs=dict(attrs),
            self_closing=self_closing,
        )
        counter[0] += 1
        spans.append(sp)
        stack.append(sp)

    def end(_name):
        sp = stack.pop()
        if sp.self_closing:
            return
        lt = p.CurrentByteIndex          # '<' of the closing tag
        gt, _ = _tag_end(data, lt)
        sp.inner_end = lt
        sp.outer_end = gt

    p.StartElementHandler = start
    p.EndElementHandler = end
    p.Parse(data, True)
    return spans


def inner_bytes(data: bytes, sp: Span) -> bytes:
    """The exact source bytes between an element's tags."""
    if sp.inner_start is None:
        return b""
    return data[sp.inner_start : sp.inner_end]


def outer_bytes(data: bytes, sp: Span) -> bytes:
    return data[sp.outer_start : sp.outer_end]


_PROLOG_OK = (b"<?", b"<!--", b"<!DOCTYPE")


def outside_root_ok(data: bytes, root: Span) -> bool:
    """True when everything outside the root element is legitimate prolog/epilog.

    AOxml files carry an `<?xml-stylesheet href="HPMxml.css"?>` processing instruction
    before the root -- valid XML, and the reason the corpus ships 184 CSS files.  Only
    whitespace may follow the root.
    """
    head = data[: root.outer_start]
    if data[root.outer_end :].strip():
        return False
    i, n = 0, len(head)
    while i < n:
        if head[i : i + 1].isspace():
            i += 1
            continue
        if head.startswith(b"<!--", i):
            j = head.find(b"-->", i)
            if j < 0:
                return False
            i = j + 3
        elif head.startswith(b"<?", i):
            j = head.find(b"?>", i)
            if j < 0:
                return False
            i = j + 2
        elif head.startswith(b"<!DOCTYPE", i):
            j = head.find(b">", i)
            if j < 0:
                return False
            i = j + 1
        else:
            return False
    return True


def verify_reconstruction(data: bytes, spans: list[Span]) -> list[str]:
    """Contract A self-check for one document.

    Every element's outer span must bracket its inner span, children must sit inside
    their parent, and slicing the root's outer span must return those exact bytes.
    Returns a list of problems; empty means the document round-trips.
    """
    problems: list[str] = []
    if not spans:
        return ["no elements"]

    root = spans[0]
    if outer_bytes(data, root) != data[root.outer_start : root.outer_end]:
        problems.append("root slice mismatch")

    stack: list[Span] = []
    for sp in spans:
        while stack and sp.outer_start >= stack[-1].outer_end:
            stack.pop()
        if sp.inner_start is not None:
            if not (sp.outer_start < sp.inner_start <= sp.inner_end < sp.outer_end):
                problems.append(f"{sp.tag}@{sp.outer_start}: inner not inside outer")
        if stack:
            parent = stack[-1]
            if parent.inner_start is None or not (
                parent.inner_start <= sp.outer_start and sp.outer_end <= parent.inner_end
            ):
                problems.append(
                    f"{sp.tag}@{sp.outer_start}: not contained in {parent.tag}"
                )
        stack.append(sp)
    return problems
