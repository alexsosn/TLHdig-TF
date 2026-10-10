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


# Two additional signed, terminal-singleton candidates. Each has *zero*
# mechanical patches; line/marker expectations come from immutable AOxml,
# not from the historical fully repaired Text-Fabric output.
SINGLETON_CASES = (
    ("CTH 448_XML_BESRIT/KBo 10.36.xml", 160, 59, 31),
    ("CTH 820_XML_TLH/KUB 48.15.xml", 37, 17, 21),
)


@pytest.mark.parametrize("path,word_count,line_count,del_closes", SINGLETON_CASES)
def test_two_additional_reviewed_terminal_words_in_complete_tf_document(
    tmp_path, path, word_count, line_count, del_closes,
):
    prep = prepared_source.prepare(path)
    assert prep.mechanical_patch_ordinals == ()
    assert len(prep.recovery_patch_ordinals) == 1

    view = recovery.recover_word_state(prep)
    audit = recovery.audit_opening_tags(prep.original_bytes, view)
    assert audit.source_word_starts == word_count
    assert audit.source_line_starts == line_count
    assert not (
        audit.missing_word_starts or audit.missing_line_starts
        or audit.unexpected_word_starts or audit.unexpected_line_starts
        or audit.duplicate_word_starts or audit.duplicate_line_starts
        or audit.out_of_order_starts
        or audit.unanchored_word_starts or audit.unanchored_line_starts
    ), "all original word/line anchors must survive source preparation"

    payload = recovery.terminal_word_payload(prep)
    assert payload.content_bytes == prep.original_bytes[
        payload.content_start_offset:payload.content_end_offset
    ]
    # The terminal word must be a source-backed *sign* word, not a contentless
    # layout word that the converter silently projects onto a sign slot.
    assert b"<del_fin/>" in payload.content_bytes
    assert payload.content_bytes.endswith(b" \n")

    baseline = _build(tmp_path / "baseline", path=path)
    graph = _build(tmp_path / "recovered", path=path, enable=True)
    assert baseline is not None and graph is not None
    assert _doc_inventory(graph) == _doc_inventory(baseline), (
        "recovering the terminal word may not change other editorial nodes"
    )
    assert len(graph.F.otype.s("line")) == line_count
    assert len(graph.F.otype.s("word")) + len(graph.F.otype.s("layout")) == word_count

    words = list(graph.F.otype.s("word"))
    recovered = [w for w in words if graph.F.recovery_open.v(w) is not None]
    assert len(recovered) == 1
    terminal = recovered[0]
    assert terminal == words[-1]
    assert graph.F.recovery_open.v(terminal) == payload.opening_offset
    assert graph.F.recovery_body_start.v(terminal) == payload.content_start_offset
    assert graph.F.recovery_body_end.v(terminal) == payload.content_end_offset
    assert graph.F.recovery_implicit_end.v(terminal) == 1
    assert graph.F.src_span.v(terminal) is None

    recovered_slots = graph.L.d(terminal, otype="sign")
    assert recovered_slots, "terminal word must produce at least one real sign"

    # Count parity is not enough: source marker boundaries must remain attached
    # to the sign(s) of this exact recovered word, not merely appear somewhere
    # else in the document as compensating nodes.
    slots = set(recovered_slots)
    terminal_del_closes = [
        c for c in graph.F.otype.s("cluster")
        if graph.F.type.v(c) == "del"
        and graph.F.from_close_marker.v(c) == 1
        and slots.intersection(graph.E.endsAt.f(c))
    ]
    assert payload.content_bytes.count(b"<del_fin/>") == 1
    assert len(terminal_del_closes) == 1
    if b"<laes_in/>" in payload.content_bytes:
        terminal_laes_opens = [
            c for c in graph.F.otype.s("cluster")
            if graph.F.type.v(c) == "laes"
            and graph.F.from_open_marker.v(c) == 1
            and slots.intersection(graph.E.startsAt.f(c))
        ]
        assert len(terminal_laes_opens) == 1
        assert graph.F.orphan.v(terminal_laes_opens[0]) == "open"
        assert graph.F.from_close_marker.v(terminal_laes_opens[0]) == 0

    assert b"".join(
        ((graph.F.srcxml.v(n) or "") + (graph.F.after.v(n) or "")).encode("utf8")
        for n in recovered_slots
    ) == payload.content_bytes

    baseline_words = baseline.F.otype.s("word")
    assert len(words) == len(baseline_words)
    for before, after in zip(baseline_words, words):
        assert baseline.F.trans.v(before) == graph.F.trans.v(after)
        assert baseline.F.nanalyses.v(before) == graph.F.nanalyses.v(after)
        assert baseline.F.mrpsel.v(before) == graph.F.mrpsel.v(after)
        assert len(baseline.E.selected.f(before)) == len(graph.E.selected.f(after))
        assert [
            baseline.F.sym.v(n) for n in baseline.L.d(before, otype="sign")
        ] == [
            graph.F.sym.v(n) for n in graph.L.d(after, otype="sign")
        ]

    # Independent source-driven editorial-marker count, not mere graph parity.
    assert prep.original_bytes.count(b"<del_fin/>") == del_closes
    assert len([
        c for c in graph.F.otype.s("cluster")
        if graph.F.type.v(c) == "del" and graph.F.from_close_marker.v(c) == 1
    ]) == del_closes
    for tag, family in ((b"<laes_in/>", "laes"), (b"<del_in/>", "del")):
        source_open = prep.original_bytes.count(tag)
        graph_open = sum(
            graph.F.type.v(c) == family
            and graph.F.from_open_marker.v(c) == 1
            for c in graph.F.otype.s("cluster")
        )
        assert graph_open == source_open, (path, tag, graph_open, source_open)


def test_source_recovery_provenance_features_have_meaningful_documentation():
    """Researchers must not confuse an implicit end with a literal src_span."""
    from tlhdig.featuremeta import DESCRIPTIONS

    for feat in (
        "recovery_open", "recovery_body_start", "recovery_body_end",
        "recovery_implicit_end", "recovery_line_open",
    ):
        assert feat in DESCRIPTIONS
        assert len(DESCRIPTIONS[feat]) > 25
        assert "(undocumented)" not in DESCRIPTIONS[feat]
    assert "src_span" in DESCRIPTIONS
