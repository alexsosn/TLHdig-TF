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

Because this changes the shipped graph/schema, release it as **TF `0.2.0`**. Preserve `tf/0.1.0` unchanged.

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

Test fixtures that exercise the converter must use a source path valid under the converter's published Beta 0.3 grammar. Empty `source_subdir` is a real empty-string path decomposition and should be asserted as `""`, not rewritten to `None` by tests.

## Gate 4 — Versioned artifact regeneration

Before rebuilding:

1. change `TF_VERSION` from `0.1.0` to `0.2.0`;
2. update current-version documentation that is operational or user-facing (`README`, `KNOWN-ISSUES`, `CITATION.cff`, integration/install examples, and generated provenance README template); historical research documents that explicitly describe measurements on 0.1.0 remain historical and are not mechanically rewritten;
3. add a regression test that the new generator version is `0.2.0` and that the old committed `tf/0.1.0` remains present.

Then run the full dataset workflow from the PR head:

1. build into `tf/0.2.0` and `tf-provenance/0.2.0` without touching `0.1.0`;
2. run `programs/census.py`, marker conservation and all normal release checks against `0.2.0`;
3. require `BUILD-COMPLETE` to validate the current bytes;
4. run `programs/publish_dataset.sh` so only certified, GitHub-safe files are staged;
5. commit the generated `0.2.0` dataset and its generated reports to the PR branch;
6. verify the committed artifact loads in a fresh checkout and exposes `project`, `source_subdir`, and `source_stem` with the same invariants as the synthetic tests.

Do not delete, rewrite, or re-certify `tf/0.1.0` as part of this release.

## Gate 5 — Compatibility and release-identity check

Before finalizing the PR:

- search the repository for `subcorpus` and confirm adding `project` does not require consumers to migrate immediately;
- search current-version references and ensure user-facing paths point to `0.2.0`, while explicitly historical measurements may still say `0.1.0`;
- confirm `TF_VERSION`, `tf/0.2.0`, `tf-provenance/0.2.0`, generated report headings/stamps and release version agree;
- confirm no `project_name.tf` exists in the new dataset;
- confirm the previous `tf/0.1.0` tree is byte-identical to `main`.

After merge, create Git tag / GitHub Release **`v0.2.0`** on the exact merged commit. The release must not point to a pre-merge PR commit or to a commit that lacks the certified `0.2.0` artifact.

## Gate 6 — Independent review before merge and release

Review the final PR diff independently from the implementation pass. At minimum challenge:

- whether any human-readable vocabulary leaked into source-derived features;
- whether parser failures can still become blank metadata;
- whether `subcorpus` and `project` can diverge;
- whether nested directories are preserved losslessly;
- whether a new identifier was accidentally implied by `source_stem`;
- whether the change affects section addressing or manuscript grouping outside scope;
- whether `0.1.0` was mutated rather than preserved;
- whether generated `0.2.0` actually came from the reviewed converter and carries a valid stamp;
- whether version strings, docs and release identity disagree.

Any review finding requires a regression test when testable, a fix, full CI/rebuild as appropriate, and a second final-diff review before merge. After merge, verify the release target SHA before publishing `v0.2.0`.

## Execution record

- Research and plan were committed before the revised implementation.
- The repaired RED run was CI #68: **340 passed, 3 failed**. The failures were exactly the missing `project` feature on ordinary/nested records and the missing explicit failure for malformed `CTH 473_XM`; no fixture or Text-Fabric infrastructure failure remained.
- Production implementation then replaced the duplicate converter regex with the merged source-path parser, emitted the planned source-derived metadata, and updated feature descriptions. The temporary branch-only apply workflow deleted itself in the implementation commit and is not part of the PR diff.
- First post-implementation CI #71 reached **341 passed, 2 failed**. Both are test-contract corrections: a legacy test constructed impossible `doc.xml` at corpus root, and the new test expected TF to coerce an intentionally empty `source_subdir` to `None` although TF preserves it as `""`. Production path validation and feature emission behaved as designed.
- Those two test contracts were corrected without changing production behavior: the load-skip fixture now uses `CTH 101_XML_TLH/doc.xml`, and the ordinary source-path test asserts `source_subdir == ""`. The temporary test-fix workflow removed itself and is absent from the PR diff.
- The artifact-release research extension established the project rule that generator/schema changes require a fresh versioned artifact and release; this ticket therefore targets TF `0.2.0` and preserves `0.1.0`.
- GREEN full-CI, versioned full rebuild/certification, independent final review, merge, and exact-SHA `v0.2.0` release remain required.
