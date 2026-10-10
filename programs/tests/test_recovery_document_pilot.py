"""Research/TDD gate #150: recover one real word in the COMPLETE document.

This is a strict, explicitly opted-in pilot for pinned KBo 12.55; it does not
turn on inference for the other 46 reviewed sources. Legacy full-repair parsing
is still used for surrounding tree structure, so passing here is an intermediate
bridge, *not* evidence of independent full recovery or validator parity.
"""
from __future__ import annotations

from collections import Counter

import pytest
from lxml import etree as LE

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

    # Every literal source gap inside a reviewed recovered word is now a
    # first-class annotation; non-gap TF node inventories are unchanged.
    graph_counts = _doc_inventory(actual)
    expected_gaps = len([
        t for t in recovery.scan_markup(payload.content_bytes)
        if t.tag == "gap" and t.kind == "empty"
    ])
    assert len(actual.F.otype.s("gap")) == expected_gaps == 1
    graph_counts.pop("gap")
    assert graph_counts == _doc_inventory(baseline), (
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
    for gap in actual.F.otype.s("gap"):
        assert actual.E.gapOf.f(gap) == (w,)
        start, end = actual.F.gap_start.v(gap), actual.F.gap_end.v(gap)
        assert prepared.original_bytes[start:end] == b'<gap c="Text bricht ab"/>'
        assert actual.L.d(gap, otype="sign") == (word_signs[-1],)
        assert actual.F.gap_c.v(gap) == "Text bricht ab"
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
    graph_inventory = _doc_inventory(graph)
    gap_nodes = tuple(graph.F.otype.s("gap")) if "gap" in graph.F.otype.all else ()
    literal_gaps = [
        t for t in recovery.scan_markup(payload.content_bytes)
        if t.tag == "gap" and t.kind == "empty"
    ]
    # All immutable-source recovered gaps are typed, including gaps that
    # the tokenizer placed on an already retained sign rather than an empty
    # discarded trailing token (KBo 10.36).
    assert len(gap_nodes) == len(literal_gaps)
    assert len(gap_nodes) == (2 if path.endswith("KUB 48.15.xml") else 1)
    graph_inventory.pop("gap")
    assert graph_inventory == _doc_inventory(baseline), (
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

    if gap_nodes:
        # A tokenizer can conserve the string while hiding the actual
        # editorial objects; prove literal source-byte offsets and source
        # attributes of each separately queryable gap annotation.
        source_gaps = [
            token for token in recovery.scan_markup(payload.content_bytes)
            if token.tag == "gap" and token.kind == "empty"
        ]
        assert len(source_gaps) == len(gap_nodes) == len(literal_gaps)
        for gap, token in zip(gap_nodes, source_gaps):
            expected_start = payload.content_start_offset + token.mechanical_start
            expected_end = payload.content_start_offset + token.mechanical_end
            assert graph.F.gap_start.v(gap) == expected_start
            assert graph.F.gap_end.v(gap) == expected_end
            literal = prep.original_bytes[expected_start:expected_end]
            assert literal.startswith(b"<gap ") and literal.endswith(b"/>")
            tag = LE.fromstring(
                literal, parser=LE.XMLParser(
                    recover=False, resolve_entities=False, no_network=True
                )
            )
            assert graph.F.gap_c.v(gap) == tag.get("c")
            # TF omits an entire feature file when every node lacks its
            # optional value. A missing gap_t feature is correct for a
            # document whose original gap tags have no literal @t.
            gap_type = (
                graph.F.gap_t.v(gap)
                if "gap_t" in set(graph.Fall()) else None
            )
            assert (gap_type or "") == tag.get("t", "")
            assert graph.E.gapOf.f(gap) == (terminal,)

    recovered_slots = graph.L.d(terminal, otype="sign")
    if gap_nodes:
        for gap in gap_nodes:
            assert graph.L.d(gap, otype="sign") == (recovered_slots[-1],)
            assert graph.F.gap_anchor_offset.v(gap) == len(
                graph.F.sym.v(recovered_slots[-1])
            )
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
        "gap_start", "gap_end", "gap_anchor_offset", "gap_c", "gap_t", "gapOf",
    ):
        assert feat in DESCRIPTIONS
        assert len(DESCRIPTIONS[feat]) > 25
        assert "(undocumented)" not in DESCRIPTIONS[feat]
    assert "src_span" in DESCRIPTIONS


def test_terminal_pilot_fails_closed_if_empty_tokens_would_change_gap_ownership(tmp_path):
    """The SHA-reviewed gap-node witness is validated only for keep_empty=False.

    With empty sign slots enabled the terminal gap markers would attach to
    different/extra slots and the existing writer skips typed gap emission.
    Neither is an acceptable silent change in a source recovery pilot.
    """
    path = "CTH 820_XML_TLH/KUB 48.15.xml"
    with pytest.raises(ValueError, match="keep_empty"):
        convert.build(
            CORPUS, tmp_path / "tf",
            files=[CORPUS / path], patches=repair.read_manifest(PATCHES),
            keep_empty=True, terminal_recovery_paths=(path,),
        )
