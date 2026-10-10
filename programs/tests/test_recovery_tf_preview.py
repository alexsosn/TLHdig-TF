"""RED contract #150: source-grounded terminal word reaches actual TF nodes.

This intentionally builds only a *preview subset* for one reviewed terminal word.
It must not modify production conversion, the source XML or the current artifact.
"""
from __future__ import annotations

from dataclasses import replace
import pytest

from tlhdig import convert, morph, prepared_source, recovery, signs

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
    source_lines = [
        t for t in recovery.recover_word_state(prepared).tokens
        if t.tag == "lb" and t.kind == "empty"
        and t.start_offset is not None
        and t.start_offset < payload.opening_offset
    ]
    assert source_lines
    assert api.F.recovery_line_open.v(api.F.otype.s("line")[0]) == (
        source_lines[-1].start_offset
    )
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
    # The normal empty-token policy drops a final whitespace-only token;
    # recovery keeps that original suffix on the final *real* sign rather
    # than adding an artificial sign slot or losing source bytes.
    retained = "".join(t.srcxml + t.after for t in expected_signs).encode()
    assert payload.content_bytes.startswith(retained)
    suffix = payload.content_bytes[len(retained):].decode("utf8")
    assert suffix == "\n"
    assert [
        (api.F.srcxml.v(s) or "", api.F.after.v(s) or "")
        for s in graph_signs[:-1]
    ] == [(t.srcxml, t.after) for t in expected_signs[:-1]]
    assert api.F.srcxml.v(graph_signs[-1]) == expected_signs[-1].srcxml
    assert api.F.after.v(graph_signs[-1]) == expected_signs[-1].after + suffix

    expected_analyses = morph.analyses(payload.attributes)
    assert len(api.E.analyses.f(w)) == len(expected_analyses)
    assert api.F.nanalyses.v(w) == len(expected_analyses)
    assert api.F.mrpsel.v(w) == payload.attributes["mrp0sel"].strip()
    reconstructed = "".join(
        (api.F.srcxml.v(s) or "") + (api.F.after.v(s) or "")
        for s in graph_signs
    ).encode("utf8")
    assert reconstructed == payload.content_bytes, (
        "graph sign features must round-trip the immutable source word body"
    )
    assert len(api.E.selected.f(w)) == 1


def test_terminal_tf_preview_rejects_multiword_boundary_inference(tmp_path):
    with pytest.raises(recovery.SignatureDrift, match="single terminal"):
        _api().build_terminal_preview(
            prepared_source.prepare(MULTIWORD), tmp_path / "tf"
        )


def test_recovered_tail_carries_only_literal_final_whitespace():
    """Regression from KBo 12.55: never discard source newline after a gap."""
    from tlhdig.signs import Sign

    reading = Sign(srcxml="a", sym="a", after=" ", type="reading")
    trailing = Sign(srcxml="\n", sym="", after="", type="empty")
    tokens = [reading, trailing]
    convert._preserve_recovered_suffix(tokens, b"a \n", keep_empty=False)
    assert reading.after == " \n"
    assert "".join(t.srcxml + t.after for t in tokens if t.type != "empty") == "a \n"


def test_recovered_tail_rejects_dropped_markup_and_middle_content():
    """No automatic sign repair may launder missing annotation as whitespace."""
    from tlhdig.signs import Sign

    reading = Sign(srcxml="a", sym="a", type="reading")
    missing_markup = Sign(srcxml="<gap c='x'/>", type="empty")
    with pytest.raises(recovery.SignatureDrift, match="non-whitespace|conservation"):
        convert._preserve_recovered_suffix(
            [reading, missing_markup], b"a<gap c='x'/>", keep_empty=False
        )
    assert reading.after == ""

    other = Sign(srcxml="b", sym="b", type="reading")
    dropped_middle = Sign(srcxml="<gap/>", type="empty")
    with pytest.raises(recovery.SignatureDrift, match="non-whitespace|conservation"):
        convert._preserve_recovered_suffix(
            [reading, dropped_middle, other], b"a<gap/>b", keep_empty=False
        )
    assert reading.after == ""


def test_recovered_tail_rejects_tokeniser_roundtrip_drift():
    from tlhdig.signs import Sign

    wrong = Sign(srcxml="changed", sym="c", type="reading")
    with pytest.raises(recovery.SignatureDrift, match="tokeniser"):
        convert._preserve_recovered_suffix([wrong], b"source", keep_empty=False)


def test_terminal_graph_emits_source_orphan_close_as_damage_cluster(tmp_path):
    """KBo 12.55's one <del_fin/> cannot survive only in srcxml bytes.

    The researcher needs a first-class TF cluster marked as a source-backed
    orphan close, with a concrete sign boundary. A synthetic opening marker
    must not be invented to make a complete range.
    """
    prepared = prepared_source.prepare(TERMINAL)
    payload = recovery.terminal_word_payload(prepared)
    assert payload.content_bytes.count(b"<del_fin/>") == 1
    api = _api().build_terminal_preview(prepared, tmp_path / "tf")
    clusters = [
        n for n in api.F.otype.s("cluster")
        if api.F.type.v(n) == "del" and api.F.from_close_marker.v(n) == 1
    ]
    assert len(clusters) == 1
    cl = clusters[0]
    assert api.F.orphan.v(cl) == "close"
    assert api.F.from_open_marker.v(cl) == 0
    close_signs = api.E.endsAt.f(cl)
    assert len(close_signs) == 1
    assert close_signs[0] in api.L.d(api.F.otype.s("word")[0], otype="sign")


class _RejectUnverifiedGraphWrites:
    def node(self, *args, **kwargs):
        raise AssertionError("invalid recovery must fail before creating any TF node")


def test_recovered_word_adapter_refuses_forged_source_and_payload():
    """The shared production word emitter must not trust caller-supplied bytes.

    Both the source digest and the exact original body slice must match before
    any TF node/slot side effects occur.
    """
    prepared = prepared_source.prepare(TERMINAL)
    valid = recovery.terminal_word_payload(prepared)
    state = convert._State(_RejectUnverifiedGraphWrites(), keep_empty=False)
    with pytest.raises(recovery.SignatureDrift, match="provenance|source|SHA"):
        state.word(
            None, None, None,
            recovered=replace(valid, content_bytes=b"forged"),
            recovered_source=prepared.original_bytes,
            recovered_prepared=prepared,
        )
    with pytest.raises(recovery.SignatureDrift, match="provenance|source|SHA"):
        state.word(
            None, None, None,
            recovered=valid, recovered_source=b"forged bytes",
            recovered_prepared=prepared,
        )
    with pytest.raises(recovery.SignatureDrift, match="provenance|source|SHA"):
        state.word(
            None, None, None,
            recovered=object(), recovered_source=prepared.original_bytes,
            recovered_prepared=prepared,
        )


def test_recovered_word_ignores_untrusted_legacy_element_attributes():
    """Source-backed graph words must not learn trans/morph from repaired tree."""

    class PoisonLegacyNode:
        def get(self, *args, **kwargs):
            raise AssertionError("legacy element attributes consulted")

        @property
        def attrib(self):
            raise AssertionError("legacy morphology attributes consulted")

    class StopOnGraphEmission:
        def node(self, *args, **kwargs):
            raise RuntimeError("reached graph emission")

    prepared = prepared_source.prepare(TERMINAL)
    payload = recovery.terminal_word_payload(prepared)
    state = convert._State(StopOnGraphEmission(), keep_empty=False)
    with pytest.raises(RuntimeError, match="reached graph emission"):
        state.word(
            PoisonLegacyNode(), None, None,
            recovered=payload, recovered_source=prepared.original_bytes,
            recovered_prepared=prepared,
        )


def test_recovered_word_rejects_attribute_forgery_before_graph_emission():
    """Even a correct source body hash cannot authenticate substituted morphology."""
    prepared = prepared_source.prepare(TERMINAL)
    valid = recovery.terminal_word_payload(prepared)
    changed = dict(valid.attributes)
    changed["trans"] = "FORGED"
    changed["mrp1"] = "forged@fake@@ V@"
    forged = replace(valid, attributes=changed)
    state = convert._State(_RejectUnverifiedGraphWrites(), keep_empty=False)
    with pytest.raises(recovery.SignatureDrift, match="provenance|attributes|reviewed"):
        state.word(
            None, None, None, recovered=forged,
            recovered_source=prepared.original_bytes,
            recovered_prepared=prepared,
        )
