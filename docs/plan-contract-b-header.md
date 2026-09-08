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

### 3. Header declarations are an exact pinned-corpus snapshot

The header contract is bidirectional rather than an allowlist:

- any observed element or element/attribute pair without a declaration fails;
- any declaration that is not observed in the pinned repaired corpus also fails.

The second condition matters because otherwise a speculative declaration could sit dormant and silently authorize a future upstream field. `declaration_drift()` therefore compares observed and declared key sets in both directions.

The historical body contract remains one-way in this ticket; changing its semantics would be unrelated scope.

### 4. Converter declaration drift is a hard regression failure

`tags.py` exposes the canonical Contract-B declarations for edit kinds and consumed edit attributes. The current converter retains its private compatibility constants to avoid an otherwise unnecessary production-code refactor in this validator-only ticket, but tests require those constants to equal the Contract-B declarations exactly.

This gives the intended safety property: any future converter edit-kind/attribute change that is not reflected in Contract B fails CI. It also keeps converter behavior byte/value-identical and avoids touching TF generation logic in a no-artifact-change ticket.

### 5. Inventory every header block

`inventory_root()` inventories every direct `AOHeader` child of the AOxml root, not merely the first one. A malformed or future source containing a second sibling header must not be able to hide undeclared metadata behind a valid first header.

Restricting enumeration to direct header children avoids double-counting descendants if malformed input nests an `AOHeader` inside another header; the outer header traversal still sees that nested construct once and the declaration contract can reject it if its qualified name is new.

### 6. Checker inventory API

`programs/check_tags.py` exposes testable inventory helpers returning:

- body element counts;
- header element counts;
- header `(element, attribute)` counts.

`main()` applies repaired source bytes exactly as before and aggregates these per-document inventories.

### 7. Failure semantics

The gate fails if any of these exist:

- undeclared body element;
- undeclared header element;
- declared-but-unobserved header element;
- undeclared header element/attribute pair;
- declared-but-unobserved header element/attribute pair.

Known explicitly declared `known-unpreserved` items do **not** make this ticket's gate fail, because this ticket owns the detection contract while sibling header-provenance work owns the data-model repair. They must be printed/reported separately so a green Contract B means “every source construct has an explicit disposition,” not “nothing is lost.”

### 8. Generated report is user-facing evidence and CI-locked

`reports/tags.md` is generated with separate regions:

1. Body `<text>` element inventory, preserving the existing destination sections/counts.
2. `AOHeader` element inventory by header disposition.
3. `AOHeader` attribute-pair inventory by disposition.
4. Explicit current-loss counts for `known-unpreserved` and `malformed-unpreserved`.

The normal CI Contract-B step regenerates the report and then runs:

```bash
git diff --exit-code -- reports/tags.md
```

so the committed inventory cannot silently lag behind the checker or repaired corpus. This makes body raw-preservation and header known-loss semantics visually impossible to conflate and keeps the visible evidence reproducible.

## TDD / adversarial sequence

### RED 1 — declaration and inventory semantics

Before production changes, tests require APIs absent on main for:

- unknown header element detection;
- unknown element-qualified header attribute detection;
- explicit `known-unpreserved` rather than `raw` for `mDocID` and `annot@data`;
- separate body/header/attribute inventories;
- converter declaration synchronization;
- visibly separate report sections.

Hosted result: seven intended failures while the existing suite remained green.

### Corpus-assisted RED — exact observed attribute snapshot

The first implementation intentionally declared only a few attribute pairs. Hosted corpus CI passed the unit suite and preceding corpus gates, then Contract B enumerated the remaining observed pairs. The final declaration table is therefore derived from the repaired pinned corpus rather than an unrestricted cross product.

### Adversarial RED — namespace collision

A fixture using `x:data` beside ordinary `data` proved that local-name normalization could collapse a future namespaced header field onto an existing declaration. The RED failed before header normalization was made namespace-sensitive; a companion element test protects the same boundary.

### Adversarial RED — dormant speculative declaration

A set-comparison fixture requires both missing declarations and declared-but-unobserved entries to be reported. This prevents declarations from becoming future escape hatches.

### Adversarial RED — second sibling header

A fixture with two direct `AOHeader` blocks requires both blocks, including unknown metadata in the second, to be inventoried. The pre-fix implementation failed because it selected only the first header.

### Adversarial RED — committed report drift

CI intentionally regenerated `reports/tags.md` and failed `git diff --exit-code` against the old body-only report. That run supplied the exact source-derived replacement; the final workflow keeps the drift check without diagnostic `cat` output.

## Tests / gates

The final candidate must pass:

- the full unit/adversarial suite;
- corpus identity and repair-manifest verification;
- sign round-trip and morphology gates;
- app and generated-feature-doc checks;
- full build-stamp verification against the current base artifact digest;
- Contract B plus report-drift verification;
- provenance split;
- cuneiform alignment;
- locked external sign-reference fetch/validation.

The PR changes no file under `tf/` or `tf-provenance/`, so the shipped artifact must remain byte-identical to the base branch. Do not hard-code an earlier digest here: concurrent certified main updates have already changed the current base stamp since the original research was written, and the final merge candidate is checked against its actual base.

## Independent adversarial review

A fresh review context on the exact final head must challenge:

- whether `known-unpreserved` is being used as a generic escape hatch;
- whether new attributes can slip through on a known element;
- whether dormant declarations pre-authorize future fields;
- whether namespace/local-name handling creates collisions;
- whether multiple header blocks can hide content;
- whether the converter and declarations can drift;
- whether the committed report matches generator output and wording could be read as claiming header preservation;
- whether any TF artifact byte changed despite the no-artifact-change contract;
- whether sibling header-provenance scope was accidentally implemented here.

Any blocking finding requires another RED/fix/test/review cycle before merge.

## Acceptance

The ticket is complete only when Contract B covers all observed body/header element names and all observed header element/attribute pairs; header declarations are an exact pinned-corpus snapshot; unknown additions, namespace changes, speculative declarations and extra header blocks fail deterministically; known header loss is explicit rather than hidden; the committed inventory is reproducibly synchronized; TF artifacts are unchanged; full CI is green; and the final adversarial review is clean.
