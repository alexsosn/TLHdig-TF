"""Phase-2 RED contract for reviewed word-state recovery (#12).

The recovery layer is intentionally specified as an event view over immutable source
coordinates.  It must not manufacture a corrected XML byte stream.
"""
from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256

import pytest

from tlhdig import prepared_source, repair
from tlhdig.paths import PROGRAMS, REPORTS

try:
    from tlhdig import recovery
except ImportError:  # RED until Phase 2 exists.
    recovery = None


KBO4149 = "CTH 479_XML_BESRIT/KBo 41.49+.xml"
BO3353 = "CTH 394_XML_BESRIT/Bo 3353.xml"
KBO1255 = "CTH 209_XML_TLH/KBo 12.55.xml"
WRAPPER_ONLY = "CTH 144_XML_SVH/KUB 26.29+.xml"


def _api():
    assert recovery is not None, "Phase-2 tlhdig.recovery API is not implemented"
    return recovery


def _effect(rel: str) -> dict:
    report = json.loads(
        (REPORTS / "source-recovery-inventory.json").read_text(encoding="utf8")
    )
    return report["file_effects"][rel]


def _start_tokens(view, tag: str):
    return [
        token
        for token in view.tokens
        if token.tag == tag and token.kind in {"start", "empty"}
    ]


def _assert_original_offsets(view, raw: bytes) -> None:
    for token in view.tokens:
        if token.start_offset is None or token.end_offset is None:
            assert token.synthetic
            assert token.start_offset is None and token.end_offset is None
            continue
        assert 0 <= token.start_offset < token.end_offset <= len(raw)
        assert raw[token.start_offset : token.start_offset + 1] == b"<"
    for event in view.events:
        assert 0 <= event.start_offset <= event.end_offset <= len(raw)
        assert 0 <= event.trigger_offset < len(raw)
        assert raw[event.trigger_offset : event.trigger_offset + 1] == b"<"


def test_markup_scanner_does_not_treat_well_formed_nested_word_as_a_defect() -> None:
    api = _api()
    raw = b"<text><lb/><w>a<w>b</w>c</w><w>d</w></text>"

    tokens = api.scan_markup(raw)

    assert [(t.kind, t.tag) for t in tokens] == [
        ("start", "text"),
        ("empty", "lb"),
        ("start", "w"),
        ("start", "w"),
        ("end", "w"),
        ("end", "w"),
        ("start", "w"),
        ("end", "w"),
        ("end", "text"),
    ]
    assert all(not getattr(token, "synthetic", False) for token in tokens)


def test_catastrophic_line_swallowing_resynchronizes_before_line_without_loss() -> None:
    api = _api()
    prepared = prepared_source.prepare(KBO4149)
    view = api.recover_word_state(prepared)
    raw = prepared.original_bytes
    effect = _effect(KBO4149)
    measured = effect["words"][0]

    assert view.path == KBO4149
    assert view.source_sha256 == prepared.source_sha256
    assert any(e.kind == "implicit_word_close_before_line" for e in view.events)
    assert all(e.omitted_bytes is None for e in view.events)

    # This source has 14 unclosed words at the text boundary.  For the first malformed
    # word, the first independent structural boundary is a new line, and the old
    # repaired-tree span swallowed dozens of later line starts.  The tolerant event
    # view must expose every measured line tag instead of making them descendants of
    # a single giant logical word.
    lb_in_measured_region = [
        t
        for t in _start_tokens(view, "lb")
        if measured["outer_start"] < t.mechanical_start < measured["outer_end"]
    ]
    assert len(lb_in_measured_region) == measured["lb_open_count"]
    _assert_original_offsets(view, raw)


def test_nested_word_swallowing_without_line_boundary_resynchronizes_before_word() -> None:
    api = _api()
    prepared = prepared_source.prepare(BO3353)
    view = api.recover_word_state(prepared)
    effect = _effect(BO3353)
    measured = effect["words"][0]

    assert measured["lb_open_count"] == 0
    assert measured["nested_w_open_count"] == 9
    assert any(e.kind == "implicit_word_close_before_word" for e in view.events)
    assert all(e.kind != "implicit_word_close_before_line" for e in view.events)

    nested_starts = [
        t
        for t in _start_tokens(view, "w")
        if measured["outer_start"] < t.mechanical_start < measured["outer_end"]
    ]
    assert len(nested_starts) == measured["nested_w_open_count"]
    _assert_original_offsets(view, prepared.original_bytes)


def test_terminal_open_word_closes_logically_at_text_end_only() -> None:
    api = _api()
    prepared = prepared_source.prepare(KBO1255)
    view = api.recover_word_state(prepared)
    effect = _effect(KBO1255)

    assert effect["failing_words"] == 1
    assert effect["words"][0]["lb_open_count"] == 0
    assert effect["words"][0]["nested_w_open_count"] == 0

    kinds = [event.kind for event in view.events]
    assert kinds == ["implicit_word_close_before_text_end"]
    event = view.events[0]
    assert event.element == "w"
    assert event.omitted_bytes is None
    assert event.omitted_semantic_annotation is None
    assert prepared.original_bytes[event.trigger_offset :].startswith(b"</text>")
    _assert_original_offsets(view, prepared.original_bytes)


def test_word_recovery_is_scoped_to_reviewed_word_resynchronization_dispositions() -> None:
    api = _api()
    prepared = prepared_source.prepare(WRAPPER_ONLY)

    with pytest.raises(api.NotWordResynchronization):
        api.recover_word_state(prepared)


def test_all_47_reviewed_word_state_events_recover_with_exact_accounting() -> None:
    api = _api()
    dispositions = json.loads(
        (PROGRAMS / "source_recovery_dispositions.json").read_text(encoding="utf8")
    )
    inventory = json.loads(
        (REPORTS / "source-recovery-inventory.json").read_text(encoding="utf8")
    )
    observed = {row["event_id"]: row for row in inventory["events"]}
    word_rows = [
        row
        for row in dispositions["events"]
        if row["planned_action"] == "resynchronize_word_state"
    ]

    assert len(word_rows) == 47
    assert len({row["event_id"].rsplit(":", 1)[0] for row in word_rows}) == 47

    for reviewed in word_rows:
        event_id = reviewed["event_id"]
        rel = event_id.rsplit(":", 1)[0]
        observation = observed[event_id]
        prepared = prepared_source.prepare(rel)
        view = api.recover_word_state(prepared)

        assert view.path == rel
        assert view.source_sha256 == reviewed["source_sha256"]
        assert observation["boundary"] == "text"
        assert set(observation["inserted_closures"]) == {"w"}
        assert len(view.events) == observation["inserted_close_count"], rel
        assert {event.kind for event in view.events} <= {
            "implicit_word_close_before_word",
            "implicit_word_close_before_line",
            "implicit_word_close_before_text_end",
        }
        assert all(event.element == "w" for event in view.events)
        assert all(event.omitted_bytes is None for event in view.events)
        assert all(
            event.omitted_semantic_annotation is None for event in view.events
        )
        _assert_original_offsets(view, prepared.original_bytes)


def test_mechanical_close_deletion_does_not_erase_surviving_markup_provenance() -> None:
    """A contextual removal must preserve byte-exact offsets of unchanged tags.

    Regresses the 47-file CI failure in KUB 50.123: OffsetMap treats the
    entire old/new replacement as edited, including an identical suffix.
    """
    api = _api()
    raw = b'<text><w>x</w> <w trans="a">z</w></text>'
    patch = repair.Patch(
        old=b'</w> <w trans="a">',
        new=b' <w trans="a">',
        reason="stray close tag, nothing open",
    )
    mechanical = repair.apply(raw, [patch])
    tokens = api.scan_markup(
        mechanical, source_bytes=raw, mechanical_patches=(patch,)
    )
    words = [t for t in tokens if t.kind == "start" and t.tag == "w"]
    assert len(words) == 2
    assert raw[words[1].start_offset:words[1].end_offset] == b'<w trans="a">'
    assert not words[1].synthetic


def test_lexically_changed_attribute_retains_original_span_but_is_marked_synthetic() -> None:
    """Lexical XML repair can anchor a token, but it is not literal original markup."""
    api = _api()
    raw = b'<text><w trans="a<b">x</w></text>'
    patch = repair.Patch(
        old=b'a<b',
        new=b'a&lt;b',
        reason="escape literal less-than in attribute",
    )
    mechanical = repair.apply(raw, [patch])
    tokens = api.scan_markup(
        mechanical, source_bytes=raw, mechanical_patches=(patch,)
    )
    word = next(t for t in tokens if t.tag == "w" and t.kind == "start")
    assert raw[word.start_offset:word.end_offset] == b'<w trans="a<b">'
    assert word.synthetic


def test_entirely_manufactured_markup_has_no_claimed_source_tag_span() -> None:
    """Internal mechanical tags may assist state tracking, but are not source XML."""
    api = _api()
    raw = b"<text>BAD</text>"
    patch = repair.Patch(old=b"BAD", new=b"<w/>", reason="mechanical example")
    mechanical = repair.apply(raw, [patch])
    word = next(
        t for t in api.scan_markup(
            mechanical, source_bytes=raw, mechanical_patches=(patch,)
        ) if t.tag == "w"
    )
    assert word.synthetic
    assert word.start_offset is None
    assert word.end_offset is None


def test_word_and_line_source_anchors_survive_recovery_on_all_47_paths() -> None:
    """Source/structural-view conservation is measured, not assumed from event counts.

    Every literal line/word opening in immutable XML must still have a
    source-anchored token in the logical recovery input; synthetic repaired
    markup must never silently stand in for an original opening.
    """
    api = _api()
    dispositions = json.loads(
        (PROGRAMS / "source_recovery_dispositions.json").read_text(encoding="utf8")
    )
    reviewed = [
        row["event_id"].rsplit(":", 1)[0]
        for row in dispositions["events"]
        if row["planned_action"] == "resynchronize_word_state"
    ]
    assert len(reviewed) == 47
    for rel in reviewed:
        prepared = prepared_source.prepare(rel)
        view = api.recover_word_state(prepared)
        audit = api.audit_opening_tags(prepared.original_bytes, view)
        assert audit.missing_line_starts == (), rel
        assert audit.missing_word_starts == (), rel
        assert audit.unexpected_line_starts == (), rel
        assert audit.unexpected_word_starts == (), rel
        assert audit.unanchored_line_starts == (), rel
        assert audit.unanchored_word_starts == (), rel


def test_opening_tag_audit_detects_loss_and_never_counts_synthetic_replacements() -> None:
    api = _api()
    raw = b"<text><lb/><w>one</w><lb/><w>two</w></text>"
    # A synthetic replacement has the correct tag name but is NOT the literal
    # original opening and must not satisfy source conservation.
    patch = repair.Patch(b"<lb/><w>two", b"<lb/><x>two", "test deletion")
    mechanical = repair.apply(raw, [patch])
    tokens = api.scan_markup(
        mechanical, source_bytes=raw, mechanical_patches=(patch,)
    )
    view = api.WordRecoveryView(
        path="synthetic.xml", source_sha256=sha256(raw).hexdigest(), tokens=tokens, events=()
    )
    audit = api.audit_opening_tags(raw, view)
    assert len(audit.missing_word_starts) == 1
    assert len(audit.unanchored_line_starts) == 0


def test_logical_word_events_do_not_claim_unmeasured_tf_conservation() -> None:
    """The source view cannot certify omissions until the converter consumes it."""
    api = _api()
    view = api.recover_word_state(prepared_source.prepare(KBO4149))
    assert view.events
    assert all(e.omitted_bytes is None for e in view.events)
    assert all(e.omitted_semantic_annotation is None for e in view.events)


def test_opening_tag_audit_rejects_cross_document_reuse_of_view() -> None:
    """Matching offset numbers do not make tokens provenance for other source bytes."""
    api = _api()
    raw = b"<text><lb/><w>x</w></text>"
    view = api.WordRecoveryView(
        path="forged.xml",
        source_sha256="0" * 64,
        tokens=api.scan_markup(raw),
        events=(),
    )
    with pytest.raises(api.SignatureDrift, match="source SHA"):
        api.audit_opening_tags(raw, view)


def test_source_anchor_audit_tolerates_real_unterminated_source_attribute() -> None:
    """KBo 12.55 has a corrupt <w ... attribute swallowing raw XML lexical scan.

    Recovery must derive candidate source word/line starts without demanding a
    globally well-formed original tag stream. This is a source-grounded case.
    """
    api = _api()
    prepared = prepared_source.prepare(KBO1255)
    with pytest.raises(api.SignatureDrift, match="unterminated"):
        api.scan_markup(prepared.original_bytes)
    audit = api.audit_opening_tags(
        prepared.original_bytes, api.recover_word_state(prepared)
    )
    assert audit.missing_line_starts == ()
    assert audit.missing_word_starts == ()


def test_source_anchor_audit_ignores_xml_like_content_inside_markup_and_comments() -> None:
    api = _api()
    raw = (
        b'<text><meta example="<w>not a source word</w>"/>'
        b'<!-- <lb/> -->'
        b'<![CDATA[<w>not markup</w>]]><lb/><w>real</w></text>'
    )
    view = api.WordRecoveryView(
        path="source-markup-control.xml",
        source_sha256=sha256(raw).hexdigest(),
        tokens=api.scan_markup(raw),
        events=(),
    )
    audit = api.audit_opening_tags(raw, view)
    assert (audit.source_word_starts, audit.source_line_starts) == (1, 1)
    assert audit.missing_word_starts == audit.missing_line_starts == ()


def test_opening_census_accepts_xml_whitespace_after_element_name() -> None:
    """Tab and newline are legal XML whitespace at source tag boundaries."""
    api = _api()
    raw = b"<text><lb\\n/><w\\ttrans='x'>a</w></text>"
    view = api.WordRecoveryView(
        path="whitespace.xml",
        source_sha256=sha256(raw).hexdigest(),
        tokens=api.scan_markup(raw),
        events=(),
    )
    audit = api.audit_opening_tags(raw, view)
    assert (audit.source_line_starts, audit.source_word_starts) == (1, 1)
    assert audit.missing_line_starts == audit.missing_word_starts == ()


def test_opening_census_detects_extra_forged_source_anchored_word() -> None:
    """Extra nodes with valid but *wrong-type* source anchors also break conservation."""
    api = _api()
    raw = b"<text><lb/><w>a</w><note>n</note></text>"
    tokens = api.scan_markup(raw)
    note = next(t for t in tokens if t.tag == "note" and t.kind == "start")
    view = api.WordRecoveryView(
        path="forged-word.xml",
        source_sha256=sha256(raw).hexdigest(),
        tokens=(*tokens, replace(note, tag="w")),
        events=(),
    )
    audit = api.audit_opening_tags(raw, view)
    assert audit.missing_word_starts == ()
    assert audit.unexpected_word_starts == (raw.index(b"<note>"),)
