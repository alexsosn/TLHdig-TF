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

### 2. Header attribute declarations are element-qualified and namespace-sensitive

Add an explicit mapping of `(element, attribute)` pairs to disposition rather than one global attribute allowlist.

For represented edit events, the current converter semantics remain exactly the existing `_EDIT_ATTRS`: the ten attributes it copies to edit-node features. Because not every edit kind necessarily carries every attribute in the pinned corpus, the declaration table describes the **observed** source pairs, not an unrestricted cross product.

Known currently dropped pairs (for example `annot@data`) receive `known-unpreserved` and stay visible in the report.

Header names preserve Clark-notation namespaces. Body names retain the historical local-name normalization needed for existing AO-prefixed body markup. This means a future namespaced header field cannot impersonate an already-declared unqualified field.

### 3. Converter declaration drift is a hard regression failure

`tags.py` exposes the canonical Contract-B declarations for edit kinds and consumed edit attributes. The current converter retains its private compatibility constants to avoid an otherwise unnecessary production-code refactor in this validator-only ticket, but tests require those constants to equal the Contract-B declarations exactly.

This gives the intended safety property: any future converter edit-kind/attribute change that is not reflected in Contract B fails CI. It also keeps converter behavior byte/value-identical and avoids touching TF generation logic in a no-artifact-change ticket.

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

Known explicitly declared `known-unpreserved` items do **not** make this ticket's gate fail, because this ticket owns the detection contract while sibling header-provenance work owns the data-model repair. They must be printed/reported separately so a green Contract B means “every source construct has an explicit disposition,” not “nothing is lost.”

The report must state that distinction prominently.

### 6. Report layout

`reports/tags.md` is generated with separate regions:

1. Body `<text>` element inventory, preserving the existing destination sections/counts.
2. `AOHeader` element inventory by header disposition.
3. `AOHeader` attribute-pair inventory by disposition.
4. Explicit current-loss counts for `known-unpreserved` and `malformed-unpreserved`.

This makes body raw-preservation and header known-loss semantics visually impossible to conflate.

## TDD sequence

### RED 1 — declaration semantics

Before production changes, add tests asserting APIs that do not exist on current main:

- unknown header element is reported;
- unknown header attribute pair is reported;
- `mDocID` is explicitly `known-unpreserved`, not `raw`;
- `annot@data` is explicitly `known-unpreserved`;
- converter edit kinds/consumed attrs cannot diverge from the Contract-B declarations.

Expected RED: failures due to missing header declaration APIs/constants.

### RED 2 — inventory/report semantics

Add fixture tests with a minimal AOxml document containing body + header data and assert:

- body/header are inventoried separately;
- attributes are element-qualified;
- a new attribute on known `annot` is detected;
- rendered report has separate Body/Header sections and visibly labels known-unpreserved items.

Expected RED: current `check_tags.py` has no testable header inventory/report helpers.

### Adversarial RED — namespace collision

Independent review must test whether a namespaced future header field can collapse onto a declared local name. A fixture using `x:data` beside ordinary `data` must retain `{namespace}data` as a distinct Contract-B key and fail unless explicitly declared.

### GREEN

Implement the smallest `tags.py` and `check_tags.py` changes required to satisfy the RED contracts. Preserve converter graph semantics and TF artifact bytes.

## Tests / gates

Run at minimum:

- `programs/tests/test_tags.py` plus the header Contract-B tests;
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
- whether sibling header-provenance scope was accidentally implemented here.

Any blocking finding requires another RED/fix/test/review cycle before merge.

## Acceptance

The ticket is complete only when Contract B covers all observed body/header element names and all observed header element/attribute pairs, unknown additions fail deterministically, namespace changes remain visible, known header loss is explicit rather than hidden, the TF artifact is unchanged, CI is green, and the final adversarial review is clean.
