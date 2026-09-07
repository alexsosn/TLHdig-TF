"""Emit the Text-Fabric manuscript apparatus graph for issue #18.

The pure source grammar lives in :mod:`tlhdig.manuscripts`. This module only maps
source occurrences to TF nodes/edges. Persisted ``joined`` orientation is the source's
left-to-right apparatus order; it is not a claim that a physical join is directed.
No reverse edge or transitive closure is synthesized.
"""
from __future__ import annotations

from collections import defaultdict

from . import lineref


CONFIDENT_KINDS = frozenset({"direct", "indirect"})


def _normalise_siglum(raw: str) -> str:
    """Apply the source siglum normalisation used by manuscript entry lookup."""
    value = " ".join((raw or "").split())
    if value.startswith("€"):
        return "€" + "".join(value[1:].split())
    return value


def _line_parts(siglum: str) -> tuple[str, ...]:
    """Expand a composite line siglum and normalize each source lookup key."""
    parts = lineref.LineRef(raw="", frag=siglum).frags or (siglum,)
    return tuple(_normalise_siglum(part) for part in parts)


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
    document_apparatus,
    document,
    *,
    line_frag,
    line_extent,
    lines_with_slots,
    line_block,
    document_slots,
) -> None:
    """Emit every apparatus block, with block-scoped witnesses and join projection.

    Fragment and join-statement order are block-local source occurrence identities.
    Lines resolve only against the most recent preceding ``Manuscripts`` block supplied
    by :func:`manuscripts.parse_document`. All blocks remain ledgered, including blocks
    before ``text`` and trailing blocks that witness no line.
    """
    if document_apparatus is None or not document_slots:
        return

    anchor = document_slots[0]

    # Source line coverage is block-scoped. Reusing A1/€1 in another apparatus block
    # does not create ambiguity and must not enlarge this block's fragment extent.
    line_slots: dict[tuple[int, str], set[int]] = defaultdict(set)
    line_rows: list[tuple[object, int, str]] = []
    for line_node, siglum in line_frag:
        block_order = line_block.get(line_node)
        if block_order is None:
            continue
        extent = line_extent.get(line_node)
        if extent is None:
            continue
        for part in _line_parts(siglum):
            line_rows.append((line_node, block_order, part))
            line_slots[(block_order, part)].update(range(extent[0], extent[1] + 1))

    by_block_order: dict[tuple[int, int], object] = {}
    by_block_siglum: dict[tuple[int, str], list[object]] = defaultdict(list)
    slots_by_block_order: dict[tuple[int, int], set[int]] = {}

    for block in document_apparatus.blocks:
        apparatus = block.apparatus
        for entry in apparatus.entries:
            covered = (
                set(line_slots.get((block.order, entry.siglum), ()))
                if entry.siglum else set()
            )
            node_slots = covered or {anchor}
            fn = cv.node("fragment", slots=node_slots)
            features = {
                "manuscript_block": block.order,
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
                features["siglum_candidates"] = " | ".join(entry.siglum_candidates)
            if entry.kind == "txtpubl":
                features["txtpubl"] = entry.label
            elif entry.kind == "invnr":
                features["invnr"] = entry.label
            cv.feature(fn, **features)
            cv.terminate(fn)

            key = (block.order, entry.order)
            by_block_order[key] = fn
            slots_by_block_order[key] = node_slots
            if entry.siglum:
                by_block_siglum[(block.order, entry.siglum)].append(fn)

    # Historical unvalued witness remains for compatibility. The valued companion says
    # whether the block-local source siglum selects one or several occurrences.
    emitted_witness = set()
    for line_node, block_order, part in line_rows:
        if line_node not in lines_with_slots:
            continue
        targets = by_block_siglum.get((block_order, part), ())
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

    # Authoritative one-node-per-source-statement ledger. Multiplicity and unresolved
    # records survive even when a fragment->fragment convenience edge cannot represent
    # them. Orders and endpoints never cross apparatus-block boundaries.
    for block in document_apparatus.blocks:
        apparatus = block.apparatus
        for statement in apparatus.statements:
            left_key = (block.order, statement.left) if statement.left is not None else None
            right_key = (block.order, statement.right) if statement.right is not None else None
            left = by_block_order.get(left_key) if left_key is not None else None
            right = by_block_order.get(right_key) if right_key is not None else None

            statement_anchor = anchor
            if left_key is not None and left_key in slots_by_block_order:
                statement_anchor = min(slots_by_block_order[left_key])
            elif right_key is not None and right_key in slots_by_block_order:
                statement_anchor = min(slots_by_block_order[right_key])

            sn = cv.node("joinstmt", slots={statement_anchor})
            values = {
                "manuscript_block": block.order,
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

        # Convenience projection is independently derived inside this block only.
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
            left = by_block_order.get((block.order, left_order))
            right = by_block_order.get((block.order, right_order))
            if left is None or right is None:
                continue
            cv.edge(left, right, joined=next(iter(kinds)))
