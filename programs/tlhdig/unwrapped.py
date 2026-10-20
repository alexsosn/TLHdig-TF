"""Byte-exact lexical group boundaries in explicitly unwrapped AOxml (#158).

This is deliberately *not* another sign tokenizer. Each returned [start, end)
is a slice of the original UTF-8 source, suitable for signs.tokenise_word().
No synthetic <w> markup is introduced, and unsupported XML fails closed.

Only call on the content of one line after its <lb> and before the next
structural boundary; the caller owns paragraph/line/provenance identity.
"""
from __future__ import annotations

from .signs import _TAG, WRAPPERS

# Source structural elements must never be fed as lexical content.
STRUCTURAL = frozenset(("w", "lb", "clb", "parsep", "parsep_dbl", "P___Standard"))
WS = frozenset(b" \t\r\n")


class UnwrappedBoundaryError(ValueError):
    """Source segment is not safe to reinterpret as lexical groups."""


def groups(data: bytes, start: int, end: int) -> tuple[tuple[int, int], ...]:
    """Return source offsets of whitespace-delimited unwrapped lexical groups.

    Separators inside an active writing-system wrapper are content, not word
    boundaries. Spaces and annotation-only fragments between words are owned
    by the following group, so concatenating the extracted slices reproduces
    the segment exactly. They are not interpreted as missing sign readings.
    """
    if not (0 <= start <= end <= len(data)):
        raise ValueError("unwrapped source offsets out of bounds")
    if start == end:
        return ()

    out: list[tuple[int, int]] = []
    stack: list[str] = []
    group_start = start
    readable = False
    pos = start

    def plain(a: int, b: int) -> None:
        nonlocal group_start, readable
        if b"<" in data[a:b]:
            raise UnwrappedBoundaryError("unparsed markup in unwrapped source segment")
        # Only ASCII XML whitespace breaks source lexical groups. Unicode bytes
        # are never split mid-character.
        for i in range(a, b):
            byte = data[i]
            if byte in WS and not stack:
                if readable:
                    out.append((group_start, i))
                    group_start = i
                    readable = False
            else:
                if byte not in WS:
                    readable = True

    for match in _TAG.finditer(data, start, end):
        if match.start() < pos or match.end() > end:
            continue
        plain(pos, match.start())
        tag = match.group(2).decode("ascii")
        closing = match.group(1) == b"/"
        self_closing = match.group(4) == b"/"
        if tag in STRUCTURAL:
            raise UnwrappedBoundaryError(f"source structure {tag} inside lexical region")
        if tag in WRAPPERS:
            if closing:
                if not stack or stack[-1] != tag:
                    raise UnwrappedBoundaryError(f"unbalanced lexical wrapper {tag}")
                stack.pop()
            elif not self_closing:
                stack.append(tag)
        elif not self_closing and not closing:
            raise UnwrappedBoundaryError(f"unsupported nested lexical markup {tag}")
        elif closing:
            raise UnwrappedBoundaryError(f"unexpected closing markup {tag}")
        pos = match.end()

    plain(pos, end)
    if stack:
        raise UnwrappedBoundaryError(f"unclosed lexical wrapper {stack[-1]}")

    if readable:
        out.append((group_start, end))
    elif out:
        a, _ = out[-1]
        out[-1] = (a, end)

    if out and (out[0][0] != start or out[-1][1] != end or
                any(b != c for (_, b), (c, _) in zip(out, out[1:]))):
        raise AssertionError("unwrapped groups must partition original source bytes")
    return tuple(out)
