"""Parse the mixed-content ``AO:Manuscripts`` source grammar.

The TLHdig source has two generations of join notation: empty XML separator elements
(``DirectJoin`` / ``InDirectJoin``) and textual ``+`` / ``(+)`` markers between
manuscript entries.  This module models source occurrences and statements only.  It does
not infer symmetry, transitivity, or graph resolution across documents; those belong to
the issue #18 graph-emission layer.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from lxml import etree as ET


ENTRY_TAGS = {"TxtPubl": "txtpubl", "TextPubl": "txtpubl", "InvNr": "invnr"}
XML_OPERATORS = {"DirectJoin": "direct", "InDirectJoin": "indirect"}
_SIGLUM_SUFFIX = re.compile(r"\{\s*(€\d+)\s*\}\s*$")
_TAIL_SIGLUM = re.compile(r"^\s*\{\s*(€\d+)\s*\}")
_PLAIN_ENTRY = re.compile(r"(?P<label>[^{}]+?\S)\s*\{\s*(?P<siglum>€\d+)\s*\}")
_MARKER = re.compile(
    r"(?<!\S)(?P<marker>\(\+\)\s*\?|\+\s*\?|\+\+|\(\+\)|\+)(?!\S)"
)
# Old records also use a marker as a target-less status suffix, often attached directly
# to the publication label (``KBo 31.5++``, ``KBo 23.116(+)``).  Repeated parenthesised
# pluses are a real corpus shape and must survive as one raw statement rather than being
# split into invented binary joins.
_STATUS_SUFFIX = re.compile(
    r"^(?P<label>.*?)(?P<marker>(?:\(\+\)){2,}|\+\+|\(\+\)|\+)\s*$"
)


@dataclass
class Entry:
    """One manuscript-entry occurrence in source order."""

    order: int
    kind: str
    label: str
    siglum: str = ""
    siglum_source: str = ""
    siglum_candidates: tuple[str, ...] = ()


@dataclass(frozen=True)
class Statement:
    """One source join statement, whether safely binary or unresolved."""

    order: int
    kind: str
    encoding: str
    raw: str
    left: int | None
    right: int | None
    resolved: bool


@dataclass(frozen=True)
class Apparatus:
    entries: tuple[Entry, ...]
    statements: tuple[Statement, ...]
    duplicate_sigla: dict[str, tuple[int, ...]]
    conflicting_boundaries: dict[tuple[int, int], tuple[str, ...]]
    residual_text: tuple[str, ...] = ()


@dataclass(frozen=True)
class _Separator:
    kind: str
    encoding: str
    raw: str


@dataclass(frozen=True)
class _Barrier:
    raw: str


def _lname(element) -> str:
    tag = element.tag
    return ET.QName(tag).localname if isinstance(tag, str) else ""


def _normalise(raw: str | None) -> str:
    return " ".join((raw or "").split())


def _marker_kind(raw: str) -> str:
    compact = "".join(raw.split())
    if compact == "+":
        return "direct"
    if compact == "(+)":
        return "indirect"
    if compact == "++":
        return "direct-multi"
    if compact in {"+?", "(+)?"}:
        return "uncertain"
    if compact.startswith("(+)") and compact == "(+)" * compact.count("(+)"):
        return "indirect-multi"
    return "unknown"


def _candidate(entry: Entry, siglum: str, source: str) -> None:
    """Attach siglum evidence without guessing when sources disagree."""
    if not siglum:
        return
    candidates = list(entry.siglum_candidates)
    if siglum not in candidates:
        candidates.append(siglum)
    entry.siglum_candidates = tuple(candidates)

    if len(candidates) == 1:
        entry.siglum = candidates[0]
        if not entry.siglum_source:
            entry.siglum_source = source
        return

    entry.siglum = ""
    entry.siglum_source = "conflict"


def _element_entry(element, order: int) -> Entry:
    name = _lname(element)
    raw_label = _normalise("".join(element.itertext()))
    text_match = _SIGLUM_SUFFIX.search(raw_label)
    text_siglum = ""
    if text_match:
        text_siglum = text_match.group(1)
        raw_label = raw_label[: text_match.start()].rstrip()

    result = Entry(order=order, kind=ENTRY_TAGS[name], label=raw_label)
    attr = _normalise(element.get("nr"))
    if attr:
        _candidate(result, attr, "attr")
    if text_siglum:
        _candidate(result, text_siglum, "element-text")
    return result


def _append_plain_segment(
    segment: str,
    tokens: list[object],
    entries: list[Entry],
    residuals: list[str],
) -> None:
    """Parse zero or more explicit ``label {€n}`` entries from marker-free text."""
    if not segment or not segment.strip():
        return
    cursor = 0
    found = False
    for match in _PLAIN_ENTRY.finditer(segment):
        prefix = _normalise(segment[cursor : match.start()])
        # A prefix before the first explicit entry is part of that label because the
        # source grammar itself identifies the endpoint with the following {€n}.
        label = _normalise((prefix + " " + match.group("label")).strip())
        if not label:
            residuals.append(_normalise(match.group(0)))
            tokens.append(_Barrier(_normalise(match.group(0))))
        else:
            entry = Entry(
                order=len(entries) + 1,
                kind="plain",
                label=label,
                siglum=match.group("siglum"),
                siglum_source="plain-text",
                siglum_candidates=(match.group("siglum"),),
            )
            entries.append(entry)
            tokens.append(entry)
        cursor = match.end()
        found = True

    remainder = _normalise(segment[cursor:])
    if remainder:
        residuals.append(remainder)
        tokens.append(_Barrier(remainder))
    elif not found:
        value = _normalise(segment)
        if value:
            residuals.append(value)
            tokens.append(_Barrier(value))


def _append_text(
    raw: str | None,
    tokens: list[object],
    entries: list[Entry],
    residuals: list[str],
    *,
    attach_to: Entry | None = None,
) -> None:
    """Append mixed text following an element, attaching a leading tail siglum."""
    text = raw or ""
    if attach_to is not None:
        match = _TAIL_SIGLUM.match(text)
        if match:
            _candidate(attach_to, match.group(1), "tail")
            text = text[match.end() :]

    # A non-canonical join-shaped tail is still source evidence.  The research census
    # found eight such tails (e.g. ``{€4} (+`` and ``{€1} (``).  They are deliberately
    # unresolved; do not turn nearby entries into an edge just because punctuation is
    # suggestive.
    compact_tail = _normalise(text)
    if attach_to is not None and compact_tail and not _MARKER.search(text):
        if "+" in compact_tail or "(" in compact_tail:
            tokens.append(_Separator("malformed", "textual", compact_tail))
            return

    # Some old blocks store only a publication/status string, with the join marker
    # attached to the label and no named target. Preserve the label as residual source
    # text and the marker as its own unresolved statement. This branch intentionally
    # runs only when there is no normal whitespace-delimited marker in the chunk.
    if not _MARKER.search(text):
        status = _STATUS_SUFFIX.match(_normalise(text))
        if status and status.group("label").strip():
            label = _normalise(status.group("label"))
            residuals.append(label)
            tokens.append(_Barrier(label))
            marker = _normalise(status.group("marker"))
            tokens.append(_Separator(_marker_kind(marker), "textual", marker))
            return

    cursor = 0
    for match in _MARKER.finditer(text):
        _append_plain_segment(text[cursor : match.start()], tokens, entries, residuals)
        marker = _normalise(match.group("marker"))
        tokens.append(_Separator(_marker_kind(marker), "textual", marker))
        cursor = match.end()
    _append_plain_segment(text[cursor:], tokens, entries, residuals)


def _neighbour(tokens: list[object], index: int, step: int) -> Entry | None:
    """Find the adjacent source entry; separators are transparent, barriers are not."""
    pos = index + step
    while 0 <= pos < len(tokens):
        token = tokens[pos]
        if isinstance(token, Entry):
            return token
        if isinstance(token, _Barrier):
            return None
        pos += step
    return None


def _duplicates(entries: Iterable[Entry]) -> dict[str, tuple[int, ...]]:
    grouped: dict[str, list[int]] = {}
    for entry in entries:
        if entry.siglum:
            grouped.setdefault(entry.siglum, []).append(entry.order)
    return {
        siglum: tuple(orders)
        for siglum, orders in grouped.items()
        if len(orders) > 1
    }


def parse(block) -> Apparatus:
    """Parse one ``AO:Manuscripts`` element without adding graph semantics."""
    tokens: list[object] = []
    entries: list[Entry] = []
    residuals: list[str] = []

    _append_text(block.text, tokens, entries, residuals)

    for child in block:
        if not isinstance(child.tag, str):
            continue
        name = _lname(child)
        if name in ENTRY_TAGS:
            entry = _element_entry(child, len(entries) + 1)
            entries.append(entry)
            tokens.append(entry)
            _append_text(child.tail, tokens, entries, residuals, attach_to=entry)
            continue

        if name in XML_OPERATORS:
            tokens.append(_Separator(XML_OPERATORS[name], "xml", name))
            _append_text(child.tail, tokens, entries, residuals)
            continue

        # Notes/layout/corrupt children may carry text, but they break a safe binary
        # adjacency. Preserve the barrier and parse any following tail independently.
        tokens.append(_Barrier(name))
        _append_text(child.tail, tokens, entries, residuals)

    statements: list[Statement] = []
    for index, token in enumerate(tokens):
        if not isinstance(token, _Separator):
            continue
        left = _neighbour(tokens, index, -1)
        right = _neighbour(tokens, index, 1)
        binary_kind = token.kind in {"direct", "indirect"}
        resolved = binary_kind and left is not None and right is not None
        statements.append(
            Statement(
                order=len(statements) + 1,
                kind=token.kind,
                encoding=token.encoding,
                raw=token.raw,
                left=left.order if left is not None else None,
                right=right.order if right is not None else None,
                resolved=resolved,
            )
        )

    boundary_kinds: dict[tuple[int, int], set[str]] = {}
    for statement in statements:
        if statement.left is None or statement.right is None:
            continue
        if statement.kind not in {"direct", "indirect"}:
            continue
        boundary_kinds.setdefault((statement.left, statement.right), set()).add(statement.kind)
    conflicts = {
        boundary: tuple(sorted(kinds))
        for boundary, kinds in boundary_kinds.items()
        if len(kinds) > 1
    }

    return Apparatus(
        entries=tuple(entries),
        statements=tuple(statements),
        duplicate_sigla=_duplicates(entries),
        conflicting_boundaries=conflicts,
        residual_text=tuple(residuals),
    )
