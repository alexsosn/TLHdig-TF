# Plan: byte-exact document-header provenance

Issues: #57, #58, #10
Research: `docs/research-header-provenance.md`

## Goal

Make every emitted Text-Fabric `document` carry byte-exact provenance for its complete source `AOHeader` in the optional provenance module, extend Contract A to verify that graph→source correspondence, and retire the now-redundant core `docid_raw` feature without changing normalized `docid` behavior.

The hosted research baseline is exact: 23,884 / 23,884 emitted documents have a directly recoverable original `AOHeader` span, with zero current repair-induced header changes or coordinate shifts.

## Concurrency / version gate

This branch must **not** allocate or build a release while another branch owns the current next TF version.

At plan time PR #55 owns TF 0.4.0. Therefore:

- research, plan and RED tests may proceed now;
- production/schema integration must wait until that release lane resolves;
- immediately before production work, rebase onto current `main`;
- read `TF_VERSION` and existing artifact directories again;
- allocate the next unused immutable version rather than assuming a number in advance.

If 0.4.0 becomes current, this change is expected to be 0.5.0. That is an expectation, not a precommitted constant.

## Schema contract

Reuse the existing optional provenance features; do not create header-specific duplicates.

For every `document` node `d`:

- `src_file(d)` stays in the main module and remains unchanged;
- `src_span(d)` in the provenance module is the original-file byte range of the complete outer `<AOHeader>...</AOHeader>`;
- `srcxml(d)` in the provenance module is exactly the bytes of that range decoded with the existing UTF-8/surrogateescape convention.

The same `src_span.tf` / `srcxml.tf` feature files continue to serve their existing sign/word/layout/etc populations. Text-Fabric node features are polymorphic over node types, so no new module or feature name is necessary.

Remove `docid_raw` from the new main artifact. Keep `docid` byte/value semantics exactly as before: source `AOHeader/docID` or filename fallback, then `.strip()`.

No other `*_raw` feature is changed.

## Converter design

### 1. Preserve original bytes through the document boundary

In `director()`:

```python
original_data = path.read_bytes()
data = original_data
```

Repairs continue to operate on `data` exactly as today. `OffsetMap` is still constructed from `original_data` and the existing manifest entry.

Pass `original_data` into `_document()` explicitly. Do not re-read the file and do not move patch application into `_document()`.

### 2. One helper owns header provenance extraction

Add a small testable helper, conceptually:

```python
header_provenance(spans, original_data, omap) -> (span_text, srcxml_text)
```

It must:

1. select exactly one `Span` with `tag == "AOHeader"` and `depth == 1`;
2. map its outer endpoints through `omap.span_to_original()` when `omap` exists;
3. require `0 <= start < end <= len(original_data)`;
4. slice the **original** bytes;
5. require that slice to start with `<AOHeader` and end with `</AOHeader>` and represent the exact mapped outer element, not a repaired serialization;
6. decode using UTF-8 with `surrogateescape` consistently with existing source-fragment handling;
7. return `f"{start}-{end}"` plus the decoded exact slice.

Any invariant failure raises a targeted `ValueError` naming the source record. It is a converter correctness failure, not a new exclusion category. The production census proves there are zero current exceptions, so there is no allowlist.

Do not derive `srcxml` by lxml serialization: attribute quoting, whitespace, entities and namespace spelling must remain source bytes.

### 3. Assign provenance on the document node

When `_document()` creates `doc` and before termination, set `src_span` and `srcxml` from the helper's result.

Continue using existing span generation for words/layout; do not refactor `_State._span()` in this ticket unless a RED test proves shared extraction is necessary.

### 4. Retire `docid_raw`

Stop declaring/emitting `docid_raw` in converter feature metadata and generated artifacts.

Tests must prove:

- `docid` retains all existing normalized values;
- duplicate `docid` grouping is unchanged;
- section addressing is unchanged;
- upstream TLHdig link resolution is unchanged;
- no consumer/app config still names `docid_raw` as required data.

The original raw `<docID>` remains recoverable from `document.srcxml` / `src_span`; no replacement main-module feature is introduced.

## Text-Fabric serialization contract

Whole headers can contain literal newline and tab characters. Before converter implementation is accepted, a pinned Text-Fabric 13.1 regression must write and reload a node feature value containing:

- an outer `AOHeader` string;
- at least one newline;
- at least one tab;
- a backslash as an adversarial value even though current corpus count is zero.

The loaded value must equal the original Python string exactly. This guards actual writer/loader behavior rather than relying only on file-format documentation.

## Contract A extension

Extend the existing `programs/check_contract_a_graph.py` `contract-a-graph` release gate. Do not add a weaker parallel header checker.

For each `document` node:

1. require `src_file`;
2. require `src_span`;
3. parse `start-end` strictly;
4. require the range to lie inside the original file;
5. require the slice to be an outer `AOHeader` element;
6. require `F.srcxml.v(document)` to equal the exact decoded slice;
7. count every emitted document and fail if any lacks span/xml.

Document checks must run even when a document appears in `contract_a_known.txt` or `known_lossy.txt`; those existing exceptions apply to word reconstruction only and must not become a header escape hatch.

Update `reports/contract_a_graph.md` to show separate document-header and word rows. CI/release certification should continue to use the existing canonical gate name so historical policy meaning is strengthened without adding an unnecessary gate alias.

## Contract B after preservation

Once whole headers are byte-recoverable, Contract B should no longer describe current header bytes as **unrecoverable**. However, its semantic-disposition distinction remains useful: a source construct can be preserved raw in optional provenance while still not be modelled as a queryable feature/node.

Update wording so current categories mean:

- represented/queryable in the main graph;
- preserved-only in document provenance;
- malformed-but-preserved in document provenance.

The exact vocabulary/placement census and fail-closed behavior remain. Do not delete Contract B merely because provenance becomes lossless.

A RED test must prevent the report from continuing to claim these header bytes are dropped after document provenance exists.

## Provenance module documentation

Update generated/static provenance documentation. Current README language says `srcxml` is the source fragment of each sign and that every contained tag is modelled elsewhere; after header preservation both statements are incomplete/false.

New wording must state:

- sign-level `srcxml` retains source fragments used for textual reconstruction;
- document-level `srcxml` retains the complete raw `AOHeader`;
- `src_span` is always a byte range in `src_file`;
- optional provenance may contain source data not semantically modelled in the main module;
- loading the module is unnecessary for ordinary linguistic queries but required for exact source audit/recovery.

Regenerate feature docs and ensure optional-module classification remains correct.

## Release-delta contract

After rebasing and selecting the actual new TF version, materialize the immediately preceding certified artifact and declare the exact semantic delta using `programs/release-delta.json`.

Expected substantive feature changes include at least:

- removal of `main:docid_raw.tf`;
- changed `provenance:src_span.tf` due document values;
- changed `provenance:srcxml.tf` due document values.

Do **not** freeze this list before the final rebased schema: the predecessor-delta gate must report the actual exact changed feature set. Version/date metadata-only differences remain governed by the existing release-delta semantics.

Historical artifacts stay immutable.

## TDD sequence

### RED 1 — pure header extraction

Before production code, tests require an API absent on current main and cover:

- ordinary one-line header exact span/value;
- multi-line/tab header exact value;
- a length-changing repair **before** the header: mapped original span/value remains exact;
- a repair **inside** header content: returned provenance remains the original bytes, not repaired bytes, if mapped outer boundaries remain exact;
- missing header;
- duplicate depth-1 headers;
- invalid/out-of-range mapped span.

The helper must fail closed on structural ambiguity.

### RED 2 — document graph emission / `docid_raw` retirement

Build a tiny fixture and require:

- `document.src_span` exists;
- `document.srcxml` equals the exact raw header;
- normalized `document.docid` is unchanged for surrounding whitespace;
- `docid_raw` is absent;
- existing source path/project fields remain unchanged.

### RED 3 — Text-Fabric escape round-trip

Write/load a tiny TF fixture containing newline, tab and backslash in `srcxml`; require exact equality after reload.

### RED 4 — Contract A graph header verification

Refactor the checker enough to expose a testable document-header verification helper, then require failures for:

- missing document span;
- malformed span syntax;
- span outside source;
- span pointing at body/another element;
- `srcxml` differing by one byte/character;
- missing `srcxml`;
- known-lossy/known-bad document attempting to bypass header verification.

### RED 5 — downstream/schema references

Tests require:

- generated feature inventory has no core `docid_raw` in the new schema;
- app/config/docs do not require it;
- Contract B wording reflects preserved-only rather than dropped/unrecoverable header data;
- provenance README/docs describe document values.

All RED commits must precede production changes. Hosted CI should demonstrate intended failures while pre-existing tests remain green.

## Implementation / test gate

After RED and after the 0.4.0 owner resolves:

1. rebase to current `main`;
2. re-check active PR ownership and TF version;
3. implement the smallest converter/checker/docs changes satisfying RED;
4. run focused unit/adversarial tests;
5. build the next immutable main + provenance artifact from the reviewed converter;
6. run canonical release certification in `regression-valid` mode with predecessor delta;
7. run ordinary exact-head CI after generated certification evidence lands;
8. verify previous TF/provenance versions are byte-identical;
9. remove the temporary research workflow before finalization.

## Independent adversarial review

A fresh review context on the exact final head must challenge at least:

- repaired vs original bytes accidentally mixed;
- a mapped span that merely starts/ends plausibly but is not the exact header;
- duplicate/namespaced header ambiguity;
- TF newline/tab/backslash escaping;
- document provenance missing on zero-sign/anchor documents;
- `contract_a_known.txt` becoming a document-header bypass;
- `docid` normalization/grouping/section/link drift after removing `docid_raw`;
- provenance module split accidentally leaving `srcxml/src_span` in main;
- Contract B falsely claiming semantic modelling merely because bytes are preserved;
- release-delta subset/allowlist mistakes;
- historical artifact mutation;
- accidental semantic promotion of `mDocID` (owned by #63);
- final branch/version racing another artifact producer.

Any blocking finding requires a new RED → fix → full relevant tests → fresh review cycle.

## Completion / issue disposition

Only after the certified artifact is merged:

- close #57: whole document header is recoverable and independently verified;
- close #58: decision implemented by retiring `docid_raw` in favor of header provenance;
- close #10 as superseded-by-design/completed through the new provenance contract, explicitly noting that normalized `docid` was intentionally unchanged;
- keep #63 open until semantic `mDocID` / join-graph comparison is complete.

## Acceptance

The feature is complete when every emitted document in the new release has exact original-source `AOHeader` `src_span` + `srcxml`, Contract A verifies all of them with zero header exceptions, `docid_raw` is absent while normalized document identity/addressing/link behavior is unchanged, optional provenance documentation is truthful, exact release delta/certification is green, historical artifacts are untouched, and a fresh independent adversarial review finds no remaining false-GREEN path.
