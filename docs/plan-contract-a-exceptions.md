# Plan: remeasure and reduce Contract-A provenance exceptions

Issue: #142

## Gate 1 — freeze the measured corpus census

Add a deterministic research measurement that runs against the committed current
`tf/0.4.0` + `tf-provenance/0.4.0`, pinned TLHdig 0.3 source bytes, and
`programs/patches.yaml`.

The generated JSON is keyed by the 16 current allowlist paths and records:

- repair classes/reasons and source SHA;
- #12 crossing ownership;
- converter-visible source-word count;
- exact/inexact repaired-stream start/end boundaries;
- mapped immutable-source span diagnostics;
- graph word count;
- invalid immutable-source slices;
- graph/source token mismatches;
- representative failures.

The generator must fail if the allowlist, corpus, manifest, #12 crossing inventory, or
TF artifact cannot be read. A partial census is worse than no census.

### RED test

Before accepting generated data, add tests that require:

- exactly the current 16 allowlisted paths;
- exactly 9 #12 crossing and 7 non-crossing paths on the current pinned source;
- every row to contain both boundary and graph measurements;
- source SHA and ordered repair reasons;
- `required_now` to be derived from measured failures, not hand-entered prose.

## Gate 2 — classify generalized exception classes

From the measured census, group failures by mechanism rather than filename. Expected
candidate classes from static inspection are:

1. crossing/coupled structural recovery (#12);
2. stray `</w>` deletion at a word boundary;
3. stray ODF close deletion;
4. attribute-value escaping;
5. malformed duplicate/bare `<w` fragment deletion.

Do not create a code fix for a class whose rows are already exact and graph-identical;
remove the stale exception instead, under a regression test.

For every class that still fails, add a focused RED test reproducing its measured
coordinate/graph failure before changing mapping semantics.

## Gate 3 — shrink the allowlist conservatively

For each row with `required_now=false`:

1. add a test proving that the document passes the same graph Contract-A predicate
   without an exemption;
2. remove only that path;
3. rerun the full Contract-A graph gate.

Do not delete all seven non-crossing paths in one assertion unless the census proves
they are one behaviorally identical class.

Crossing-owned paths remain coordinated with #12. If #12 recovery makes their
provenance exact, remove them only after rebuilding the current artifact and rerunning
the census/gate.

## Gate 4 — fix canonical provenance documentation

Update `featuremeta.DESCRIPTIONS["src_span"]` to state the actual contract:

- byte range in the immutable file named by `src_file`;
- repaired-source spans are translated through `OffsetMap`;
- an explicit allowlist exists only for measured cases where exact immutable-source
  reconstruction is not yet possible.

Do not retain the obsolete statement that every length-changing repaired document is
indexed in repaired-stream coordinates.

Regenerate feature documentation/metadata as required by the normal build/validation
path.

## Gate 5 — corpus validation and independent review

Run:

- focused unit tests for census + exception classes;
- `check_contract_a_graph.py`;
- the normal current validation/CI suite;
- manifest/feature-reference validation if generated metadata changes.

Then perform a logically independent adversarial review grounded in:

- the generated census;
- at least one real source from every generalized repair class;
- the shipped TF provenance features;
- `OffsetMap` behavior at both span boundaries.

The review should specifically try to find an exception removed because its *source
span* looked exact while its graph/sign content still disagreed.

## Merge strategy

Prefer a research/census PR before semantic changes if the measurements uncover
multiple root causes. If all non-crossing rows are demonstrably stale, the same PR may
continue through TDD to remove them, but the research and plan commits remain distinct
in history.
