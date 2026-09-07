# Agent instructions

Before changing Text-Fabric serialization or node anchoring, read `docs/architecture/ADR-0001-empty-slots-not-sidecars.md`.

## Zero-span TF invariant

A source entity that belongs to the textual sequence but has no ordinary semantic slot remains inside Text-Fabric through an explicit empty/synthetic slot. Do not invent a sidecar solely to satisfy the TF `oslots` invariant.

- Distinguish semantic/source slots, synthetic empty slots, and total TF slots in reports and tests.
- Reuse descendant anchors for ancestors; do not create redundant empty slots per container.
- Never borrow a neighbouring real slot for an independently positioned textual entity.
- Never fabricate visible source content for an empty slot.
- Non-textual metadata/provenance abstractions may use documented technical anchors when required, but those anchors are not textual content.
- A sidecar for textual zero-span nodes is an architectural deviation and requires a corpus-specific ADR plus independent review.

Apply the repository's normal research → plan → TDD → test → independent-review gates to any implementation of this rule.
