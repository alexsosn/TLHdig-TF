"""RED contract #150: source-grounded terminal word reaches actual TF nodes.

This intentionally builds only a *preview subset* for one reviewed terminal word.
It must not modify production conversion, the source XML or the current artifact.
"""
from __future__ import annotations

import pytest

from tlhdig import morph, prepared_source, recovery, signs
from tlhdig.paths import CORPUS

try:
    from tlhdig import terminal_preview
except ImportError:  # TDD RED until the bridge exists
    terminal_preview = None


TERMINAL = "CTH 209_XML_TLH/KBo 12.55.xml"
MULTIWORD = "CTH 394_XML_BESRIT/Bo 3353.xml"


def _api():
    assert terminal_preview is not None, "terminal TF preview bridge not implemented"
    return terminal_preview


def test_real_tf_graph_witnesses_terminal_word_and_its_original_source(tmp_path):
    prepared = prepared_source.prepare(TERMINAL)
    payload = recovery.terminal_word_payload(prepared)
    api = _api().build_terminal_preview(prepared, tmp_path / "tf")

    assert len(api.F.otype.s("document")) == 1
    assert len(api.F.otype.s("line")) == 1
    words = api.F.otype.s("word")
    assert len(words) == 1
    w = words[0]

    # The absent literal </w> must not masquerade as a normal source.Span.
    assert api.F.recovery_open.v(w) == payload.opening_offset
    assert api.F.recovery_body_start.v(w) == payload.content_start_offset
    assert api.F.recovery_body_end.v(w) == payload.content_end_offset
    assert api.F.recovery_implicit_end.v(w) == 1

    assert api.F.trans.v(w) == payload.attributes["trans"]
    expected_signs = [
        t for t in signs.tokenise_word(payload.content_bytes) if t.type != "empty"
    ]
    graph_signs = api.L.d(w, otype="sign")
    assert graph_signs
    assert len(graph_signs) == len(expected_signs)
    assert [api.F.sym.v(s) for s in graph_signs] == [s.sym for s in expected_signs]
    assert [
        (api.F.srcxml.v(s) or "", api.F.after.v(s) or "")
        for s in graph_signs
    ] == [(s.srcxml, s.after) for s in expected_signs]

    expected_analyses = morph.analyses(payload.attributes)
    assert len(api.E.analyses.f(w)) == len(expected_analyses)
    assert api.F.nanalyses.v(w) == len(expected_analyses)
    assert api.F.mrpsel.v(w) == payload.attributes["mrp0sel"].strip()


def test_terminal_tf_preview_rejects_multiword_boundary_inference(tmp_path):
    with pytest.raises(recovery.SignatureDrift, match="single terminal"):
        _api().build_terminal_preview(
            prepared_source.prepare(MULTIWORD), tmp_path / "tf"
        )
