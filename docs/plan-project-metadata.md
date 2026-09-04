# Project metadata implementation plan

**Research prerequisite:** `docs/research-project-metadata.md`.

This ticket follows the gate order **research → plan → implement → test**. Production changes must not begin until the research and this plan are committed.

## Scope

Add canonical source-path metadata to document nodes without changing section addressing or `docid` semantics.

Emit:

- `project` — top-level `_XML_<project>` code;
- `subcorpus` — compatibility alias, exactly equal to `project`;
- `source_subdir` — intermediate path components, `/`-joined, empty when none;
- `source_stem` — source filename without `.xml`.

Retain existing:

- `src_file` — full normalized corpus-relative path;
- `cth` — catalogue number from the top directory.

Do **not** emit `project_name`.

## Gate 1 — Test contract first

Repair the synthetic converter fixture so it satisfies the existing TF text-format requirements (`cu` must occur on at least one line), then assert the intended behavior before production code changes.

Required failing tests:

1. ordinary Beta 0.3 record emits `project`, `source_subdir`, `source_stem`;
2. `subcorpus == project` for compatibility;
3. nested HFR shard keeps the complete intermediate directory and does not reinterpret it;
4. malformed top-level path produces an explicit conversion failure containing the parser reason;
5. no `project_name` document feature is emitted;
6. existing `docid`, `cth`, `src_file`, and language behavior remains unchanged.

A failure caused only by an invalid synthetic fixture does not satisfy the RED gate; fixture failures must be repaired first.

## Gate 2 — Implementation

### 2.1 Replace duplicate path parsing

In `programs/tlhdig/convert.py`:

- remove the converter-local `_CTH_DIR` parsing logic;
- call `sourcepath.parse(rel)` once per source record after `rel_key()` has produced the canonical relative path;
- if `parse_ok` is false, raise a targeted `ValueError` naming `rel` and `parse_error`;
- pass the parsed structure into `_document()` or parse at the document boundary, but do not parse the same path twice.

The error is an invariant failure, not an exclusion-ledger category: all current Beta 0.3 corpus paths are required to satisfy the path parser gate.

### 2.2 Emit metadata

On the document node emit:

```text
cth            = parsed.cth
project        = parsed.project
subcorpus      = parsed.project
src_file       = parsed.src_file
source_subdir  = parsed.source_subdir
source_stem    = parsed.source_stem
```

Do not alter `docid`, grouping, line/column construction, or section features in this ticket.

### 2.3 Feature documentation

Update `programs/tlhdig/featuremeta.py`:

- add `project`, `source_subdir`, `source_stem` descriptions;
- mark `subcorpus` explicitly as a compatibility alias for `project`;
- clarify that `src_file` is release-scoped source-record identity, not cross-release persistent identity.

Do not add `project_name`.

## Gate 3 — Tests after implementation

Run the complete unit suite and require the new tests to turn green.

Add/retain corpus-level invariants:

- every current corpus path parses;
- observed project-code set remains the measured Beta 0.3 set;
- no current document can be produced with blank `project` due to parser failure.

Then run the existing full CI gates:

1. unit/adversarial tests;
2. corpus identity;
3. repair manifest;
4. sign round-trip;
5. morphology;
6. app config;
7. build stamp;
8. AOxml destination coverage;
9. provenance split;
10. cuneiform alignment;
11. outside-sign parsing.

## Gate 4 — Compatibility check

Before finalizing the PR, search the repository for `subcorpus` and confirm that adding `project` does not require consumers to migrate immediately. App and README may continue to use `subcorpus` in this ticket; migration can be a separate ticket with its own research/plan gate.

Generated TF artifacts are not rebuilt in this ticket unless the repository's normal PR policy requires committed dataset regeneration for feature-schema changes. If regeneration is required, it must happen only after code/tests are green and must be validated by the full census/stamp gates.

## Gate 5 — Independent review before merge

Review the final PR diff independently from the implementation pass. At minimum challenge:

- whether any human-readable vocabulary leaked into source-derived features;
- whether parser failures can still become blank metadata;
- whether `subcorpus` and `project` can diverge;
- whether nested directories are preserved losslessly;
- whether a new identifier was accidentally implied by `source_stem`;
- whether the change affects section addressing or manuscript grouping outside scope.

Any review finding requires a regression test when testable, a fix, full CI rerun, and a second final-diff review before merge.
