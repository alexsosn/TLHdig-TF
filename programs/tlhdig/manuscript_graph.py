"""Emit the Text-Fabric manuscript apparatus graph for issue #18.

The pure source grammar lives in :mod:`tlhdig.manuscripts`.  This module only maps
those source occurrences to TF nodes/edges.  Persisted ``joined`` orientation is the
source's left-to-right apparatus order; it is not a claim that a physical join is a
directed relation.  No reverse edge or transitive closure is synthesized.
"""
from __future__ import annotations

from collections import defaultdict

from . import lineref


CONFIDENT_KINDS = frozenset({"direct", "indirect"})


def _line_parts(siglum: str) -> tuple[str, ...]:
    """Expand a composite line siglum using the converter's established grammar."""
    return lineref.LineRef(raw="", frag=siglum).frags or (siglum,)


def _statement_reason(statement) -> str:
    """Return a stable diagnostic for an unresolved source statement."""
    reasons = []
    if statement.kind not in CONFIDENT_KINDS:
        reasons.append(f"non_confident_kind:{statement.kind}")
    if statement.left is None:
        reasons.append("missing_left")
    if statement.right is None:
        reasons.append("missing_right")
    return ";".join(reasons)


def emit(
    cv,
    apparatus,
    document,
    *,
    line_frag,
    line_extent,
    lines_with_slots,
    document_slots,
) -> None:
    """Emit fragment occurrences, witness resolution, join ledger, and join edges.

    ``apparatus`` is already source-ordered and endpoint-resolved by occurrence order.
    Every apparatus entry receives its own fragment node even when it has no siglum or
    line coverage.  A fragment without textual coverage is anchored to the document's
    first slot solely to keep the edge-bearing node alive in Text-Fabric.
    """
    if apparatus is None or not document_slots:
        return

    anchor = document_slots[0]

    # Line coverage is keyed by source siglum, but source occurrence identity is not.
    # Multiple entries may deliberately share one siglum and must remain distinct.
    line_slots: dict[str, set[int]] = defaultdict(set)
    line_rows: list[tuple[object, str]] = []
    for line_node, siglum in line_frag:
        extent = line_extent.get(line_node)
        if extent is None:
            continue
        for part in _line_parts(siglum):
            line_rows.append((line_node, part))
            line_slots[part].update(range(extent[0], extent[1] + 1))

    by_siglum: dict[str, list[object]] = defaultdict(list)
    by_order: dict[int, object] = {}
    slots_by_order: dict[int, set[int]] = {}

    for entry in apparatus.entries:
        covered = set(line_slots.get(entry.siglum, ())) if entry.siglum else set()
        node_slots = covered or {anchor}
        fn = cv.node("fragment", slots=node_slots)
        features = {
            "fragment_order": entry.order,
            "fragment_kind": entry.kind,
            "fragment_label": entry.label,
        }
        if entry.siglum:
            features["frag"] = entry.siglum
        if entry.siglum_source:
            features["siglum_source"] = entry.siglum_source
        if entry.siglum_raw:
            features["frag_raw"] = entry.siglum_raw
        if len(entry.siglum_raw_candidates) > 1:
            features["siglum_raw_candidates"] = " | ".join(entry.siglum_raw_candidates)
        if entry.siglum and entry.siglum in apparatus.duplicate_sigla:
            features["siglum_ambiguous"] = 1
        if len(entry.siglum_candidates) > 1:
            # A conflict must remain inspectable even though no candidate is promoted
            # to `frag`, otherwise graph output would erase the parser diagnostic.
            features["siglum_candidates"] = " | ".join(entry.siglum_candidates)
        if entry.kind == "txtpubl":
            features["txtpubl"] = entry.label
        elif entry.kind == "invnr":
            features["invnr"] = entry.label
        cv.feature(fn, **features)
        cv.terminate(fn)

        by_order[entry.order] = fn
        slots_by_order[entry.order] = node_slots
        if entry.siglum:
            by_siglum[entry.siglum].append(fn)

    # Keep the historical unvalued witness edge for compatibility and add an explicit
    # valued resolution edge so duplicate source sigla cannot be mistaken for certainty.
    # Composite line sigla are split before lookup exactly as in the old converter.
    emitted_witness = set()
    for line_node, part in line_rows:
        if line_node not in lines_with_slots:
            continue
        targets = by_siglum.get(part, ())
        if not targets:
            continue
        resolution = "unique" if len(targets) == 1 else "ambiguous"
        for fn in targets:
            pair = (line_node, fn)
            if pair in emitted_witness:
                continue
            emitted_witness.add(pair)
            cv.edge(line_node, fn, witness=None)
            cv.edge(line_node, fn, witness_resolution=resolution)

    # The joinstmt layer is the authoritative one-node-per-source-statement ledger.
    # It retains multiplicity and unresolved statements that a fragment->fragment edge
    # cannot represent.
    for statement in apparatus.statements:
        left = by_order.get(statement.left) if statement.left is not None else None
        right = by_order.get(statement.right) if statement.right is not None else None
        statement_anchor = anchor
        if statement.left is not None and statement.left in slots_by_order:
            statement_anchor = min(slots_by_order[statement.left])
        elif statement.right is not None and statement.right in slots_by_order:
            statement_anchor = min(slots_by_order[statement.right])

        sn = cv.node("joinstmt", slots={statement_anchor})
        values = {
            "join_order": statement.order,
            "join_kind": statement.kind,
            "join_encoding": statement.encoding,
            "join_raw": statement.raw,
            "join_resolved": 1 if statement.resolved and left is not None and right is not None else 0,
        }
        if not values["join_resolved"]:
            reason = _statement_reason(statement)
            if reason:
                values["join_reason"] = reason
        cv.feature(sn, **values)
        cv.terminate(sn)
        if left is not None:
            cv.edge(sn, left, joinLeft=None)
        if right is not None:
            cv.edge(sn, right, joinRight=None)
        cv.edge(sn, document, joinDocument=None)

    # `joined` is a convenience projection only.  Multiple same-kind source statements
    # collapse to one edge; conflicting confident statements suppress the projection.
    support: dict[tuple[int, int], set[str]] = defaultdict(set)
    for statement in apparatus.statements:
        if not statement.resolved or statement.kind not in CONFIDENT_KINDS:
            continue
        if statement.left is None or statement.right is None:
            continue
        support[(statement.left, statement.right)].add(statement.kind)

    for (left_order, right_order), kinds in support.items():
        if len(kinds) != 1:
            continue
        left = by_order.get(left_order)
        right = by_order.get(right_order)
        if left is None or right is None:
            continue
        cv.edge(left, right, joined=next(iter(kinds)))
