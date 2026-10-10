"""Research/TDD gate #150: recover one real word in the COMPLETE document.

This is a strict, explicitly opted-in pilot for pinned KBo 12.55; it does not
turn on inference for the other 46 reviewed sources. Legacy full-repair parsing
is still used for surrounding tree structure, so passing here is an intermediate
bridge, *not* evidence of independent full recovery or validator parity.
"""
from __future__ import annotations

from collections import Counter

import pytest

from tlhdig import convert, prepared_source, recovery, repair
from tlhdig.paths import CORPUS, PATCHES


REL = "CTH 209_XML_TLH/KBo 12.55.xml"
AMBIGUOUS = "CTH 394_XML_BESRIT/Bo 3353.xml"


def _build(tmp_path, *, enable=False, path=REL):
    corpus_file = CORPUS / path
    assert corpus_file.is_file()
    return convert.build(
        CORPUS, tmp_path, files=[corpus_file],
        patches=repair.read_manifest(PATCHES),
        terminal_recovery_paths=(path,) if enable else (),
    )


def _doc_inventory(api):
    F = api.F
    return {
        kind: len(F.otype.s(kind))
        for kind in F.otype.all
    }


def test_complete_document_pilot_conserves_structure_signs_and_morphology(tmp_path):
    prepared = prepared_source.prepare(REL)
    payload = recovery.terminal_word_payload(prepared)
    baseline = _build(tmp_path / "baseline")
    actual = _build(tmp_path / "recovered", enable=True)
    assert baseline is not None and actual is not None

    assert _doc_inventory(actual) == _doc_inventory(baseline), (
        "single-terminal-word recovery must not change other document nodes"
    )
    assert len(actual.F.otype.s("document")) == 1
    for feat in ("docid", "cth", "subcorpus", "lang", "src_file"):
        a = actual.F
        b = baseline.F
        assert [
            getattr(a, feat).v(n) for n in a.otype.s("document")
        ] == [
            getattr(b, feat).v(n) for n in b.otype.s("document")
        ], feat

    bw = list(baseline.F.otype.s("word"))
    aw = list(actual.F.otype.s("word"))
    assert len(bw) == len(aw)
    assert [
        baseline.F.trans.v(n) for n in bw
    ] == [
        actual.F.trans.v(n) for n in aw
    ]
    recovered = [
        w for w in aw
        if actual.F.recovery_open.v(w) is not None
    ]
    assert len(recovered) == 1
    w = recovered[0]
    assert w == aw[-1], "only the original terminal word is recovered"
    assert actual.F.recovery_open.v(w) == payload.opening_offset
    assert actual.F.recovery_body_start.v(w) == payload.content_start_offset
    assert actual.F.recovery_body_end.v(w) == payload.content_end_offset
    assert actual.F.recovery_implicit_end.v(w) == 1
    assert actual.F.src_span.v(w) is None, (
        "a synthetic source </w> must not be claimed as a literal src_span"
    )

    for i, (old, new) in enumerate(zip(bw, aw)):
        assert baseline.F.nanalyses.v(old) == actual.F.nanalyses.v(new)
        assert baseline.F.mrpsel.v(old) == actual.F.mrpsel.v(new)
        assert len(baseline.E.selected.f(old)) == len(actual.E.selected.f(new))
        old_signs = baseline.L.d(old, otype="sign")
        new_signs = actual.L.d(new, otype="sign")
        assert [baseline.F.sym.v(s) for s in old_signs] == [
            actual.F.sym.v(s) for s in new_signs
        ], i
        if new != w:
            assert [
                (baseline.F.srcxml.v(s) or "", baseline.F.after.v(s) or "")
                for s in old_signs
            ] == [
                (actual.F.srcxml.v(s) or "", actual.F.after.v(s) or "")
                for s in new_signs
            ], i

    word_signs = actual.L.d(w, otype="sign")
    assert b"".join(
        ((actual.F.srcxml.v(s) or "") + (actual.F.after.v(s) or "")).encode("utf8")
        for s in word_signs
    ) == payload.content_bytes

    # Independent source marker census vs actual full-document TF graph.
    assert prepared.original_bytes[payload.content_start_offset:payload.content_end_offset].count(
        b"<del_fin/>"
    ) == 1
    close_clusters = [
        n for n in actual.F.otype.s("cluster")
        if actual.F.type.v(n) == "del"
        and actual.F.from_close_marker.v(n) == 1
    ]
    old_closes = [
        n for n in baseline.F.otype.s("cluster")
        if baseline.F.type.v(n) == "del"
        and baseline.F.from_close_marker.v(n) == 1
    ]
    assert len(close_clusters) == len(old_closes)

    # Unlike legacy-vs-pilot parity, these expectations come directly from
    # the SHA-pinned original bytes, not the historically repaired XML tree.
    lexical = recovery.audit_opening_tags(
        prepared.original_bytes, recovery.recover_word_state(prepared)
    )
    assert lexical.source_word_starts == 14
    assert lexical.source_line_starts == 7
    assert lexical.missing_word_starts == lexical.missing_line_starts == ()
    assert lexical.unexpected_word_starts == lexical.unexpected_line_starts == ()
    assert len(actual.F.otype.s("word")) + len(actual.F.otype.s("layout")) == (
        lexical.source_word_starts
    )
    assert len(actual.F.otype.s("line")) == lexical.source_line_starts
    source_del_closes = prepared.original_bytes.count(b"<del_fin/>")
    assert source_del_closes == 7
    assert len(close_clusters) == source_del_closes, (
        "the original's 7 editorial lacuna closings need 7 graph boundaries"
    )


def test_complete_document_pilot_is_explicit_and_fails_closed(tmp_path):
    with pytest.raises((recovery.SignatureDrift, ValueError), match="pilot|single terminal|reviewed"):
        _build(tmp_path / "ambiguous", enable=True, path=AMBIGUOUS)


def test_complete_document_pilot_rejects_unknown_source_before_graph_mutation(tmp_path):
    # No opt-in can reclassify a file that has no signed source recovery policy.
    with pytest.raises((recovery.SignatureDrift, ValueError), match="pilot|reviewed"):
        convert.build(
            CORPUS, tmp_path / "invalid",
            files=[CORPUS / REL], patches=repair.read_manifest(PATCHES),
            terminal_recovery_paths=("CTH 209_XML_TLH/not-reviewed.xml",),
        )
