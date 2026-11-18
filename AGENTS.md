# Agent instructions

> **Autonomous-development policy:** Before selecting or inventing work, read [PRODUCT_GOALS.md](PRODUCT_GOALS.md) and [docs/agentic-development-policy.md](docs/agentic-development-policy.md). State the targeted researcher journey, observed blocker, minimal reuse-first solution and real-data/public-interface acceptance criterion. Follow proportional research → plan → TDD → test → logically independent adversarial review. Preserve all more specific source, editorial, safety and release requirements below.

> **Product-goal gate:** Before selecting a task or expanding the backlog, read [PRODUCT_GOALS.md](PRODUCT_GOALS.md). Prioritize its researcher journeys and minimum usable release; require concrete evidence for infrastructure work. Keep all mandatory source, security, licensing, TDD and independent-review checks below.

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
