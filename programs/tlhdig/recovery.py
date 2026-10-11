"""Signature-scoped structural recovery for reviewed TLHdig word-stack defects.

Phase 2 of #12 deliberately exposes a logical event view rather than a corrected XML
byte stream. The immutable source remains the provenance authority; mechanical XML
repairs are applied by tlhdig.prepared_source, while the recovery decisions below are
represented as events anchored back to immutable-source offsets.
"""
from __future__ import annotations

from array import array
from collections import Counter
from dataclasses import dataclass
from collections.abc import Mapping
from types import MappingProxyType
from hashlib import sha256
import json
from pathlib import Path
import re

from lxml import etree as LE

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
    start_offset/end_offset index immutable source bytes; end_offset may be
    unknown even when a literal opening tag and its start_offset survive.
    Recovery never inserts synthetic tokens into this sequence.
    """

    kind: str
    tag: str
    mechanical_start: int
    mechanical_end: int
    start_offset: int | None
    end_offset: int | None
    synthetic: bool = False


@dataclass(frozen=True, slots=True)
class RecoveryEvent:
    """One logical word-state decision anchored in immutable-source coordinates."""

    kind: str
    element: str
    start_offset: int
    end_offset: int
    trigger_offset: int
    # Unknown until the recovered structure is consumed by TF and checked.
    # The token/event view itself does not establish graph-level zero loss.
    omitted_bytes: int | None
    omitted_semantic_annotation: bool | None


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


def _source_byte_trace(
    original: bytes,
    mechanical: bytes,
    patches: tuple[repair.Patch, ...],
) -> array:
    """Track literal source bytes through byte-local repairs, conservatively.

    OffsetMap intentionally collapses *entire* replacements, including the
    unchanged context used to make a patch unique. For a markup token this can
    turn a surviving <w> into a fictitious zero-length provenance span.

    Retain only an unambiguous common prefix/suffix for each ordered patch;
    changed bytes have sentinel -1. This does not infer an alignment between
    distinct lexical content or create source bytes for inserted text.
    """
    offsets = array("q", range(len(original)))
    current = original
    for patch in patches:
        if not patch.old or current.count(patch.old) != 1:
            raise SignatureDrift("mechanical patch missing or ambiguous during byte trace")
        at = current.find(patch.old)
        old, new = patch.old, patch.new
        overlap = min(len(old), len(new))
        left = 0
        while left < overlap and old[left] == new[left]:
            left += 1
        right = 0
        while right < overlap - left and old[-1 - right] == new[-1 - right]:
            right += 1

        replacement = offsets[at : at + left]
        replacement.extend([-1] * (len(new) - left - right))
        if right:
            replacement.extend(offsets[at + len(old) - right : at + len(old)])
        offsets[at : at + len(old)] = replacement
        current = current[:at] + new + current[at + len(old):]

    if current != mechanical or len(offsets) != len(mechanical):
        raise SignatureDrift("mechanical repair bytes disagree with source trace")
    return offsets


def scan_markup(
    data: bytes,
    *,
    offset_map: repair.OffsetMap | None = None,
    source_bytes: bytes | None = None,
    mechanical_patches: tuple[repair.Patch, ...] = (),
) -> tuple[MarkupToken, ...]:
    """Lex XML element tags without requiring a balanced tree.

    When a mechanically repaired stream is supplied, return conservative
    original-byte spans and flag nonliteral (partly repaired) tokens.
    """
    if source_bytes is not None and offset_map is not None:
        raise ValueError("source_bytes and offset_map are mutually exclusive")
    traced = (
        _source_byte_trace(source_bytes, data, mechanical_patches)
        if source_bytes is not None
        else None
    )
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

        if traced is None:
            start_original = _mapped_offset(offset_map, lt)
            end_original = _mapped_offset(offset_map, end)
            synthetic = False
        else:
            first, last = traced[lt], traced[end - 1]
            # Preserve the *opening* anchor independently of the tag end.
            # Mechanical patches may manufacture '>' while the literal '<w'
            # and element name survived unchanged (KBo 58.79+). Erasing the
            # entire source coordinate pair would claim that original word
            # was missing, despite its byte-exact opening delimiter.
            literal_head = (b"</" if is_end else b"<") + match.group(0)
            after_name = first + len(literal_head)
            valid_start = (
                first >= 0
                and source_bytes[first:after_name] == literal_head
                and after_name < len(source_bytes)
                and source_bytes[after_name] in b" \t\r\n/>"
            )
            if not valid_start:
                # A patched element name or manufactured '<' is not a
                # literal source opening and has no source identity.
                start_original = end_original = None
                synthetic = True
            else:
                start_original = first
                if (
                    last >= first
                    and last < len(source_bytes)
                    and source_bytes[last] == 0x3E
                ):
                    end_original = last + 1
                else:
                    end_original = None
                synthetic = end_original is None or any(
                    traced[pos] != start_original + (pos - lt)
                    for pos in range(lt, end)
                )
        if (
            start_original is not None
            and end_original is not None
            and end_original <= start_original
        ):
            raise SignatureDrift(
                f"non-positive source span for {tag}@{lt}: "
                f"{start_original}>={end_original}"
            )
        tokens.append(
            MarkupToken(
                kind=kind,
                tag=tag,
                mechanical_start=lt,
                mechanical_end=end,
                start_offset=start_original,
                end_offset=end_original,
                synthetic=synthetic,
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




_RAW_OPEN = re.compile(rb"<(w|lb)(?=[\t\r\n />])")



def _trustworthy_raw_tag_end(data: bytes, lt: int) -> int | None:
    """Tag boundary for a *source census*, not an XML repair.

    A quote ending an attribute value must be followed by space, '/' or '>'.
    KUB 34.22+ contains `c="... c="22"`: a purely quote-aware lexer
    mistakes the second quote for an opening quote and then swallows the
    following literal words as attribute data. Return None at that malformed
    construct so the census resumes at subsequent '<' characters.

    Retain the normal quoted-attribute skip when it is syntactically bounded:
    quoted '<w>' strings in non-element markup cannot create real source words.
    """
    quote = 0
    for i in range(lt + 1, len(data)):
        c = data[i]
        if quote:
            if c == quote:
                quote = 0
                if i + 1 < len(data) and data[i + 1] not in b" \t\r\n/>":
                    return None
        elif c in (0x22, 0x27):
            quote = c
        elif c == 0x3C:
            return None
        elif c == 0x3E:
            return i + 1
    return None


def _raw_opening_starts(original: bytes) -> tuple[set[int], set[int]]:
    """Find source <w>/<lb> anchors even when surrounding XML is malformed.

    The reviewed upstream includes an unterminated quoted attribute in KBo
    12.55: a normal tag lexer cannot reach later literal line and word starts.
    This scanner skips complete markup, comments, PIs and CDATA when possible;
    on a broken element it resumes at the next literal '<'. These are source
    *candidate* offsets, not evidence that the whole source parses as XML.
    Ambiguous candidates are intentionally retained and must be reconciled.
    """
    words: set[int] = set()
    lines: set[int] = set()
    pos = 0
    while True:
        lt = original.find(b"<", pos)
        if lt < 0:
            break
        skipped = _skip_non_element(original, lt)
        if skipped is not None:
            pos = skipped
            continue

        candidate = _RAW_OPEN.match(original, lt)
        if candidate is not None:
            (words if candidate.group(1) == b"w" else lines).add(lt)

        # Source is immutable; an invalid quote boundary is a lexical
        # resynchronization point, never permission to fabricate a tag.
        end = _trustworthy_raw_tag_end(original, lt)
        pos = lt + 1 if end is None else end
    return words, lines


@dataclass(frozen=True, slots=True)
class OpeningTagAudit:
    """Pre-graph source conservation over literal word and line opening tags.

    These are lexical source anchors, not proof of eventual TF node/slot
    conservation.  In particular, a mechanically manufactured tag does not
    satisfy the corresponding immutable-source identity.
    """

    source_line_starts: int
    retained_line_starts: int
    source_word_starts: int
    retained_word_starts: int
    missing_line_starts: tuple[int, ...]
    missing_word_starts: tuple[int, ...]
    unexpected_line_starts: tuple[int, ...]
    unexpected_word_starts: tuple[int, ...]
    duplicate_line_starts: tuple[int, ...]
    duplicate_word_starts: tuple[int, ...]
    out_of_order_starts: tuple[tuple[int, int], ...]
    unanchored_line_starts: tuple[int, ...]
    unanchored_word_starts: tuple[int, ...]


def audit_opening_tags(original: bytes, view: WordRecoveryView) -> OpeningTagAudit:
    """Audit source opening-tag identities before structural TF construction.

    Compare immutable-source lexical <lb>/<w> offsets to the provenance
    coordinates of the tokens that the recovery view will offer its consumer.
    Attribute-only lexical repairs are allowed: they can change a tag's bytes
    while retaining its real opening delimiter and original name.

    This is deliberately independent of RecoveryEvent.omitted_bytes, which
    cannot establish graph conservation before conversion.
    """
    if sha256(original).hexdigest() != view.source_sha256:
        raise SignatureDrift(f"{view.path}: recovery audit source SHA mismatch")
    source_words, source_lines = _raw_opening_starts(original)

    def starts(tokens: tuple[MarkupToken, ...], tag: str) -> set[int]:
        return {
            t.start_offset
            for t in tokens
            if t.tag == tag and t.kind in {"start", "empty"}
            and t.start_offset is not None
        }

    def unanchored(tag: str) -> tuple[int, ...]:
        return tuple(sorted(
            t.mechanical_start for t in view.tokens
            if t.tag == tag and t.kind in {"start", "empty"}
            and t.start_offset is None
        ))

    view_lines, view_words = starts(view.tokens, "lb"), starts(view.tokens, "w")

    def duplicate_starts(tag: str) -> tuple[int, ...]:
        counted = Counter(
            t.start_offset for t in view.tokens
            if t.tag == tag and t.kind in {"start", "empty"}
            and t.start_offset is not None
        )
        return tuple(sorted(offset for offset, count in counted.items() if count > 1))

    # A set comparison alone misses reordered or duplicated source tokens.
    # The scanner's literal word and line openings must retain byte order.
    anchored_sequence = [
        t.start_offset for t in view.tokens
        if t.tag in {"w", "lb"} and t.kind in {"start", "empty"}
        and t.start_offset is not None
    ]
    reversed_pairs = tuple(
        (earlier, later)
        for earlier, later in zip(anchored_sequence, anchored_sequence[1:])
        if later < earlier
    )
    return OpeningTagAudit(
        source_line_starts=len(source_lines),
        retained_line_starts=len(source_lines & view_lines),
        source_word_starts=len(source_words),
        retained_word_starts=len(source_words & view_words),
        missing_line_starts=tuple(sorted(source_lines - view_lines)),
        missing_word_starts=tuple(sorted(source_words - view_words)),
        unexpected_line_starts=tuple(sorted(view_lines - source_lines)),
        unexpected_word_starts=tuple(sorted(view_words - source_words)),
        duplicate_line_starts=duplicate_starts("lb"),
        duplicate_word_starts=duplicate_starts("w"),
        out_of_order_starts=reversed_pairs,
        unanchored_line_starts=unanchored("lb"),
        unanchored_word_starts=unanchored("w"),
    )

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
    tokens = scan_markup(
        prepared.mechanical_bytes,
        source_bytes=prepared.original_bytes,
        mechanical_patches=prepared.mechanical_patches,
    )

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
    if text_trigger_original is None:
        raise SignatureDrift(f"{prepared.path}: text-end trigger is synthetic")

    for opened in open_words:
        if opened.start_offset is None:
            raise SignatureDrift(
                f"{prepared.path}: unclosed word has no immutable-source tag start "
                f"at mechanical offset {opened.mechanical_start}"
            )
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
        if trigger_original is None:
            raise SignatureDrift(
                f"{prepared.path}: word synchronization boundary is synthetic"
            )
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
                omitted_bytes=None,
                omitted_semantic_annotation=None,
            )
        )

    return WordRecoveryView(
        path=prepared.path,
        source_sha256=prepared.source_sha256,
        tokens=tokens,
        events=tuple(events),
    )



# Source-SHA-reviewed layout suffix on a terminal sign-bearing word.
# KUB 48.15's last "x-" precedes an orphan laes opening and two gap tags.
# Preserve these in the final sign 'after' ONLY when the original, reviewed
# byte stream contains this exact ordered tag sequence.
REVIEWED_TERMINAL_TAIL_TAGS: dict[str, tuple[str, ...]] = {
    "CTH 820_XML_TLH/KUB 48.15.xml": ("laes_in", "gap", "gap"),
}

@dataclass(frozen=True, slots=True)
class RecoveredGap:
    """One literal self-closing source <gap/> annotation inside a recovered word.

    Coordinates are half-open byte offsets RELATIVE to the original word body.
    Its underlying markup remains verbatim in sign provenance; this typed view
    makes the separate editorial assertion queryable without inventing a slot.
    Values are XML-decoded literal attribute values, never inferred text.
    """

    relative_start: int
    relative_end: int
    c: str | None
    t: str | None


@dataclass(frozen=True, slots=True)
class TerminalWordPayload:
    """Source-grounded one-word payload, not a fabricated XML Span or TF node.

    There is no literal closing </w> in the source: content_end_offset is the
    original </text> trigger and end_is_implicit explicitly says so.
    Attributes come from the reviewed mechanical lexical opener; content must
    be byte-identical to the immutable source on this narrow first path.
    """

    path: str
    source_sha256: str
    opening_offset: int
    content_start_offset: int
    content_end_offset: int
    content_bytes: bytes
    attributes: Mapping[str, str]
    end_is_implicit: bool
    attribute_source: str


def terminal_word_payload(
    prepared: prepared_source.PreparedSource,
) -> TerminalWordPayload:
    """Extract ONLY one unambiguously terminal word from a reviewed source.

    This intentionally does not infer the boundary of a nested or next-line
    word, even if the historical patched XML could be made to parse. It is a
    controlled bridge toward _State.word/sign/morph, not graph integration.
    """
    if sha256(prepared.original_bytes).hexdigest() != prepared.source_sha256:
        raise SignatureDrift(f"{prepared.path}: terminal payload source SHA drift")

    view = recover_word_state(prepared)
    if (
        len(view.events) != 1
        or view.events[0].kind != "implicit_word_close_before_text_end"
    ):
        raise SignatureDrift(
            f"{prepared.path}: not a single terminal recovered word"
        )
    event = view.events[0]
    starts = [
        t for t in view.tokens
        if t.tag == "w" and t.kind == "start"
        and t.start_offset == event.start_offset
    ]
    endings = [
        t for t in view.tokens
        if t.tag == "text" and t.kind == "end"
        and t.start_offset == event.trigger_offset
    ]
    if len(starts) != 1 or len(endings) != 1:
        raise SignatureDrift(
            f"{prepared.path}: terminal source opening/trigger is not unique"
        )
    opened, text_end = starts[0], endings[0]
    if (
        opened.end_offset is None
        or text_end.start_offset is None
        or opened.end_offset > text_end.start_offset
        or opened.mechanical_end > text_end.mechanical_start
    ):
        raise SignatureDrift(
            f"{prepared.path}: terminal word content is not source-anchored"
        )

    # A subsequent <w>, a line transition, or an explicit </w> changes this
    # case from a terminal singleton into an ambiguous recovery problem.
    between = [
        t for t in view.tokens
        if opened.mechanical_end <= t.mechanical_start < text_end.mechanical_start
    ]
    if any(
        (t.tag == "lb" and t.kind in {"start", "empty"})
        or (t.tag == "w" and t.kind in {"start", "empty", "end"})
        for t in between
    ):
        raise SignatureDrift(
            f"{prepared.path}: not a single terminal recovered word"
        )

    raw_content = prepared.original_bytes[
        opened.end_offset:text_end.start_offset
    ]
    mechanical_content = prepared.mechanical_bytes[
        opened.mechanical_end:text_end.mechanical_start
    ]
    if raw_content != mechanical_content:
        # Future mixed-source payloads require per-byte trace and separate
        # source/sign witnesses. Never silently expose repaired bytes as source.
        raise SignatureDrift(
            f"{prepared.path}: terminal source content differs after lexical repairs"
        )

    open_tag = prepared.mechanical_bytes[
        opened.mechanical_start:opened.mechanical_end
    ]
    if not open_tag.startswith(b"<w") or not open_tag.endswith(b">"):
        raise SignatureDrift(
            f"{prepared.path}: terminal mechanical word opener is malformed"
        )
    try:
        # Parse only the pinned, standalone *opening tag* for its attributes;
        # no strict full-source parser and no corrected source document.
        parser = LE.XMLParser(recover=False, no_network=True, resolve_entities=False)
        elem = LE.fromstring(open_tag[:-1] + b"/>", parser)
    except LE.XMLSyntaxError as exc:
        raise SignatureDrift(
            f"{prepared.path}: terminal word opener cannot be parsed"
        ) from exc
    if elem.tag != "w":
        raise SignatureDrift(
            f"{prepared.path}: terminal opener parsed as unexpected element"
        )

    return TerminalWordPayload(
        path=prepared.path,
        source_sha256=prepared.source_sha256,
        opening_offset=opened.start_offset,
        content_start_offset=opened.end_offset,
        content_end_offset=text_end.start_offset,
        content_bytes=raw_content,
        attributes=MappingProxyType(dict(elem.attrib)),
        end_is_implicit=True,
        attribute_source="mechanical",
    )


def word_before_line_payload(
    prepared: prepared_source.PreparedSource,
) -> TerminalWordPayload:
    """Recover a word ending immediately before a literal next-line opener.

    Narrow but reusable safe shape: precisely one reviewed unresolved word,
    whose first following structural token is an original <lb>, and exactly
    one independently source-closed following word before </text>. The
    historical end-of-text synthetic close is *never* treated as the source
    boundary. Other structural shapes remain unimplemented, not guessed.
    """
    if sha256(prepared.original_bytes).hexdigest() != prepared.source_sha256:
        raise SignatureDrift(f"{prepared.path}: before-line payload source SHA drift")
    view = recover_word_state(prepared)
    if (
        len(view.events) != 1
        or view.events[0].kind != "implicit_word_close_before_line"
    ):
        raise SignatureDrift(f"{prepared.path}: not a single before-line word")

    event = view.events[0]
    starts = [
        t for t in view.tokens
        if t.tag == "w" and t.kind == "start"
        and t.start_offset == event.start_offset
    ]
    boundaries = [
        t for t in view.tokens
        if t.tag == "lb" and t.kind == "empty"
        and t.start_offset == event.trigger_offset
    ]
    if len(starts) != 1 or len(boundaries) != 1:
        raise SignatureDrift(
            f"{prepared.path}: before-line word or literal lb is not unique"
        )
    opened, boundary = starts[0], boundaries[0]
    if (
        opened.end_offset is None
        or boundary.start_offset is None
        or opened.mechanical_end > boundary.mechanical_start
        or opened.end_offset > boundary.start_offset
        or event.end_offset != boundary.start_offset
        or prepared.original_bytes[boundary.start_offset:boundary.start_offset + 3]
        != b"<lb"
    ):
        raise SignatureDrift(f"{prepared.path}: before-line boundary has no literal source anchor")

    between = [
        t for t in view.tokens
        if opened.mechanical_end <= t.mechanical_start < boundary.mechanical_start
    ]
    if any(t.tag in {"w", "lb"} for t in between):
        raise SignatureDrift(
            f"{prepared.path}: ambiguous additional word/line before recovered boundary"
        )

    after = [
        t for t in view.tokens
        if t.mechanical_start >= boundary.mechanical_end
        and t.tag in {"w", "lb"}
    ]
    following_words = [t for t in after if t.tag == "w" and t.kind == "start"]
    closing_words = [t for t in after if t.tag == "w" and t.kind == "end"]
    following_lines = [t for t in after if t.tag == "lb"]
    if (
        len(following_words) != 1 or len(closing_words) != 1
        or following_lines
        or following_words[0].mechanical_start >= closing_words[0].mechanical_start
        or following_words[0].start_offset is None
        or following_words[0].end_offset is None
        or closing_words[0].start_offset is None
    ):
        raise SignatureDrift(
            f"{prepared.path}: before-line pilot lacks one independently closed next word"
        )

    raw_content = prepared.original_bytes[
        opened.end_offset:boundary.start_offset
    ]
    mechanical_content = prepared.mechanical_bytes[
        opened.mechanical_end:boundary.mechanical_start
    ]
    if raw_content != mechanical_content:
        raise SignatureDrift(
            f"{prepared.path}: before-line word body differs after lexical repairs"
        )

    open_tag = prepared.mechanical_bytes[
        opened.mechanical_start:opened.mechanical_end
    ]
    if not open_tag.startswith(b"<w") or not open_tag.endswith(b">"):
        raise SignatureDrift(
            f"{prepared.path}: reviewed before-line mechanical opener malformed"
        )
    try:
        elem = LE.fromstring(
            open_tag[:-1] + b"/>",
            parser=LE.XMLParser(recover=False, resolve_entities=False, no_network=True),
        )
    except LE.XMLSyntaxError as exc:
        raise SignatureDrift(
            f"{prepared.path}: before-line word attributes cannot be parsed"
        ) from exc
    if elem.tag != "w":
        raise SignatureDrift(f"{prepared.path}: before-line opener is not a word")
    return TerminalWordPayload(
        path=prepared.path,
        source_sha256=prepared.source_sha256,
        opening_offset=opened.start_offset,
        content_start_offset=opened.end_offset,
        content_end_offset=boundary.start_offset,
        content_bytes=raw_content,
        attributes=MappingProxyType(dict(elem.attrib)),
        end_is_implicit=True,
        attribute_source="mechanical",
    )


def reviewed_word_payload(
    prepared: prepared_source.PreparedSource,
) -> TerminalWordPayload:
    """Re-derive the source-authoritative word payload before graph writes."""
    view = recover_word_state(prepared)
    if len(view.events) != 1:
        raise SignatureDrift(f"{prepared.path}: expected one reviewed word event")
    kind = view.events[0].kind
    if kind == "implicit_word_close_before_text_end":
        return terminal_word_payload(prepared)
    if kind == "implicit_word_close_before_line":
        return word_before_line_payload(prepared)
    raise SignatureDrift(
        f"{prepared.path}: unimplemented reviewed word event kind {kind}"
    )


def literal_gap_annotations(content: bytes) -> tuple[RecoveredGap, ...]:
    """Extract typed literal gaps from ANY source-verified recovered word body.

    This scans only the immutable body, with quote-aware token coordinates.
    No historical tree or previous tokenisation is treated as the semantic
    authority. Such annotations never invent signs, lines, or word extents.
    """
    result = []
    for t in scan_markup(content):
        if t.tag != "gap":
            continue
        if (
            t.kind != "empty" or t.start_offset is None or t.end_offset is None
            or not (0 <= t.start_offset < t.end_offset <= len(content))
        ):
            raise SignatureDrift("recovered word has nonliteral or nonempty gap")
        raw_tag = content[t.start_offset:t.end_offset]
        if not raw_tag.startswith(b"<gap") or not raw_tag.endswith(b"/>"):
            raise SignatureDrift("recovered word has invalid gap delimiters")
        try:
            elem = LE.fromstring(
                raw_tag,
                parser=LE.XMLParser(
                    recover=False, resolve_entities=False, no_network=True
                ),
            )
        except LE.XMLSyntaxError as exc:
            raise SignatureDrift("recovered word has invalid original gap") from exc
        if elem.tag != "gap" or set(elem.attrib) - {"c", "t"}:
            raise SignatureDrift("recovered word has unsupported literal gap attributes")
        result.append(RecoveredGap(
            relative_start=t.start_offset, relative_end=t.end_offset,
            c=elem.get("c"), t=elem.get("t"),
        ))
    return tuple(result)


@dataclass(frozen=True, slots=True)
class SourceLineGap:
    """A literal gap after a closed word, owned by the real source line.

    start/end and line_open are absolute offsets in the immutable AOxml
    source. The annotation has no word parent and never introduces a line or
    sign slot; TF anchors the point to that line's last real sign.
    """

    start_offset: int
    end_offset: int
    line_open: int
    c: str | None
    t: str | None


def literal_outside_word_line_gaps(
    prepared: prepared_source.PreparedSource,
) -> tuple[SourceLineGap, ...]:
    """Project a reviewed outside-word gap from the *logical source* stream.

    Fail closed on anything other than the first independently reviewed
    before-line word resynchronization, with one literal next-line word
    subsequently closed in the original. The historical lxml tree makes the
    gap a child of the unclosed previous word; its ancestry is NOT a valid
    semantic witness. No arbitrary 'lb => close w' inference is performed.
    """
    if sha256(prepared.original_bytes).hexdigest() != prepared.source_sha256:
        raise SignatureDrift(
            f"{prepared.path}: line-scoped gap source SHA drift"
        )
    # This validates the reviewed patch signature, the literal fifth-line
    # boundary, the source/mechanical word body and its independently closed
    # successor. Do not add paths to a source-specific exception registry.
    payload = word_before_line_payload(prepared)
    view = recover_word_state(prepared)
    event = view.events[0]
    stack: list[MarkupToken] = []
    in_text = False
    text_end = None
    line: MarkupToken | None = None
    last_literal_word_close: int | None = None
    applied_implicit = False
    gaps: list[SourceLineGap] = []

    for tok in view.tokens:
        if tok.tag == "text" and tok.kind == "start":
            if in_text:
                raise SignatureDrift("line-scoped gap: nested text element")
            in_text = True
            continue
        if tok.tag == "text" and tok.kind == "end" and in_text:
            text_end = tok.start_offset
            if stack:
                raise SignatureDrift(
                    "line-scoped gap: unresolved source word after reviewed close"
                )
            break
        if not in_text:
            continue

        if tok.start_offset == event.trigger_offset:
            if (
                tok.tag != "lb" or tok.kind != "empty"
                or tok.start_offset != event.end_offset
                or len(stack) != 1
                or stack[0].start_offset != payload.opening_offset
            ):
                raise SignatureDrift(
                    "line-scoped gap: reviewed close cannot be applied to one real lb"
                )
            stack.pop()
            applied_implicit = True

        if tok.tag == "lb":
            if tok.kind != "empty" or tok.start_offset is None:
                raise SignatureDrift("line-scoped gap: unanchored literal line")
            line = tok
            continue
        if tok.tag == "w":
            if tok.kind == "start":
                stack.append(tok)
            elif tok.kind == "end":
                if not stack or tok.end_offset is None:
                    raise SignatureDrift("line-scoped gap: unmatched or synthetic word close")
                stack.pop()
                if applied_implicit:
                    last_literal_word_close = tok.end_offset
            else:
                raise SignatureDrift("line-scoped gap: unsupported empty word")
            continue
        if tok.tag == "gap" and not stack:
            if (
                not applied_implicit or line is None
                or line.start_offset != event.trigger_offset
                or tok.kind != "empty"
                or tok.start_offset is None or tok.end_offset is None
                or last_literal_word_close is None
                or tok.start_offset <= last_literal_word_close
                or prepared.original_bytes[
                    last_literal_word_close:tok.start_offset
                ].strip()
            ):
                raise SignatureDrift(
                    "line-scoped gap: original annotation is not after a closed word"
                )
            raw = prepared.original_bytes[tok.start_offset:tok.end_offset]
            literal = literal_gap_annotations(raw)
            if (
                len(literal) != 1 or literal[0].relative_start != 0
                or literal[0].relative_end != len(raw)
            ):
                raise SignatureDrift("line-scoped gap: annotation is not literal")
            gaps.append(SourceLineGap(
                start_offset=tok.start_offset,
                end_offset=tok.end_offset,
                line_open=line.start_offset,
                c=literal[0].c,
                t=literal[0].t,
            ))

    if (
        not applied_implicit or text_end is None or len(gaps) != 1
        or gaps[0].t != "line"
        or gaps[0].line_open != event.trigger_offset
        or prepared.original_bytes[gaps[0].end_offset:text_end].strip()
    ):
        raise SignatureDrift(
            f"{prepared.path}: line-scoped gap is not one reviewed trailing "
            "original annotation on the new source line"
        )
    return tuple(gaps)


def original_opening_sequences(
    prepared: prepared_source.PreparedSource,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Return immutable word/line opening identities within this source text.

    The returned offsets name real *opening delimiters*, not reparsed parent
    spans. Mechanical lexical attribute edits may alter a tag body, never
    manufacture a source opening. No unrelated document may opt into this
    contract without its own reviewed recovery signature.
    """
    if sha256(prepared.original_bytes).hexdigest() != prepared.source_sha256:
        raise SignatureDrift(
            f"{prepared.path}: original opening source SHA drift"
        )
    view = recover_word_state(prepared)
    starts = [
        t for t in view.tokens
        if t.tag == "text" and t.kind == "start"
    ]
    ends = [
        t for t in view.tokens
        if t.tag == "text" and t.kind == "end"
    ]
    if len(starts) != 1 or len(ends) != 1:
        raise SignatureDrift(
            f"{prepared.path}: original lexical text boundary is ambiguous"
        )
    begin, stop = starts[0].mechanical_end, ends[0].mechanical_start
    if begin >= stop:
        raise SignatureDrift(
            f"{prepared.path}: invalid original lexical text coordinates"
        )

    def original_tokens(tag: str) -> tuple[int, ...]:
        opens = [
            t for t in view.tokens
            if t.tag == tag and t.kind in {"start", "empty"}
            and begin <= t.mechanical_start < stop
        ]
        if not opens or any(t.start_offset is None for t in opens):
            raise SignatureDrift(
                f"{prepared.path}: unanchored or missing source {tag} opening"
            )
        offsets = tuple(t.start_offset for t in opens)
        head = b"<" + tag.encode("ascii")
        if any(
            prepared.original_bytes[pos:pos + len(head)] != head
            for pos in offsets
        ):
            raise SignatureDrift(
                f"{prepared.path}: nonliteral original source {tag} opening"
            )
        # The four reviewed pilots contain no alternate lexical <w>/<lb>
        # wrappers outside <text>. Also guard against source-lexer loss or
        # token substitutions: this independent raw opening census must
        # exactly match the token-to-original coordinate mapping.
        raw = tuple(
            m.start() for m in re.finditer(
                rb"<" + tag.encode("ascii") + rb"(?=[ \t\r\n/>])",
                prepared.original_bytes,
            )
        )
        if offsets != raw or len(set(offsets)) != len(offsets):
            raise SignatureDrift(
                f"{prepared.path}: source {tag} token/opening sequence drift"
            )
        return offsets

    return original_tokens("w"), original_tokens("lb")


def verify_emitted_openings(
    prepared: prepared_source.PreparedSource,
    emitted_word_starts: tuple[int, ...],
    emitted_line_starts: tuple[int, ...],
) -> None:
    """Fail closed if emitted TF source-opening identities diverge from AOxml.

    A word emitted as a source-word layout still counts. The ordering is
    recorded by the actual TF state transitions; comparing totals or sets
    alone would accept dropped, forged, substituted or reordered nodes.
    """
    original_words, original_lines = original_opening_sequences(prepared)

    def verify(label: str, actual: tuple[int, ...], expected: tuple[int, ...]):
        if len(set(actual)) != len(actual):
            raise SignatureDrift(
                f"{prepared.path}: duplicate emitted source {label} opening"
            )
        if len(actual) < len(expected):
            raise SignatureDrift(
                f"{prepared.path}: missing emitted source {label} opening"
            )
        if len(actual) > len(expected):
            raise SignatureDrift(
                f"{prepared.path}: unexpected source {label} opening count"
            )
        if set(actual) != set(expected):
            raise SignatureDrift(
                f"{prepared.path}: source {label} opening identity mismatch"
            )
        if actual != expected:
            raise SignatureDrift(
                f"{prepared.path}: emitted {label} opening source order drift"
            )

    verify("word", tuple(emitted_word_starts), original_words)
    verify("line", tuple(emitted_line_starts), original_lines)


@dataclass(frozen=True, slots=True)
class LexicalWordWitness:
    """One authenticated, source-token lexical word, independent of lxml.

    body_bytes are mechanical-only bytes, never the full historically patched
    XML word extent. One reviewed implicit closing boundary is represented by
    end_is_implicit and deliberately has no original source close offset.
    """

    path: str
    source_sha256: str
    opening_offset: int
    mechanical_open_start: int
    mechanical_open_end: int
    body_bytes: bytes
    attributes: Mapping[str, str]
    end_is_implicit: bool
    original_close_offset: int | None


def lexical_word_witnesses(
    prepared: prepared_source.PreparedSource,
) -> tuple[LexicalWordWitness, ...]:
    """Derive EVERY lexical word from signed AOxml tokens and one reviewed event.

    An XML serializer (or the historical inserted </w>) is *not* the
    authority for a source word's attributes or body. This one-to-one
    vertical slice deliberately rejects genuine nested words and additional
    implicit ends until their ownership is separately reviewed.
    """
    expected_words, _ = original_opening_sequences(prepared)
    view = recover_word_state(prepared)
    if len(view.events) != 1:
        raise SignatureDrift(
            f"{prepared.path}: lexical parity requires one reviewed recovery event"
        )
    event = view.events[0]
    payload = reviewed_word_payload(prepared)
    if event.start_offset != payload.opening_offset:
        raise SignatureDrift(
            f"{prepared.path}: lexical event and recovered payload diverge"
        )

    mechanical = prepared.mechanical_bytes
    word_open: MarkupToken | None = None
    opened_attrs: Mapping[str, str] | None = None
    witnessed: list[LexicalWordWitness] = []
    active_text = False
    applied_implicit = False

    def close_word(stop: int, close_offset: int | None, *, implicit: bool):
        nonlocal word_open, opened_attrs, applied_implicit
        if word_open is None or opened_attrs is None:
            raise SignatureDrift(
                f"{prepared.path}: unmatched lexical word close"
            )
        if not (word_open.mechanical_end <= stop <= len(mechanical)):
            raise SignatureDrift(
                f"{prepared.path}: invalid mechanical lexical word body bounds"
            )
        content = mechanical[word_open.mechanical_end:stop]
        if implicit:
            if (
                applied_implicit
                or word_open.start_offset != event.start_offset
                or content != payload.content_bytes
                or dict(opened_attrs) != dict(payload.attributes)
            ):
                raise SignatureDrift(
                    f"{prepared.path}: implicit word body/attributes differ from source"
                )
            applied_implicit = True
        elif close_offset is None:
            raise SignatureDrift(
                f"{prepared.path}: explicit lexical closing tag has no source offset"
            )
        witnessed.append(LexicalWordWitness(
            path=prepared.path,
            source_sha256=prepared.source_sha256,
            opening_offset=word_open.start_offset,
            mechanical_open_start=word_open.mechanical_start,
            mechanical_open_end=word_open.mechanical_end,
            body_bytes=content,
            attributes=MappingProxyType(dict(opened_attrs)),
            end_is_implicit=implicit,
            original_close_offset=close_offset,
        ))
        word_open = None
        opened_attrs = None

    for tok in view.tokens:
        if tok.tag == "text" and tok.kind == "start":
            if active_text:
                raise SignatureDrift(
                    f"{prepared.path}: ambiguous nested source text"
                )
            active_text = True
            continue
        if tok.tag == "text" and tok.kind == "end":
            if not active_text:
                continue
            if (
                event.kind == "implicit_word_close_before_text_end"
                and tok.start_offset == event.trigger_offset
            ):
                close_word(tok.mechanical_start, None, implicit=True)
            if word_open is not None:
                raise SignatureDrift(
                    f"{prepared.path}: unreviewed word open at source text end"
                )
            active_text = False
            break
        if not active_text:
            continue

        if (
            event.kind == "implicit_word_close_before_line"
            and tok.tag == "lb"
            and tok.start_offset == event.trigger_offset
        ):
            if tok.kind != "empty":
                raise SignatureDrift(
                    f"{prepared.path}: implicit source line boundary not literal lb"
                )
            close_word(tok.mechanical_start, None, implicit=True)

        if tok.tag != "w":
            continue
        if tok.kind == "start":
            if word_open is not None:
                raise SignatureDrift(
                    f"{prepared.path}: nested lexical word outside reviewed pilot"
                )
            if tok.start_offset is None or tok.end_offset is None:
                raise SignatureDrift(
                    f"{prepared.path}: lexical word opener has no original byte anchor"
                )
            open_tag = mechanical[tok.mechanical_start:tok.mechanical_end]
            if not (open_tag.startswith(b"<w") and open_tag.endswith(b">")):
                raise SignatureDrift(
                    f"{prepared.path}: malformed mechanical lexical opener"
                )
            try:
                parsed = LE.fromstring(
                    open_tag[:-1] + b"/>",
                    parser=LE.XMLParser(
                        recover=False, resolve_entities=False, no_network=True
                    ),
                )
            except LE.XMLSyntaxError as exc:
                raise SignatureDrift(
                    f"{prepared.path}: cannot parse mechanically reviewed word attributes"
                ) from exc
            if parsed.tag != "w":
                raise SignatureDrift(
                    f"{prepared.path}: source word opener parsed as another tag"
                )
            word_open = tok
            opened_attrs = MappingProxyType(dict(parsed.attrib))
        elif tok.kind == "end":
            close_word(tok.mechanical_start, tok.start_offset, implicit=False)
        else:
            raise SignatureDrift(
                f"{prepared.path}: unsupported self-closing lexical word"
            )

    if (
        active_text or word_open is not None
        or not applied_implicit
        or tuple(w.opening_offset for w in witnessed) != expected_words
        or len({w.opening_offset for w in witnessed}) != len(witnessed)
    ):
        raise SignatureDrift(
            f"{prepared.path}: lexical word source opening or closing sequence drift"
        )
    return tuple(witnessed)


def verify_lexical_pairing(
    prepared: prepared_source.PreparedSource,
    opening_offset: int,
    emitted_attributes: Mapping[str, str],
    emitted_body: bytes,
    *,
    witness: LexicalWordWitness | None = None,
) -> None:
    """Compare exactly one emitted word's input to its signed lexical witness.

    The converter supplies a witness from one authenticated source pass; a
    direct caller without that witness receives the same source-derived
    validation with a fresh pass. Compare *all* attributes, including mrpN,
    rather than only transcription or one morphology selector.
    """
    if sha256(prepared.original_bytes).hexdigest() != prepared.source_sha256:
        raise SignatureDrift(
            f"{prepared.path}: lexical pairing source SHA drift"
        )
    if witness is None:
        matches = [
            w for w in lexical_word_witnesses(prepared)
            if w.opening_offset == opening_offset
        ]
        if len(matches) != 1:
            raise SignatureDrift(
                f"{prepared.path}: lexical source opening not uniquely reviewed"
            )
        witness = matches[0]
    if (
        witness.path != prepared.path
        or witness.source_sha256 != prepared.source_sha256
        or witness.opening_offset != opening_offset
        or prepared.original_bytes[opening_offset:opening_offset + 2] != b"<w"
        or prepared.mechanical_bytes[
            witness.mechanical_open_start:witness.mechanical_open_end
        ].startswith(b"<w") is False
    ):
        raise SignatureDrift(
            f"{prepared.path}: lexical pairing source opening identity mismatch"
        )
    if dict(emitted_attributes) != dict(witness.attributes):
        raise SignatureDrift(
            f"{prepared.path}: lexical attribute/trans/mrp pairing mismatch "
            f"at original byte {opening_offset}"
        )
    if emitted_body != witness.body_bytes:
        raise SignatureDrift(
            f"{prepared.path}: lexical body/source pairing mismatch "
            f"at original byte {opening_offset}"
        )
