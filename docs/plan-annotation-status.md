# Plan: annotation-status disposition

Issue: #79

Date: 2026-09-09

Research prerequisite: `docs/research-annotation-status.md`.

## Selected outcome

**Do not add a corpus feature or browser colour for HFR annotation validation status from TLHdig 0.3 XML.**

The research establishes two different contracts that must remain separate:

- `mrp0sel` / TF `mrpsel` + `mrpsel_kind` describe source analysis **selection/disambiguation mechanics**;
- HFR's grey/magenta labels describe a broader annotation **workflow stage** (automatic vs manually pre-validated), with completion state also recorded in project status/overview material outside the per-word selector.

Conflating those contracts would visually assert stronger scholarly certainty than the distributed source proves.

## Scope of this ticket

#79 remains research-only. It will land:

1. the reproducible census script;
2. the frozen research conclusion;
3. this disposition plan.

It will not change:

- `programs/tlhdig/convert.py`;
- TF schema/features/edges;
- any immutable TF artifact;
- `app/app.py`, `app/config.yaml` or CSS;
- release policy/version;
- morphology-marker handling owned by #92.

No TDD production RED/GREEN phase is applicable because the selected outcome is explicitly **no production implementation**. The research script itself has already run successfully against the exact production-source population.

## Follow-up ownership

### #94 — documentation

Document the public meaning of:

- empty/missing selector;
- `???` / unknown selector;
- numeric selections and alternatives;
- deletion/language special selectors;
- `mrpsel` and `mrpsel_kind` as disambiguation state;
- the distinction between selector state and HFR validation workflow.

Coordinate this with #44 browser documentation and #46 comprehensive corpus documentation rather than creating competing prose sources of truth.

### #92 — morphology markers

Opaque leading circled/control glyphs in `mrpN` values are a separate source-fidelity/lexical-identity problem. They must be researched and fixed under their own immutable-artifact TDD lane.

### Future authoritative status export

If HFR publishes a versioned machine-readable validation-status export, create a new integration ticket. That ticket must establish:

- exact semantic unit (word / candidate / text / CTH);
- stable join key against TLHdig-TF record identity;
- coverage and duplicate/composite behavior;
- provenance/license/version contract;
- missing/unknown semantics;
- RED tests before any schema/UI change.

Do not silently reinterpret `mrpsel_kind` later.

## Finalization gates

Before merging #79:

1. remove the temporary research-only Actions workflow;
2. synchronize the branch with current `main` without rewriting research history;
3. run ordinary repository CI on the exact final head;
4. perform a logically independent adversarial research review that challenges at least:
   - numeric selector being mistaken for validation status;
   - HFR semantics generalized to non-HFR projects;
   - header `<annot>` history used as a token status proxy;
   - excluded/live-only examples treated as shipped-corpus evidence;
   - CSS colour reverse-engineered as a data contract;
   - external project status files assumed joinable when they are not distributed here;
   - useful selector semantics being hidden merely because validation status is unavailable;
   - #92 morphology-marker findings being smuggled into this ticket;
5. address any blocking review finding and repeat exact-head review if the head changes.

## Acceptance

- The repository records what HFR's validation-status display means.
- The repository records what the distributed XML/TF graph actually preserves.
- No unsupported validation-stage feature or UI styling is introduced.
- Researchers have a follow-up path to understand selector state (#94).
- The independently discovered morphology defect remains separately owned (#92).
- Final research PR is current-main compatible, CI-green and independently reviewed.