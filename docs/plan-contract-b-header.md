# Plan: extend Contract B to `AOHeader`

Issue: #56

Research: `docs/research-contract-b-header.md`

## Goal

Make Contract B cover both source regions that affect conversion:

- body markup under `<text>`;
- document metadata under `<AOHeader>`.

The gate must detect new header element names and new header attributes without falsely claiming that currently dropped header data is preserved.

## Non-goals

- no document-header provenance feature;
- no `srcxml`/`src_span` on documents;
- no `mDocID` modelling or join-graph changes;
- no `docid_raw` redesign;
- no TF feature/node/edge changes;
- no TF version bump.

Those remain owned by #57/#58.

## Design

### 1. Separate body and header declaration tables

Keep the existing body declaration contract (`DESTINATION`, `KINDS`) and add explicit header declarations in `programs/tlhdig/tags.py`.

Header element dispositions:

- `structure` — header/container syntax recognized by the converter;
- `document-feature` — consumed directly into a document feature (`docID` today);
- `edit` — represented as an `edit` node by the converter;
- `known-unpreserved` — present in the pinned source but currently dropped; this status is a visible debt and must never be treated as `raw`/preserved;
- `malformed-unpreserved` — known source typo currently dropped.

`known-unpreserved`/`malformed-unpreserved` are accepted only for explicitly declared current names and are linked in comments/docs to #57/#58. A new element cannot inherit them by default.

### 2. Header attribute declarations are element-qualified

Add an explicit mapping of `(element, attribute)` pairs to disposition rather than one global attribute allowlist.

For represented edit events, the current converter semantics remain exactly the existing `_EDIT_ATTRS`: the ten attributes it copies to edit-node features. Because not every edit kind necessarily carries every attribute in the pinned corpus, the declaration table should describe the **observed** source pairs, not generate an unrestricted cross product.

Known currently dropped pairs (for example `annot@data`) receive `known-unpreserved` and stay visible in the report.

### 3. One source of truth for converter edit kinds/consumed attributes

Move or expose the canonical edit-kind and consumed-attribute declarations from `tags.py` and have `convert.py` import them. This prevents a future converter change from silently diverging from Contract B.

The converter's behavior must remain byte/value-identical: this is a declaration-source refactor only.

### 4. Checker inventory API

Refactor `programs/check_tags.py` so inventory logic is testable without executing a full corpus scan. Add helpers that, given a parsed root, return:

- body element counts;
- header element counts;
- header `(element, attribute)` counts.

`main()` still applies repaired source bytes exactly as today and aggregates these per-document inventories.

### 5. Failure semantics

The gate fails if any of these exist:

- undeclared body element;
- undeclared header element;
- undeclared header element/attribute pair.

Known explicitly declared `known-unpreserved` items do **not** make this ticket's gate fail, because #56 is the detection contract and #57/#58 own the data-model repair. They must be printed/reported separately so a green Contract B means “every source construct has an explicit disposition,” not “nothing is lost.”

The report must state that distinction prominently.

### 6. Report layout

`reports/tags.md` becomes regioned:

1. Body `<text>` element inventory, preserving the existing destination sections/counts.
2. `AOHeader` element inventory by header disposition.
3. `AOHeader` attribute-pair inventory by disposition.
4. Explicit summary counts for `known-unpreserved` and `malformed-unpreserved`, with links to #57/#58 in explanatory prose.

This makes body raw-preservation and header known-loss semantics visually impossible to conflate.

## TDD sequence

### RED 1 — declaration semantics

Before production changes, add tests asserting APIs that do not exist on current main:

- unknown header element is reported;
- unknown header attribute pair is reported;
- `mDocID` is explicitly `known-unpreserved`, not `raw`;
- `annot@data` is explicitly `known-unpreserved`;
- all converter edit kinds/consumed attrs come from the Contract-B declaration module.

Expected RED: failures due to missing header declaration APIs/constants.

### RED 2 — inventory/report semantics

Add fixture tests with a minimal AOxml document containing body + header data and assert:

- body/header are inventoried separately;
- attributes are element-qualified;
- a new attribute on known `annot` is detected;
- rendered report has separate Body/Header sections and visibly labels known-unpreserved items.

Expected RED: current `check_tags.py` has no testable header inventory/report helpers.

### GREEN

Implement the smallest `tags.py`, `convert.py`, and `check_tags.py` changes required to satisfy RED. Do not touch TF generation semantics.

## Tests / gates

Run at minimum:

- `programs/tests/test_tags.py` plus new header Contract-B tests;
- full unit/adversarial suite;
- `python programs/check_tags.py` on the repaired corpus;
- normal CI gates;
- release certification/regression checks sufficient to prove the committed `tf/0.3.0` module digest remains `sha256:93790f9e283c3c3d29d8a751b1eecbb7fd908745470aa36b9cec0525b90182d1` and no `.tf` file changed.

## Independent adversarial review

A fresh review context must challenge:

- whether `known-unpreserved` is being used as a generic escape hatch;
- whether new attributes can slip through on a known element;
- whether namespace/local-name handling creates collisions;
- whether the converter and declarations can still drift;
- whether report wording could be read as claiming header preservation;
- whether any TF artifact byte changed despite the no-artifact-change contract;
- whether #57/#58 scope was accidentally implemented here.

Any blocking finding requires another RED/fix/test/review cycle before merge.

## Acceptance

The ticket is complete only when Contract B covers all observed body/header element names and all observed header element/attribute pairs, unknown additions fail deterministically, known header loss is explicit rather than hidden, the TF artifact is unchanged, CI is green, and the final adversarial review is clean.
