# ADR-0001: Represent zero-span textual entities with explicit empty slots

Status: Accepted

## Decision

Text-Fabric corpora in this project family MUST represent source entities that belong to the textual graph but have no ordinary semantic slot by introducing an explicit empty/synthetic slot inside the Text-Fabric warp.

Do not move such entities into a sidecar merely because Text-Fabric requires every non-slot node to span at least one slot.

An empty slot is a technical positional anchor, not an assertion that a real grapheme/sign/token exists in the source.

## Required modelling contract

1. Keep the corpus's normal TF slot type; mark empty anchors explicitly (`type=empty` and/or `synthetic=1`).
2. Reports distinguish semantic/source slots, synthetic empty slots, and total TF slots.
3. Empty words receive an empty slot at their textual position.
4. Empty lines/containers receive an empty slot only if no descendant already supplies an anchor.
5. A wholly empty document receives an empty slot only if it would otherwise have no slot.
6. Ancestors span descendant empty slots through normal `oslots`; do not make redundant slots per ancestor.
7. Never borrow a neighbouring real slot and never fabricate visible source content.
8. Sidecars remain appropriate only for genuinely non-textual data; zero span alone is not sufficient justification.

## Precedent

This follows established Text-Fabric practice. ETCBC/DSS creates explicit empty slots for otherwise signless words/vacat clusters. The Nino-cunei `tfFromAtf` converter used by Old Babylonian / Old Assyrian creates `cv.slot()` anchors for otherwise-empty lines and documents.

## Agent rule

Autonomous agents MUST apply this ADR by default before proposing new serialization for zero-span nodes. A sidecar proposal for textual zero-span entities is an architectural deviation and requires a corpus-specific ADR explaining why empty-slot anchoring is semantically invalid.

## Tests

Pin deterministic empty anchors, semantic-vs-total slot counts, normal TF reachability, no borrowed real slots, no fabricated visible content, and empty word/line/document plus mixed cases.
