"""TDD gate #150: UBT 70 source-backed recovered word before the next real lb.

The historical inserted end-of-text closing w makes line-5's literal word
appear nested under line 4, and production suppresses it. These tests
check real AOxml, original-byte anchors, and a loaded whole-document TF graph.
No corpus-wide sibling or line-boundary inference is permitted.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from tlhdig import convert, prepared_source, recovery, repair
from tlhdig.paths import CORPUS, PATCHES

REL = "CTH 832_XML_TLH/UBT 70.xml"


def test_ubt70_word_boundary_is_one_signed_literal_line_opening():
    prep = prepared_source.prepare(REL)
    assert prep.mechanical_patch_ordinals == (1, 2)
    assert prep.recovery_patch_ordinals == (3,)
    view = recovery.recover_word_state(prep)
    assert len(view.events) == 1
    ev = view.events[0]
    assert ev.kind == "implicit_word_close_before_line"
    assert ev.start_offset == prep.original_bytes.index(b'<w trans="%-mu')
    assert prep.original_bytes[ev.trigger_offset:].startswith(b'<lb txtid="UBT 70" lnr="5')
    assert ev.end_offset == ev.trigger_offset
    assert prep.original_bytes.count(b"<w ") == 5
    assert prep.original_bytes.count(b"<lb ") == 5
    assert prep.original_bytes.count(b"<del_fin/>") == 6

    payload = recovery.word_before_line_payload(prep)
    assert payload.path == REL
    assert payload.opening_offset == ev.start_offset
    assert payload.content_end_offset == ev.end_offset
    assert payload.content_bytes == prep.original_bytes[
        payload.content_start_offset:payload.content_end_offset
    ]
    assert payload.content_bytes == b'<del_fin/>x-mu<gap c="RASUR"/> \n'
    assert payload.end_is_implicit
    assert payload.attribute_source == "mechanical"
    assert payload.attributes["mrp0sel"].strip() == "1"
    assert payload.attributes["trans"].startswith("%-mu")
    assert payload.content_end_offset < prep.original_bytes.index(b'<w trans="%"')
    assert prep.original_bytes[payload.content_end_offset:].count(b"</w>") == 1
    # A genuine terminal singleton extraction is explicitly incorrect here.
    with pytest.raises(recovery.SignatureDrift, match="single terminal"):
        recovery.terminal_word_payload(prep)


def test_ubt70_recovered_complete_tf_retains_both_original_words_and_lines(tmp_path):
    prep = prepared_source.prepare(REL)
    payload = recovery.word_before_line_payload(prep)
    source_file = CORPUS / REL
    api = convert.build(
        CORPUS, tmp_path / "tf", files=[source_file],
        patches=repair.read_manifest(PATCHES),
        terminal_recovery_paths=(REL,),
    )
    assert api is not None

    F, L, E = api.F, api.L, api.E
    assert len(F.otype.s("document")) == 1
    assert F.docid.v(F.otype.s("document")[0]) == "UBT 70"
    lines = F.otype.s("line")
    words = F.otype.s("word")
    assert len(lines) == prep.original_bytes.count(b"<lb ") == 5
    assert len(words) == prep.original_bytes.count(b"<w ") == 5
    assert [F.lnr.v(n) for n in lines] == ["1′", "2′", "3′", "4′", "5′"]
    for ln in lines:
        assert len(L.d(ln, otype="word")) == 1, (
            "literal words must retain separate source lines"
        )

    first_four = L.d(lines[3], otype="word")
    final_five = L.d(lines[4], otype="word")
    assert len(first_four) == len(final_five) == 1
    w4, w5 = first_four[0], final_five[0]
    assert w4 != w5
    assert w4 == words[-2] and w5 == words[-1]
    assert F.recovery_open.v(w4) == payload.opening_offset
    assert F.recovery_body_start.v(w4) == payload.content_start_offset
    assert F.recovery_body_end.v(w4) == payload.content_end_offset
    assert F.recovery_implicit_end.v(w4) == 1
    assert F.src_span.v(w4) is None
    assert F.recovery_open.v(w5) is None
    assert F.trans.v(w4) == payload.attributes["trans"]
    assert F.trans.v(w5) == "%"
    assert F.nanalyses.v(w4) == 1
    assert F.nanalyses.v(w5) == 1
    assert F.mrpsel.v(w4) == F.mrpsel.v(w5) == "1"

    slots4 = L.d(w4, otype="sign")
    slots5 = L.d(w5, otype="sign")
    assert [F.sym.v(s) for s in slots4] == ["x", "mu"]
    assert [F.sym.v(s) for s in slots5] == ["x"]
    assert b"".join(
        ((F.srcxml.v(s) or "") + (F.after.v(s) or "")).encode("utf8")
        for s in slots4
    ) == payload.content_bytes
    assert b"".join(
        ((F.srcxml.v(s) or "") + (F.after.v(s) or "")).encode("utf8")
        for s in slots5
    ) == b'<del_fin/>x'
    assert len(E.analyses.f(w4)) == len(E.analyses.f(w5)) == 1
    assert len(E.selected.f(w4)) == len(E.selected.f(w5)) == 1

    # The non-recovered final word has a real, literal </w>, not a fake
    # source-word end at the next </text>.
    start, stop = map(int, F.src_span.v(w5).split("-"))
    assert prep.original_bytes[start:stop].startswith(b'<w trans="%"')
    assert prep.original_bytes[start:stop].endswith(b"</w>")
    assert prep.original_bytes[start:stop].count(b"<w ") == 1
    assert b"<lb" not in prep.original_bytes[start:stop]

    # One in-word original gap must remain queryable; the separate
    # line-type gap after w5 is NOT another literal lb.
    gaps = F.otype.s("gap")
    assert len(gaps) == 1
    assert E.gapOf.f(gaps[0]) == (w4,)
    gs, ge = F.gap_start.v(gaps[0]), F.gap_end.v(gaps[0])
    assert prep.original_bytes[gs:ge] == b'<gap c="RASUR"/>'
    assert F.gap_c.v(gaps[0]) == "RASUR"
    assert L.d(gaps[0], otype="sign") == (slots4[-1],)
    assert len([
        c for c in F.otype.s("cluster")
        if F.type.v(c) == "del" and F.from_close_marker.v(c) == 1
    ]) == prep.original_bytes.count(b"<del_fin/>") == 6


def test_ubt70_recovery_rejects_unknown_and_changed_source(tmp_path):
    prep = prepared_source.prepare(REL)
    forged = replace(
        prep, original_bytes=prep.original_bytes.replace(b"RASUR", b"RAZUR"),
    )
    with pytest.raises(recovery.SignatureDrift, match="source SHA"):
        recovery.word_before_line_payload(forged)
    with pytest.raises(ValueError, match="reviewed|pilot"):
        convert.build(
            CORPUS, tmp_path / "forbidden",
            files=[CORPUS / REL],
            patches=repair.read_manifest(PATCHES),
            terminal_recovery_paths=(REL + ".unreviewed",),
        )
