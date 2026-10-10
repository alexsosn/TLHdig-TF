"""#150: source-authoritative, loaded-TF per-analysis output parity (RED).

This deliberately does not use reparsed historical XML as its oracle.
The input witnesses have already been authenticated against immutable AOxml
and mechanical-only patches. The checker must audit *written* morphology,
not merely count candidates or reread F.mrpsel.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from tlhdig import convert, morph_output, prepared_source, recovery, repair
from tlhdig.paths import CORPUS, PATCHES


REVIEWED = (
    "CTH 209_XML_TLH/KBo 12.55.xml",
    "CTH 448_XML_BESRIT/KBo 10.36.xml",
    "CTH 820_XML_TLH/KUB 48.15.xml",
    "CTH 832_XML_TLH/UBT 70.xml",
)


def _loaded(tmp_path, rel):
    prepared = prepared_source.prepare(rel)
    witnesses = recovery.lexical_word_witnesses(prepared)
    api = convert.build(
        CORPUS, tmp_path / "loaded", files=[CORPUS / rel],
        patches=repair.read_manifest(PATCHES),
        terminal_recovery_paths=(rel,),
    )
    assert api is not None
    graph = {
        api.F.source_word_open.v(n): n
        for n in (*api.F.otype.s("word"), *api.F.otype.s("layout"))
        if api.F.source_word_open.v(n) is not None
    }
    assert set(graph) == {w.opening_offset for w in witnesses}
    return api, {w.opening_offset: w for w in witnesses}, graph


@pytest.mark.parametrize("rel", REVIEWED)
def test_loaded_morphology_matches_every_source_candidate_and_selected_edge(
    tmp_path, rel,
):
    api, witnesses, graph = _loaded(tmp_path, rel)
    audited = 0
    for offset, witness in witnesses.items():
        node = graph[offset]
        if api.F.otype.v(node) == "layout":
            # Layout-only analysis loss is separately tracked by #105.
            # An independent audit must *not* certify it as conserved.
            if any(k.startswith("mrp") and k[3:].isdigit() for k in witness.attributes):
                with pytest.raises(morph_output.MorphOutputMismatch, match="layout"):
                    morph_output.assert_word_output(api, node, witness.attributes)
            continue
        morph_output.assert_word_output(api, node, witness.attributes)
        audited += 1
    assert audited > 0


def test_source_case_peran_has_four_distinct_analysis_semantics(tmp_path):
    rel = "CTH 448_XML_BESRIT/KBo 10.36.xml"
    api, witnesses, graph = _loaded(tmp_path, rel)
    target = next(
        witness for witness in witnesses.values()
        if witness.attributes.get("trans") == "peran"
    )
    w = graph[target.opening_offset]
    assert api.F.otype.v(w) == "word"
    candidates = {
        api.F.index.v(a): a for a in api.E.analyses.f(w)
    }
    assert set(candidates) == {1, 2, 3, 4}
    F = api.F
    assert [
        (F.lemma.v(candidates[i]), F.gloss.v(candidates[i]),
         F.field4_kind.v(candidates[i]), F.pos.v(candidates[i]))
        for i in (1, 2, 3)
    ] == [
        ("peran", "vor", "pos", "ADV"),
        ("peran", "vor", "pos", "POSP"),
        ("peran", "vor-", "pos", "PREV"),
    ]
    fourth = candidates[4]
    assert F.lemma.v(fourth) == "per, parn-"
    assert F.gloss.v(fourth) == "Haus"
    assert F.clitic_lemma.v(fourth) == "an"
    assert F.clitic_morph.v(fourth) == "PPRO.3SG.C.ACC"
    assert api.E.selected.f(w) == ()
    morph_output.assert_word_output(api, w, target.attributes)


def test_source_case_nu_has_literal_valued_selection_edge(tmp_path):
    rel = "CTH 820_XML_TLH/KUB 48.15.xml"
    api, witnesses, graph = _loaded(tmp_path, rel)
    target = next(
        witness for witness in witnesses.values()
        if witness.attributes.get("trans") == "nu"
        and witness.attributes.get("mrp0sel", "").strip() == "1"
    )
    w = graph[target.opening_offset]
    (a,) = api.E.analyses.f(w)
    assert api.F.index.v(a) == 1
    assert api.E.selected.f(w) == (a,)
    assert api.E.selected.v(w, a) == "1"
    assert api.F.lemma.v(a) == "nu"
    assert api.F.morph.v(a) == "CONNn"
    morph_output.assert_word_output(api, w, target.attributes)


def test_output_audit_rejects_corrupt_emitted_lemma_or_selection(tmp_path):
    rel = "CTH 820_XML_TLH/KUB 48.15.xml"
    api, witnesses, graph = _loaded(tmp_path, rel)
    target = next(
        witness for witness in witnesses.values()
        if witness.attributes.get("trans") == "nu"
        and witness.attributes.get("mrp0sel", "").strip() == "1"
    )
    w = graph[target.opening_offset]
    (a,) = api.E.analyses.f(w)

    class ForgedLemmaFeature:
        def v(self, node):
            return "forged-lemma" if node == a else api.F.lemma.v(node)

    class ForgedF:
        def __getattr__(self, name):
            return ForgedLemmaFeature() if name == "lemma" else getattr(api.F, name)

    forged = SimpleNamespace(F=ForgedF(), E=api.E, Fall=api.Fall)
    with pytest.raises(morph_output.MorphOutputMismatch, match="lemma"):
        morph_output.assert_word_output(forged, w, target.attributes)

    altered = dict(target.attributes)
    altered["mrp0sel"] = "2"
    with pytest.raises(morph_output.MorphOutputMismatch, match="select"):
        morph_output.assert_word_output(api, w, altered)
