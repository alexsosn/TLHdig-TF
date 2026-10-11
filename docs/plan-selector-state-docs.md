# Plan: document selector state without inventing validation status

Issue: #94. Research basis: `docs/research-annotation-status.md` and `docs/plan-annotation-status.md` from completed #79.

Status: frozen before public-documentation changes.

## Goal

Make the current researcher manual explain the word-level `mrpsel` / `mrpsel_kind` contract precisely enough to use it without mistaking source disambiguation for HFR workflow validation status.

This is documentation-only. It does not change converter, schema, artifact, app colours, or the already-researched decision not to infer a validation-stage feature.

## Required public semantics

`docs/morphology.md` remains the single manual owner for this material and must distinguish:

- missing/blank `mrp0sel` → `mrpsel_kind=none`: no source selector is supplied;
- numeric selectors such as `1`, `1a`, `1bR`, including multiple numeric tokens → `mrpsel_kind=analysis`: source candidate/alternative selection mechanics, not a validation label;
- `???` → `mrpsel_kind=unknown`: unresolved selector state; a following numeric token may be preserved as a fallback hint without changing the `unknown` kind;
- `DEL` → `mrpsel_kind=DEL`: source deletion/special selector state, not an analysis candidate index;
- language-special selectors `AKK`, `HURR`, `HAT`, `SUM`, `LUW` → their corresponding `mrpsel_kind` values;
- special selector + numeric forms may retain numeric selection detail while the special kind remains authoritative for the selector class.

The page must explicitly say that these values describe local source selection/disambiguation. A numeric selector alone is not proof that the live HFR UI would label the word pre-validated; header `<annot>` events are not word-level validation state.

Link the frozen #79 research for the authoritative HFR automatic → manual pre-validation → full validation workflow and live grey/magenta evidence rather than copying volatile corpus counts.

## RED gate

Before editing `docs/morphology.md`, add one focused documentation regression that requires the selector section to name all current `mrpsel_kind` classes and the concrete source cases above, including `???` fallback and the explicit selector-vs-validation warning.

The current manual is expected to fail this test because it states the high-level boundary but does not explain the individual selector cases.

## Implementation

Expand only the selector-state section of `docs/morphology.md` and link the existing frozen research. Do not add a second standalone manual page, UI styling, or schema feature.

Avoid claiming undocumented semantics for language/deletion markers beyond their source selector class. `sel_base`, `sel_clitic`, `sel_group`, and multi-selector behavior may be mentioned only to explain preserved selection detail already implemented by `morph.parse_selection()`.

## GREEN / review

Require targeted docs test, full unit suite/ordinary CI, existing documentation checker, and logically independent adversarial review focused on:

- numeric selector accidentally being called validation status;
- `???` + numeric fallback being described as resolved;
- language/deletion selectors being presented as morphological analyses;
- header `<annot>` being used as word-level validation evidence;
- HFR workflow semantics being generalized beyond the evidence;
- duplicated/stale corpus counts or competing prose sources of truth.

No current TF artifact or `BUILD-MANIFEST.json` refresh is required because this lane changes documentation/tests only.