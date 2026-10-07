"""Phase-2 RED contract for reviewed word-state recovery (#12).

The recovery layer is intentionally specified as an event view over immutable source
coordinates.  It must not manufacture a corrected XML byte stream.
"""
from __future__ import annotations

import json

import pytest

from tlhdig import prepared_source
from tlhdig.paths import REPORTS

try:
    from tlhdig import recovery
except ImportError:  # RED until Phase 2 exists.
    recovery = None


DAAM = "CTH 527_XML_KULTINV/DAAM 1.39.xml"
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
    prepared = prepared_source.prepare(DAAM)
    view = api.recover_word_state(prepared)
    raw = prepared.original_bytes
    effect = _effect(DAAM)
    measured = effect["words"][0]

    assert view.path == DAAM
    assert view.source_sha256 == prepared.source_sha256
    assert any(e.kind == "implicit_word_close_before_line" for e in view.events)
    assert all(e.omitted_bytes == 0 for e in view.events)

    # The old repaired-tree span swallowed 124 independent line starts.  The tolerant
    # event view must still expose every one of those source tags instead of making
    # them descendants of a single giant logical word.
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
    assert event.omitted_bytes == 0
    assert event.omitted_semantic_annotation is False
    assert prepared.original_bytes[event.trigger_offset :].startswith(b"</text>")
    _assert_original_offsets(view, prepared.original_bytes)


def test_word_recovery_is_scoped_to_reviewed_word_resynchronization_dispositions() -> None:
    api = _api()
    prepared = prepared_source.prepare(WRAPPER_ONLY)

    with pytest.raises(api.NotWordResynchronization):
        api.recover_word_state(prepared)
