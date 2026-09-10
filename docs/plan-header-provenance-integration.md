# Header provenance integration freeze

This note records the post-RED integration decision for the already-frozen
`docs/plan-header-provenance.md`. It is committed after TF 0.4.0 became the certified
`main` release and before any production implementation for document-header provenance.

## Base and immutable version

- The research/plan/hosted-RED ancestry was merged with current certified `main`
  without rebasing or force-updating it.
- Current immutable TF version on `main`: `0.4.0`.
- No other artifact-changing lane has reserved the next version.
- This feature therefore owns **TF/provenance 0.5.0**.
- `tf/0.4.0`, `tf-provenance/0.4.0`, and every earlier published artifact remain
  byte-for-byte immutable.

The later PUA-classification lane may continue through RED but must not claim an
artifact version until this release finishes.

## Release policy

The feature extends the already-mandatory `contract-a-graph` gate so that it verifies
whole-document `AOHeader` provenance in addition to word provenance. It does **not**
change the required gate set, required certification input set, artifact-digest
algorithm, predecessor-evidence contract, or evidence-publication semantics.

Therefore TF 0.5.0 remains under **`release-v5`**. A policy-number bump would imply a
changed release-policy contract that this feature does not introduce.

The predecessor delta for 0.5.0 must explicitly account for:

- document-level values added to optional provenance `srcxml` / `src_span`;
- retirement of core `docid_raw`;
- the corresponding metadata/documentation/app references;
- no unintended semantic changes to existing corpus features.

## Finalization dependency

Production implementation and ordinary tests may proceed now. Final immutable build,
canonical certification, and merge remain gated on the same-ref certification
concurrency fix being present on the final branch, so release evidence is generated on
one quiet exact head.
