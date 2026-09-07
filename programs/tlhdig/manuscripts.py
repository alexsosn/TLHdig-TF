"""Parse the source-faithful ``AO:Manuscripts`` grammar.

The source has XML join separators, legacy textual separators, entry-internal chains,
and multiple apparatus blocks per document.  This module models source occurrence and
scope only; it never infers graph symmetry or transitivity.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from lxml import etree as ET


ENTRY_TAGS = {"TxtPubl": "txtpubl", "TextPubl": "txtpubl", "InvNr": "invnr"}
XML_OPERATORS = {"DirectJoin": "direct", "InDirectJoin": "indirect"}

# Measured line-used source sigla: €n (occasionally with internal whitespace), A1..B3,
# and bare numerals.  Attribute values remain more permissive because they are already
# explicit source keys; braced-text recognition stays on the measured grammar.
_SIGLUM_CORE = r"(?:€\s*\d+|[A-Za-z]\d+|\d+)"
_BRACED_SIGLUM = re.compile(rf"\{{\s*(?P<siglum>{_SIGLUM_CORE})\s*\}}")
_SIGLUM_SUFFIX = re.compile(rf"(?P<raw>\{{\s*(?P<siglum>{_SIGLUM_CORE})\s*\}})\s*$")
_TAIL_SIGLUM = re.compile(rf"^\s*(?P<raw>\{{\s*(?P<siglum>{_SIGLUM_CORE})\s*\}})")
_PLAIN_ENTRY = re.compile(
    rf"(?P<label>[^{{}}]*?\S)\s*(?P<raw>\{{\s*(?P<siglum>{_SIGLUM_CORE})\s*\}})"
)
_SPACED_DIRECT = re.compile(r"\s+\+\s+")
_MARKER_CANDIDATE = re.compile(r"(?P<marker>\(\+\)\s*\?|\+\s*\?|\+\+|\(\+\)|\+)")
_STATUS_SUFFIX = re.compile(
    r"^(?P<label>.*?)(?P<marker>(?:\(\+\)){2,}|\+\+|\(\+\)|\+)\s*$"
)


@dataclass
class Entry:
    """One manuscript-entry occurrence in source order inside one block."""

    order: int
    kind: str
    label: str
    siglum: str = ""
    siglum_source: str = ""
    siglum_raw: str = ""
    siglum_candidates: tuple[str, ...] = ()
    siglum_raw_candidates: tuple[str, ...] = ()


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
    context: str = ""


@dataclass(frozen=True)
class Apparatus:
    entries: tuple[Entry, ...]
    statements: tuple[Statement, ...]
    duplicate_sigla: dict[str, tuple[int, ...]]
    conflicting_boundaries: dict[tuple[int, int], tuple[str, ...]]
    residual_text: tuple[str, ...] = ()


@dataclass(frozen=True)
class BlockScope:
    """One source ``Manuscripts`` block and its block-local parsed apparatus."""

    order: int
    element: object
    apparatus: Apparatus


@dataclass(frozen=True)
class LineScope:
    """One source line and the most recent preceding apparatus block."""

    element: object
    block: int | None


@dataclass(frozen=True)
class DocumentApparatus:
    """All apparatus blocks and line scopes under one ``body/div1``."""

    blocks: tuple[BlockScope, ...]
    lines: tuple[LineScope, ...]


@dataclass(frozen=True)
class _Separator:
    kind: str
    encoding: str
    raw: str
    context: str = ""


@dataclass(frozen=True)
class _Barrier:
    raw: str


def _lname(element) -> str:
    tag = element.tag
    return ET.QName(tag).localname if isinstance(tag, str) else ""


def _normalise(raw: str | None) -> str:
    return " ".join((raw or "").split())


def _normalise_siglum(raw: str | None) -> str:
    value = _normalise(raw)
    if value.startswith("€"):
        return "€" + "".join(value[1:].split())
    return value


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


def _iter_markers(text: str):
    """Yield canonical textual operators without promoting publication suffixes.

    Operators may touch a closing siglum brace (``{€2}+ KUB``), but a plus attached to
    an ordinary publication token (``KUB 47.90+``) is not manuscript syntax.
    """
    for match in _MARKER_CANDIDATE.finditer(text):
        start, end = match.span()
        left = text[start - 1] if start else ""
        right = text[end] if end < len(text) else ""
        left_ok = not left or left.isspace() or left == "}"
        right_ok = not right or right.isspace() or right == "{"
        if left_ok and right_ok:
            yield match


def _candidate(entry: Entry, siglum: str, source: str, *, raw: str | None = None) -> None:
    """Attach normalized + raw siglum evidence without guessing on disagreement."""
    siglum = _normalise_siglum(siglum)
    if not siglum:
        return
    candidates = list(entry.siglum_candidates)
    if siglum not in candidates:
        candidates.append(siglum)
    entry.siglum_candidates = tuple(candidates)

    raw_value = siglum if raw is None else raw
    raw_candidates = list(entry.siglum_raw_candidates)
    if raw_value and raw_value not in raw_candidates:
        raw_candidates.append(raw_value)
    entry.siglum_raw_candidates = tuple(raw_candidates)

    if len(candidates) == 1:
        entry.siglum = candidates[0]
        if not entry.siglum_source:
            entry.siglum_source = source
            entry.siglum_raw = raw_value
        return

    entry.siglum = ""
    entry.siglum_source = "conflict"
    entry.siglum_raw = ""


def _entry_from_segment(segment: str, order: int, kind: str, source: str) -> Entry | None:
    """Turn one operator-delimited source segment into one occurrence."""
    value = segment.strip()
    if not value:
        return None
    match = _SIGLUM_SUFFIX.search(value)
    if match:
        label = _normalise(value[: match.start()])
        raw = match.group("raw")
        siglum = _normalise_siglum(match.group("siglum"))
    else:
        label = _normalise(value)
        raw = ""
        siglum = ""
    if not label:
        return None
    entry = Entry(order=order, kind=kind, label=label)
    if siglum:
        _candidate(entry, siglum, source, raw=raw)
    return entry


def _append_element(
    element,
    tokens: list[object],
    entries: list[Entry],
) -> Entry | None:
    """Append one entry element, splitting measured entry-internal join chains."""
    kind = ENTRY_TAGS[_lname(element)]
    source_text = "".join(element.itertext())
    markers = list(_iter_markers(source_text))
    made: list[Entry] = []

    if not markers:
        entry = _entry_from_segment(source_text, len(entries) + 1, kind, "element-text")
        if entry is None:
            # Preserve an empty source occurrence rather than deleting the element.
            entry = Entry(order=len(entries) + 1, kind=kind, label=_normalise(source_text))
        entries.append(entry)
        tokens.append(entry)
        made.append(entry)
    else:
        cursor = 0
        for match in markers:
            entry = _entry_from_segment(
                source_text[cursor : match.start()], len(entries) + 1, kind, "element-text"
            )
            if entry is not None:
                entries.append(entry)
                tokens.append(entry)
                made.append(entry)
            marker = _normalise(match.group("marker"))
            tokens.append(_Separator(_marker_kind(marker), "textual", marker))
            cursor = match.end()
        entry = _entry_from_segment(source_text[cursor:], len(entries) + 1, kind, "element-text")
        if entry is not None:
            entries.append(entry)
            tokens.append(entry)
            made.append(entry)

    # @nr is element-level evidence.  It is unambiguous for a single occurrence.  For
    # a split element, attach it only when it agrees with exactly one braced occurrence;
    # otherwise do not invent which internal occurrence it names.
    attr_raw = element.get("nr") or ""
    attr = _normalise_siglum(attr_raw)
    if attr and made:
        if len(made) == 1:
            _candidate(made[0], attr, "attr", raw=attr_raw)
        else:
            agreeing = [entry for entry in made if entry.siglum == attr]
            if len(agreeing) == 1:
                _candidate(agreeing[0], attr, "attr", raw=attr_raw)

    return made[-1] if made else None


def _append_plain_segment(
    segment: str,
    tokens: list[object],
    entries: list[Entry],
    residuals: list[str],
) -> None:
    """Parse zero or more explicit ``label {siglum}`` entries from marker-free text."""
    if not segment or not segment.strip():
        return
    cursor = 0
    found = False
    for match in _PLAIN_ENTRY.finditer(segment):
        prefix = _normalise(segment[cursor : match.start()])
        label = _normalise((prefix + " " + match.group("label")).strip())
        if not label:
            raw = _normalise(match.group(0))
            residuals.append(raw)
            tokens.append(_Barrier(raw))
        else:
            raw_siglum = match.group("raw")
            siglum = _normalise_siglum(match.group("siglum"))
            entry = Entry(order=len(entries) + 1, kind="plain", label=label)
            _candidate(entry, siglum, "plain-text", raw=raw_siglum)
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


def _append_text_only_chain(raw: str | None, tokens: list[object], entries: list[Entry]) -> bool:
    """Parse the measured block-text ``label + label [+ label]`` grammar."""
    text = _normalise(raw)
    if not text or _BRACED_SIGLUM.search(text):
        return False
    labels = [part.strip() for part in _SPACED_DIRECT.split(text)]
    if len(labels) < 2 or any(not label for label in labels):
        return False
    for index, label in enumerate(labels):
        entry = Entry(order=len(entries) + 1, kind="plain", label=label)
        entries.append(entry)
        tokens.append(entry)
        if index + 1 < len(labels):
            tokens.append(_Separator("direct", "textual", "+"))
    return True


def _append_opaque_text(raw: str | None, tokens: list[object], residuals: list[str]) -> None:
    value = _normalise(raw)
    if not value:
        return
    residuals.append(value)
    tokens.append(_Barrier(value))


def _append_text(
    raw: str | None,
    tokens: list[object],
    entries: list[Entry],
    residuals: list[str],
    *,
    attach_to: Entry | None = None,
    allow_text_chain: bool = False,
) -> None:
    """Append mixed block/tail text and preserve unsafe contexts as barriers."""
    text = raw or ""

    if allow_text_chain and _append_text_only_chain(text, tokens, entries):
        return

    # A block consisting only of a manuscript label plus a trailing status marker
    # (for example ``KBo 24.129 +``) has no serialized fragment endpoint. Recognize
    # that measured shape before the generic marker scanner consumes the marker and
    # leaves the label as an unrelated barrier. Braced sigla are excluded so a real
    # fragment occurrence such as ``KBo 1.1 {€1} +`` keeps its one-sided endpoint.
    if allow_text_chain and not _BRACED_SIGLUM.search(text):
        status = _STATUS_SUFFIX.match(_normalise(text))
        if status and status.group("label").strip():
            label = _normalise(status.group("label"))
            residuals.append(label)
            tokens.append(_Barrier(label))
            marker = _normalise(status.group("marker"))
            tokens.append(_Separator(_marker_kind(marker), "textual", marker, context=label))
            return

    if attach_to is not None:
        match = _TAIL_SIGLUM.match(text)
        if match:
            _candidate(
                attach_to,
                match.group("siglum"),
                "tail",
                raw=match.group("raw"),
            )
            text = text[match.end() :]

    compact_tail = _normalise(text)
    if attach_to is not None and compact_tail.startswith("#"):
        _append_opaque_text(compact_tail, tokens, residuals)
        return

    markers = list(_iter_markers(text))

    # Non-canonical join-shaped tails are retained but never promoted to binary joins.
    if attach_to is not None and compact_tail and not markers:
        if "+" in compact_tail or "(" in compact_tail:
            tokens.append(_Separator("malformed", "textual", compact_tail))
            return

    if not markers:
        status = _STATUS_SUFFIX.match(_normalise(text))
        if status and status.group("label").strip():
            label = _normalise(status.group("label"))
            residuals.append(label)
            tokens.append(_Barrier(label))
            marker = _normalise(status.group("marker"))
            tokens.append(_Separator(_marker_kind(marker), "textual", marker, context=label))
            return

    cursor = 0
    for match in markers:
        _append_plain_segment(text[cursor : match.start()], tokens, entries, residuals)
        marker = _normalise(match.group("marker"))
        tokens.append(_Separator(_marker_kind(marker), "textual", marker))
        cursor = match.end()
    _append_plain_segment(text[cursor:], tokens, entries, residuals)


def _neighbour(tokens: list[object], index: int, step: int) -> Entry | None:
    """Find the adjacent occurrence; separators are transparent, barriers are not."""
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
    return {siglum: tuple(orders) for siglum, orders in grouped.items() if len(orders) > 1}


def parse(block) -> Apparatus:
    """Parse one ``AO:Manuscripts`` element without adding graph semantics."""
    tokens: list[object] = []
    entries: list[Entry] = []
    residuals: list[str] = []

    _append_text(block.text, tokens, entries, residuals, allow_text_chain=True)

    for child in block:
        if not isinstance(child.tag, str):
            continue
        name = _lname(child)
        if name in ENTRY_TAGS:
            last_entry = _append_element(child, tokens, entries)
            _append_text(child.tail, tokens, entries, residuals, attach_to=last_entry)
            continue
        if name in XML_OPERATORS:
            tokens.append(_Separator(XML_OPERATORS[name], "xml", name))
            _append_text(child.tail, tokens, entries, residuals)
            continue

        tokens.append(_Barrier(name))
        _append_opaque_text(child.tail, tokens, residuals)

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
                context=token.context,
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


def parse_document(div1) -> DocumentApparatus:
    """Parse every apparatus block and assign lines by preceding source order.

    The active witness apparatus is the most recent ``Manuscripts`` block encountered
    before a line in ``body/div1`` document order.  Blocks are all ledgered, including
    siblings before ``text`` and trailing blocks after the final line.
    """
    if div1 is None:
        return DocumentApparatus(blocks=(), lines=())

    blocks: list[BlockScope] = []
    lines: list[LineScope] = []
    active: int | None = None
    for element in div1.iter():
        if element is div1 or not isinstance(element.tag, str):
            continue
        name = _lname(element)
        if name == "Manuscripts":
            active = len(blocks) + 1
            blocks.append(BlockScope(order=active, element=element, apparatus=parse(element)))
        elif name == "lb":
            lines.append(LineScope(element=element, block=active))
    return DocumentApparatus(blocks=tuple(blocks), lines=tuple(lines))
