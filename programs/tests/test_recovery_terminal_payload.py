"""RED gate #150: one genuinely terminal recovered word as a TF-ready input payload.

This is deliberately narrower than multiword resynchronization: a terminal
</text> with exactly one open word and no following <w>/<lb>. It provides
source-grounded bytes and attributes without inventing a source </w>.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256

import lxml.etree as LE
import pytest

from tlhdig import morph, prepared_source, recovery, repair, signs, source
from tlhdig.paths import PATCHES


TERMINAL = "CTH 209_XML_TLH/KBo 12.55.xml"
MULTIWORD = "CTH 394_XML_BESRIT/Bo 3353.xml"


def test_terminal_payload_matches_source_and_existing_word_semantics():
    prepared = prepared_source.prepare(TERMINAL)
    payload = recovery.terminal_word_payload(prepared)

    assert payload.path == TERMINAL
    assert payload.source_sha256 == sha256(prepared.original_bytes).hexdigest()
    assert payload.opening_offset == prepared.original_bytes.rfind(b"<w trans=")
    assert payload.content_start_offset > payload.opening_offset
    assert payload.content_end_offset == prepared.original_bytes.index(b"</text>")
    assert payload.content_bytes == prepared.original_bytes[
        payload.content_start_offset:payload.content_end_offset
    ]
    assert payload.content_bytes.endswith(b'<gap c="Text bricht ab"/> \n')
    assert payload.end_is_implicit
    assert payload.attribute_source == "mechanical"
    assert payload.attributes["mrp0sel"].strip() == "1"
    assert payload.attributes["trans"].startswith("%-uš")

    # Compare against the existing strict reparsed tree only as a temporary
    # *baseline*, not as the provenance authority for the new word.
    source_sha, patches = repair.read_manifest(PATCHES)[TERMINAL]
    legacy = repair.apply(prepared.original_bytes, patches, expect_sha=source_sha)
    root = LE.fromstring(legacy)
    legacy_word = list(root.iter("w"))[-1]
    assert payload.attributes == dict(legacy_word.attrib)
    legacy_span = [
        span for span in source.scan(legacy) if span.tag == "w"
    ][-1]
    legacy_inner = source.inner_bytes(legacy, legacy_span)
    assert payload.content_bytes == legacy_inner

    recovered_signs = signs.tokenise_word(payload.content_bytes)
    baseline_signs = signs.tokenise_word(legacy_inner)
    assert [
        (s.sym, s.srcxml, s.after, s.type) for s in recovered_signs
    ] == [
        (s.sym, s.srcxml, s.after, s.type) for s in baseline_signs
    ]
    assert "".join(s.srcxml + s.after for s in recovered_signs).encode() == (
        payload.content_bytes
    )
    assert morph.analyses(payload.attributes) == morph.analyses(legacy_word.attrib)
    assert morph.parse_selection(payload.attributes["mrp0sel"]) == (
        morph.parse_selection(legacy_word.get("mrp0sel"))
    )


def test_terminal_payload_does_not_infer_boundaries_for_ambiguous_nested_words():
    with pytest.raises(recovery.SignatureDrift, match="single terminal"):
        recovery.terminal_word_payload(prepared_source.prepare(MULTIWORD))


def test_terminal_payload_rejects_source_identity_drift():
    prepared = prepared_source.prepare(TERMINAL)
    forged = replace(
        prepared,
        original_bytes=prepared.original_bytes.replace(b"Text bricht ab", b"Text bricht xx"),
    )
    with pytest.raises(recovery.SignatureDrift, match="source SHA"):
        recovery.terminal_word_payload(forged)


def test_terminal_payload_attributes_cannot_be_mutated_after_source_validation():
    """Frozen dataclass is insufficient if an exposed morphology mapping is mutable."""
    payload = recovery.terminal_word_payload(prepared_source.prepare(TERMINAL))
    original_selection = payload.attributes["mrp0sel"]
    with pytest.raises(TypeError):
        payload.attributes["mrp0sel"] = "DEL"
    assert payload.attributes["mrp0sel"] == original_selection
