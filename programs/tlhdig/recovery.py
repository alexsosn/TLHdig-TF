"""Signature-scoped structural recovery for reviewed TLHdig word-stack defects.

Phase 2 of #12 deliberately exposes a logical event view rather than a corrected XML
byte stream. The immutable source remains the provenance authority; mechanical XML
repairs are applied by tlhdig.prepared_source, while the recovery decisions below are
represented as events anchored back to immutable-source offsets.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

from . import prepared_source, repair
from .paths import PROGRAMS


DISPOSITIONS = PROGRAMS / "source_recovery_dispositions.json"
_NAME = re.compile(rb"[A-Za-z_][A-Za-z0-9_.:-]*")
_ONLY_WORD_CLOSES = re.compile(rb"(?:</w>)+")
_ALLOWED_KINDS = {
    "implicit_word_close_before_word",
    "implicit_word_close_before_line",
    "implicit_word_close_before_text_end",
}


class RecoveryError(RuntimeError):
    """Base class for structural-recovery contract failures."""


class NotWordResynchronization(RecoveryError):
    """The reviewed source belongs to another recovery family."""


class SignatureDrift(RecoveryError):
    """Pinned source/policy facts no longer match the supported recovery signature."""


@dataclass(frozen=True, slots=True)
class MarkupToken:
    """One literal source markup token.

    mechanical_* coordinates index PreparedSource.mechanical_bytes.
    start_offset/end_offset index the immutable source named by src_file.
    Recovery never inserts synthetic tokens into this sequence.
    """

    kind: str
    tag: str
    mechanical_start: int
    mechanical_end: int
    start_offset: int
    end_offset: int
    synthetic: bool = False


@dataclass(frozen=True, slots=True)
class RecoveryEvent:
    """One logical word-state decision anchored in immutable-source coordinates."""

    kind: str
    element: str
    start_offset: int
    end_offset: int
    trigger_offset: int
    omitted_bytes: int
    omitted_semantic_annotation: bool


@dataclass(frozen=True, slots=True)
class WordRecoveryView:
    """Literal markup plus logical recovery decisions for one reviewed source."""

    path: str
    source_sha256: str
    tokens: tuple[MarkupToken, ...]
    events: tuple[RecoveryEvent, ...]


def _tag_end(data: bytes, lt: int) -> int:
    """Return the byte offset just past a tag's closing delimiter."""

    quote = 0
    i = lt + 1
    while i < len(data):
        c = data[i]
        if quote:
            if c == quote:
                quote = 0
        elif c in (0x22, 0x27):
            quote = c
        elif c == 0x3E:
            return i + 1
        i += 1
    raise SignatureDrift(f"unterminated markup token at byte {lt}")


def _skip_non_element(data: bytes, lt: int) -> int | None:
    """Return the end of comments/PIs/declarations, else None."""

    if data.startswith(b"<!--", lt):
        end = data.find(b"-->", lt + 4)
        if end < 0:
            raise SignatureDrift(f"unterminated XML comment at byte {lt}")
        return end + 3
    if data.startswith(b"<![CDATA[", lt):
        end = data.find(b"]]>", lt + 9)
        if end < 0:
            raise SignatureDrift(f"unterminated CDATA section at byte {lt}")
        return end + 3
    if data.startswith(b"<?", lt):
        end = data.find(b"?>", lt + 2)
        if end < 0:
            raise SignatureDrift(f"unterminated processing instruction at byte {lt}")
        return end + 2
    if data.startswith(b"<!", lt):
        return _tag_end(data, lt)
    return None


def _mapped_offset(
    offset_map: repair.OffsetMap | None,
    offset: int,
) -> int:
    return offset if offset_map is None else offset_map.to_original(offset)


def scan_markup(
    data: bytes,
    *,
    offset_map: repair.OffsetMap | None = None,
) -> tuple[MarkupToken, ...]:
    """Lex literal XML element tags without requiring a balanced tree."""

    tokens: list[MarkupToken] = []
    pos = 0
    while True:
        lt = data.find(b"<", pos)
        if lt < 0:
            break

        skipped = _skip_non_element(data, lt)
        if skipped is not None:
            pos = skipped
            continue

        end = _tag_end(data, lt)
        body = data[lt + 1 : end - 1].strip()
        if not body:
            raise SignatureDrift(f"empty markup token at byte {lt}")

        is_end = body.startswith(b"/")
        name_body = body[1:].lstrip() if is_end else body
        match = _NAME.match(name_body)
        if match is None:
            raise SignatureDrift(
                f"unsupported markup token at byte {lt}: {body[:120]!r}"
            )
        tag = match.group(0).decode("utf8", "surrogateescape")

        if is_end:
            kind = "end"
        else:
            kind = "empty" if body.rstrip().endswith(b"/") else "start"

        start_original = _mapped_offset(offset_map, lt)
        end_original = _mapped_offset(offset_map, end)
        if end_original < start_original:
            raise SignatureDrift(
                f"non-monotone source mapping for {tag}@{lt}: "
                f"{start_original}>{end_original}"
            )
        tokens.append(
            MarkupToken(
                kind=kind,
                tag=tag,
                mechanical_start=lt,
                mechanical_end=end,
                start_offset=start_original,
                end_offset=end_original,
            )
        )
        pos = end

    return tuple(tokens)


def _dispositions(path: Path = DISPOSITIONS) -> dict[str, dict]:
    doc = json.loads(path.read_text(encoding="utf8"))
    rows = doc.get("events")
    if not isinstance(rows, list):
        raise SignatureDrift(f"invalid recovery disposition file: {path}")
    out: dict[str, dict] = {}
    for row in rows:
        event_id = row.get("event_id")
        if not isinstance(event_id, str) or event_id in out:
            raise SignatureDrift(f"invalid/duplicate recovery event id: {event_id!r}")
        out[event_id] = row
    return out


def _word_signature(
    prepared: prepared_source.PreparedSource,
    *,
    dispositions_path: Path = DISPOSITIONS,
) -> tuple[int, int]:
    """Return (mechanical_trigger, expected_open_words) or fail closed."""

    reviewed = _dispositions(dispositions_path)
    if len(prepared.recovery_event_ids) != 1:
        raise NotWordResynchronization(
            f"{prepared.path}: expected one reviewed recovery event, got "
            f"{len(prepared.recovery_event_ids)}"
        )

    event_id = prepared.recovery_event_ids[0]
    row = reviewed.get(event_id)
    if row is None or row.get("planned_action") != "resynchronize_word_state":
        raise NotWordResynchronization(
            f"{prepared.path}: {event_id} is not reviewed word-state recovery"
        )
    if row.get("source_sha256") != prepared.source_sha256:
        raise SignatureDrift(f"{prepared.path}: disposition source SHA drift")

    if len(prepared.recovery_patches) != 1:
        raise SignatureDrift(
            f"{prepared.path}: word recovery must own exactly one structural patch"
        )
    patch = prepared.recovery_patches[0]
    if not patch.old or not patch.new.endswith(patch.old):
        raise SignatureDrift(
            f"{prepared.path}: structural patch is not an inserted-prefix rewrite"
        )

    prefix = patch.new[: -len(patch.old)]
    if _ONLY_WORD_CLOSES.fullmatch(prefix) is None:
        raise SignatureDrift(
            f"{prepared.path}: reviewed word recovery inserts non-word structure"
        )
    if not patch.old.startswith(b"</text>"):
        raise SignatureDrift(
            f"{prepared.path}: reviewed word recovery no longer triggers at </text>"
        )

    count = prepared.mechanical_bytes.count(patch.old)
    if count != 1:
        raise SignatureDrift(
            f"{prepared.path}: structural trigger occurs {count} times in mechanical bytes"
        )
    trigger = prepared.mechanical_bytes.find(patch.old)
    if not prepared.mechanical_offset_map.is_exact(trigger):
        raise SignatureDrift(
            f"{prepared.path}: </text> trigger no longer maps exactly to source bytes"
        )

    return trigger, prefix.count(b"</w>")


def _unclosed_words_before(
    tokens: tuple[MarkupToken, ...],
    trigger: int,
    *,
    path: str,
) -> list[MarkupToken]:
    stack: list[MarkupToken] = []
    for token in tokens:
        if token.mechanical_start >= trigger:
            break
        if token.tag != "w":
            continue
        if token.kind == "start":
            stack.append(token)
        elif token.kind == "end":
            if not stack:
                raise SignatureDrift(
                    f"{path}: unmatched literal </w> before reviewed trigger"
                )
            stack.pop()
    return stack


def recover_word_state(
    prepared: prepared_source.PreparedSource,
    *,
    dispositions_path: Path = DISPOSITIONS,
) -> WordRecoveryView:
    """Build a source-coordinate event view for one reviewed word-stack defect.

    Recovery is enabled only by the checked-in reviewed disposition. The historical
    crossing patch is used as a signature, never applied to the byte stream.
    """

    trigger, expected_open_words = _word_signature(
        prepared, dispositions_path=dispositions_path
    )
    offset_map = prepared.mechanical_offset_map
    tokens = scan_markup(prepared.mechanical_bytes, offset_map=offset_map)

    text_end = [
        token
        for token in tokens
        if token.mechanical_start == trigger
        and token.kind == "end"
        and token.tag == "text"
    ]
    if len(text_end) != 1:
        raise SignatureDrift(
            f"{prepared.path}: reviewed trigger is not one literal </text> token"
        )

    open_words = _unclosed_words_before(tokens, trigger, path=prepared.path)
    if len(open_words) != expected_open_words:
        raise SignatureDrift(
            f"{prepared.path}: expected {expected_open_words} unclosed <w> at </text>, "
            f"found {len(open_words)}"
        )

    boundaries = [
        token
        for token in tokens
        if token.mechanical_start < trigger
        and (
            (token.tag == "w" and token.kind == "start")
            or (token.tag == "lb" and token.kind in {"start", "empty"})
        )
    ]
    events: list[RecoveryEvent] = []
    text_trigger_original = text_end[0].start_offset

    for opened in open_words:
        boundary = next(
            (
                token
                for token in boundaries
                if token.mechanical_start >= opened.mechanical_end
            ),
            None,
        )
        if boundary is None:
            kind = "implicit_word_close_before_text_end"
            trigger_original = text_trigger_original
        elif boundary.tag == "w":
            kind = "implicit_word_close_before_word"
            trigger_original = boundary.start_offset
        else:
            kind = "implicit_word_close_before_line"
            trigger_original = boundary.start_offset

        if kind not in _ALLOWED_KINDS:
            raise AssertionError(kind)
        if trigger_original < opened.start_offset:
            raise SignatureDrift(
                f"{prepared.path}: recovery trigger precedes unmatched word"
            )
        events.append(
            RecoveryEvent(
                kind=kind,
                element="w",
                start_offset=opened.start_offset,
                end_offset=trigger_original,
                trigger_offset=trigger_original,
                omitted_bytes=0,
                omitted_semantic_annotation=False,
            )
        )

    return WordRecoveryView(
        path=prepared.path,
        source_sha256=prepared.source_sha256,
        tokens=tokens,
        events=tuple(events),
    )
