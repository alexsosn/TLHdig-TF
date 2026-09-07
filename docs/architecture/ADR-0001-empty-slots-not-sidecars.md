# ADR-0001: Represent zero-span textual entities with explicit empty slots

Status: Accepted  
Scope: project-family Text-Fabric architecture

## Decision

A source entity that **belongs to the textual sequence** and has an independent source position/order but no ordinary semantic slot MUST remain inside the Text-Fabric warp through an explicit empty/synthetic slot.

Do not move textual zero-span entities into a sidecar merely because Text-Fabric requires every non-slot node to span at least one slot. The empty slot is a technical positional anchor, not an assertion that a real grapheme, cuneiform sign, character, or word exists in the source.

## Scope boundary

- Textual zero-span entities with their own source position/order get an explicit empty/synthetic slot.
- Ancestor/container nodes reuse descendant slots, including descendant empty slots; do not create one synthetic slot per ancestor.
- Genuinely non-textual nodes with no independent textual position (for example lexeme abstractions, metadata, provenance, resources) should anchor through their occurrence/locus or a documented O(1) technical anchor when required. That anchor must not be presented as textual content.
- Sidecars are for data genuinely outside the TF graph/API contract. **Zero span alone is not sufficient reason for a sidecar.**

## Required modelling contract

1. Keep the corpus's normal TF slot type. In a cuneiform corpus whose slot type is `sign`, an empty positional anchor is technically a `sign` slot even though it is not a semantic cuneiform sign.
2. Mark empty anchors explicitly (`type=empty`, `is_gap=1`, and/or `synthetic=1`).
3. Reports distinguish semantic/source slots, synthetic empty slots, and total TF slots.
4. Empty words/textual units receive an empty slot at their source position.
5. Empty lines/containers receive an empty slot only if no descendant already supplies an anchor.
6. A wholly empty textual document receives an empty slot only if it would otherwise have no slot.
7. Ancestors span descendant real/empty slots through normal `oslots`.
8. Never borrow a neighbouring real slot for an independently positioned textual entity.
9. Never fabricate visible Unicode/sign/token/lexical content for an empty anchor.
10. Non-textual technical anchors must be documented and must not leak into APIs as fabricated content.

## Precedent

- ETCBC/DSS creates empty slots for words with no glyphs and for vacat/other clusters with no signs to anchor them in the text sequence.
- Nino-cunei `tfFromAtf`, used by Old Babylonian / Old Assyrian, creates `cv.slot()` anchors for otherwise-empty textual lines and documents.

The reusable principle is: **empty slots preserve textual position; they do not fabricate philological content.**

## Agent rule

Autonomous implementation/review agents MUST treat this ADR as the default architecture. Before proposing a zero-span sidecar, classify the object as textual, non-textual-but-in-graph, or genuinely outside the TF graph. A sidecar proposal whose only justification is empty `oslots` is an architectural error. Deviating from this ADR requires a corpus-specific ADR and independent review.

## Tests

Pin deterministic/source-ordered empty anchors, semantic-vs-total slot counts, normal TF reachability, ancestor reuse, no borrowed real slots, no fabricated visible content, non-textual-anchor rendering behavior, and empty word/line/document plus mixed cases.
