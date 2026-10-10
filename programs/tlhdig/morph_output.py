"""Verify loaded Text-Fabric morphology against reviewed lexical source attributes.

#150 recovered documents: a source-opening audit and lexical input check do
not prove that the TF writer persisted every mrpN analysis, optional field or
valued selection edge correctly. This audit consumes separately authenticated
attributes and compares a *loaded* graph, after TF serialization.

This is deliberately not an independent implementation of TLHdig's complete
mrp grammar: morph.analyses/parse_selection are still the canonical parser.
Source authentication is the caller's responsibility; the audit's independent
boundary is the emitted on-disk TF representation.
"""
from __future__ import annotations

import re
from collections.abc import Mapping

from . import morph


class MorphOutputMismatch(ValueError):
    """Source-derived morphology differs from the actually loaded TF graph."""


def _require_equal(field: str, actual, expected, *, index: int | None = None) -> None:
    if actual != expected:
        context = f" analysis {index}" if index is not None else " word"
        raise MorphOutputMismatch(
            f"{field}{context}: loaded TF {actual!r} != source-derived {expected!r}"
        )


def _optional(api, features: set[str], name: str, node: int):
    """Absent optional TF feature files represent an empty field, not a failure."""
    return getattr(api.F, name).v(node) if name in features else None


def _selection_tokens(raw: str | None) -> dict[int, str]:
    """Extract valued edges from the literal source selector tokens.

    This does not call the writer's `chosen` calculation or share a precomputed
    edge map with the converter. Grammar classification (including ???+0a)
    remains with the canonical selection parser below.
    """
    chosen: dict[int, str] = {}
    for token in (raw or "").split():
        match = re.fullmatch(r"(\d+)[A-Za-z]*", token)
        if match is None:
            continue
        index = int(match.group(1))
        chosen[index] = " ".join((*chosen.get(index, "").split(), token))
    return chosen


def assert_word_output(api, word_node: int, source_attributes: Mapping[str, str]) -> None:
    """Require candidate-by-candidate parity of a loaded word and source mrpN.

    The caller must supply a lexical-word witness authenticated to immutable
    source + reviewed mechanical edits, *not* attributes read back from the
    historical fully-repaired lxml tree. Layout-only source morphology is a
    known separate loss (#105), so the audit must fail rather than certify it.
    """
    features = set(api.Fall())
    kind = api.F.otype.v(word_node)
    candidates = morph.analyses(dict(source_attributes))
    if kind == "layout":
        if candidates or source_attributes.get("mrp0sel", "").strip():
            raise MorphOutputMismatch(
                "layout: original morphology/selection has no analysis TF graph"
            )
        _require_equal("layout analyses", tuple(api.E.analyses.f(word_node)), ())
        _require_equal("layout selected", tuple(api.E.selected.f(word_node)), ())
        return
    if kind != "word":
        raise MorphOutputMismatch(f"expected word or layout, got {kind!r}")

    actual_nodes = tuple(api.E.analyses.f(word_node))
    _require_equal("nanalyses", api.F.nanalyses.v(word_node), len(candidates))
    _require_equal("analyses edges", len(actual_nodes), len(candidates))
    actual_indices = tuple(api.F.index.v(n) for n in actual_nodes)
    expected_indices = tuple(a.index for a in candidates)
    _require_equal("candidate index/order", actual_indices, expected_indices)
    if len(set(actual_indices)) != len(actual_indices):
        raise MorphOutputMismatch("duplicated candidate index in loaded graph")

    selection_raw = source_attributes.get("mrp0sel")
    selection = morph.parse_selection(selection_raw)
    chosen = _selection_tokens(selection_raw)
    # The scalar count is indexed by all numeric source tokens, including
    # fallback hints after an unresolved marker; graph edges themselves are
    # only emitted when selection.kind == 'analysis'.
    _require_equal("mrpsel", api.F.mrpsel.v(word_node) or "", selection.raw.strip())
    _require_equal("mrpsel_kind", api.F.mrpsel_kind.v(word_node), selection.kind)
    _require_equal("nselected", api.F.nselected.v(word_node), len(chosen))
    for name, value in (
        ("sel_base", selection.base_alt),
        ("sel_clitic", selection.clitic_alt),
        ("sel_group", selection.group),
    ):
        _require_equal(name, _optional(api, features, name, word_node) or "", value)

    for source, node in zip(candidates, actual_nodes):
        raw = source.raw if not source.ok or source.normalised else ""
        expected = {
            "index": source.index,
            "sep": source.sep.strip(),
            "parse_ok": 1 if source.ok else 0,
            "lemma": source.base.lemma,
            "gloss": source.base.gloss,
            "morph": source.base.morph,
            "stemclass_raw": source.base.stemclass,
            "field4_kind": source.field4_kind,
            "det_hint": source.base.det,
            "mrp_control": source.control,
            "raw": raw,
            "pos": source.pos if source.field4_kind == "pos" else "",
            "stemclass": (
                source.base.stemclass.strip()
                if source.field4_kind == "stemclass" else ""
            ),
            "clitic_lemma": source.clitic.lemma if source.clitic else "",
            "clitic_morph": source.clitic.morph if source.clitic else "",
            "clitic_stemclass": source.clitic.stemclass if source.clitic else "",
            "clitic_det": source.clitic.det if source.clitic else "",
        }
        for name, value in expected.items():
            got = _optional(api, features, name, node)
            # Empty strings are omitted or represented by an empty value
            # depending on whether other nodes in the graph populate feature.
            if isinstance(value, str):
                got = got or ""
            _require_equal(name, got, value, index=source.index)

    expected_selected = chosen if selection.kind == "analysis" else {}
    # Text-Fabric's valued EdgeFeature.f() returns (destination, value)
    # pairs, not destination IDs and not an EdgeFeature.v() accessor.
    # It is essential to audit the *stored edge values* rather than only
    # their count/targets.
    actual_selected_pairs = tuple(api.E.selected.f(word_node))
    # An analysis index is only meaningful *within its word*. Two distinct
    # source words may both have mrp1 and selector "1": checking index and
    # value alone accepts a cross-word selected edge that silently changes
    # the TF morphological interpretation.
    own_analyses = set(actual_nodes)
    for target, _value in actual_selected_pairs:
        if target not in own_analyses:
            raise MorphOutputMismatch(
                f"selected edge target {target} is not this word's own analysis"
            )
    actual_selected_indices = tuple(api.F.index.v(n) for n, _ in actual_selected_pairs)
    _require_equal(
        "selected edge targets", set(actual_selected_indices),
        set(expected_selected),
    )
    if len(actual_selected_pairs) != len(expected_selected):
        raise MorphOutputMismatch("selected edges contain a duplicate or extra target")
    for node, edge_value in actual_selected_pairs:
        index = api.F.index.v(node)
        _require_equal(
            "selected edge value", edge_value,
            expected_selected[index], index=index,
        )
