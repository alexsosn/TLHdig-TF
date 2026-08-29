# Plan: automate TLHdig Zenodo updates through TLHdig-TF publication

## Goal

Implement an end-to-end upstream update pipeline:

```text
discover latest TLHdig on Zenodo
→ detect whether it is new
→ download source ZIP
→ verify published checksum
→ unpack safely
→ inventory/diff XML
→ derive version-specific repairs and exception state
→ rebuild Text-Fabric
→ run all source and graph validation gates
→ regenerate reports/documentation
→ package an immutable release
→ publish to GitHub Releases
```

The pipeline must be idempotent, reproducible, safe against AOxml drift, and fully automatic on the green path. New source conditions that require philological or converter-design judgement should produce a candidate build/report and stop before public publication.

---

# Phase 0 — version and publication model

## 0.1 Keep separate version identities

Preserve:

```text
SOURCE_VERSION   human upstream TLHdig version
TF_VERSION       converter/ontology version
RELEASE_TAG      immutable binding of both
```

Recommended tags:

```text
tlhdig-0.3_tf-0.1.0
tlhdig-0.4_tf-0.1.0
tlhdig-0.4_tf-0.1.1
```

Fallback:

```text
zenodo-<record-id>_tf-<tf-version>
```

Do not bump `TF_VERSION` only because the upstream XML changed.

## 0.2 Initial release assets

Before the TF app is ready, publish:

```text
TLHdig-TF-<tag>.zip
reports-<tag>.zip
provenance.json
SHA256SUMS
```

After `app/` exists, also publish Text-Fabric's standard `complete.zip` and smoke-test the public `tf.app.use()` path.

---

# Phase 1 — upstream configuration and lock

## 1.1 Add `programs/upstream.toml`

Example:

```toml
provider = "zenodo"
seed_record_id = 20328284

[source_file]
suffix = ".zip"
require_unique = true

[limits]
max_archive_bytes = 500000000
max_unpacked_bytes = 3000000000
```

Do not encode the current archive filename or MD5 here.

## 1.2 Add generated `programs/upstream.lock.json`

Store:

- Zenodo parent/concept record ID;
- current version-specific record ID and DOI;
- title/version label/publication date;
- selected archive key and size;
- Zenodo checksum;
- local SHA-256;
- XML count;
- source-manifest digest.

Bootstrap the lock from Beta 0.3 and verify that it resolves record `20328284`, DOI `10.5281/zenodo.20328284`, archive `TLHbasisONLINE25_1_ZENODO_Beta_03.zip`, and its published MD5.

## 1.3 Refactor source constants

Keep `TF_VERSION` in the converter, but stop treating `SOURCE_VERSION`, `CORPUS`, Zenodo DOI, archive MD5, and the encrypted-file exception as immutable import-time globals.

---

# Phase 2 — Zenodo client and discovery

Create:

```text
programs/upstream/zenodo.py
programs/upstream/discover.py
```

Pin a normal HTTP client (`requests` or `httpx`) in `requirements.txt`.

Required API:

```python
get_record(record_id)
get_latest(seed_or_parent_record_id)
select_source_file(record, config)
```

Discovery rules:

1. query the public Records API;
2. bootstrap the parent/concept identity from the known record;
3. follow the current latest-version link;
4. compare immutable record ID with `upstream.lock.json`;
5. require exactly one configured `.zip` candidate;
6. parse a friendly version label if possible, but never depend on it for identity.

Add tests for:

- 0.2-style metadata;
- 0.3-style metadata;
- no `metadata.version`;
- no ZIP;
- multiple ZIPs;
- latest == lock;
- latest != lock.

---

# Phase 3 — update orchestrator

Create:

```text
programs/update.py
```

First subcommand:

```bash
python programs/update.py discover
```

Emit machine-readable discovery state, e.g.:

```json
{
  "has_update": true,
  "current_record_id": 20328284,
  "latest_record_id": 99999999,
  "version_label": "0.4"
}
```

A scheduled run with no new record must finish quickly without starting the full conversion.

---

# Phase 4 — download and checksum

Create:

```text
programs/upstream/download.py
```

Use working path:

```text
build/upstream/<record-id>/
```

Procedure:

1. stream to `*.part`;
2. compute/verify Zenodo checksum;
3. compute SHA-256 simultaneously;
4. close/fsync;
5. atomically rename to final archive;
6. write download metadata.

A checksum failure must happen before extraction.

---

# Phase 5 — safe extraction

Create:

```text
programs/upstream/extract.py
```

Reject archive entries with:

- absolute paths;
- `..` traversal;
- normalized paths outside extraction root;
- symlinks;
- duplicate normalized paths;
- configured compressed/uncompressed size violations.

Extract under:

```text
build/upstream/<record-id>/unpacked/
```

Discover the XML corpus root by structure, not by ZIP filename or guessed top-level directory.

---

# Phase 6 — source inventory and diff

Create:

```text
programs/upstream/diff.py
```

For each XML record:

```text
NFC-normalized relative path
size
SHA-256
```

Compare with the previous published source state and classify:

```text
unchanged
changed
added
removed
```

Generate:

```text
reports/upstream.md
reports/upstream-diff.md
build/update/source-diff.json
```

---

# Phase 7 — version source-specific state

Migrate the current global source files into:

```text
programs/source-state/<zenodo-record-id>/
  source.json
  corpus.sha256
  patches.yaml
  excluded.tsv
  known_lossy.tsv
  morph_exceptions.tsv
```

For Beta 0.3 the directory is:

```text
programs/source-state/20328284/
```

Use Zenodo record ID because it is immutable and unambiguous.

`source.json` should store record ID/DOI, friendly source version, archive identity, XML count, previous record ID, and relevant converter metadata.

---

# Phase 8 — dynamic source context

Refactor `programs/tlhdig/paths.py` around something like:

```python
@dataclass
class SourceContext:
    corpus: Path
    state_dir: Path
    metadata: dict
```

`corpus_files()`, `rel()`, build, repair verification, and gates should receive/use this context instead of a single global `TLHdig-0.3` path.

Keep a no-argument local default that loads the current lock if convenient.

---

# Phase 9 — common raw/repaired source iterator

Create:

```text
programs/tlhdig/sourcecorpus.py
```

Expose per document:

```text
relpath
raw bytes
repaired bytes
source SHA-256
repair status
exclusion status
```

Refactor build and source gates to use this shared access layer while remaining explicit about whether each test validates raw source, repaired converter input, or both.

---

# Phase 10 — regenerate repairs safely

Refactor `make_patches.py` to accept runtime corpus/output paths and generate the new release's `patches.yaml` without overwriting previous source state.

Add policy classification:

```text
SAFE_REPAIR_REASONS
REVIEW_REPAIR_REASONS
```

At minimum, crossing-tag structural boundary repairs are review-class.

Generate:

```text
reports/repair-summary.md
reports/repair-review.md
```

Carry an old repair automatically only when the new file's SHA-256 is identical.

---

# Phase 11 — exclusions and known-lossy state

Add `programs/make_exclusions.py` or equivalent preparation logic.

Classify files as:

```text
convertible as-is
convertible after approved repair
unchanged previous exclusion
new/changed unconvertible file
```

Automatic publication requires zero new/changed exclusions.

Change known-lossy state from a path-only list to a structured version-specific form containing at least path, source SHA-256, failure signature, and reason. Carry it forward only for identical source bytes.

---

# Phase 12 — morphology anomaly signatures

Refactor `check_morph.py` so aggregate counts are reports, not the primary cross-version gate.

Replace static thresholds with approved anomaly signatures containing enough immutable context to identify the source anomaly, e.g.:

```text
path
file SHA-256
mrp index
problem code
hash/raw-value signature
```

Known signatures on unchanged bytes pass. A novel signature becomes a release blocker and is written to `reports/morph-new.tsv` / `reports/morphology.md`.

---

# Phase 13 — AOxml schema drift gate

Create:

```text
programs/check_source_schema.py
```

Inventory:

- qualified/local element names;
- attributes per element;
- counts;
- selected low-cardinality structural values.

Compare with previous source release and classify new constructs as:

```text
mapped
intentionally ignored
unmapped
```

Any new unmapped construct blocks unattended publication.

---

# Phase 14 — refactor build CLI

Support:

```bash
python programs/build.py \
  --corpus "$CORPUS_ROOT" \
  --source-state "$STATE_DIR"
```

Write a richer `tf/<TF_VERSION>/BUILD-COMPLETE` containing:

```text
sourceRecordId
sourceDOI
sourceVersion
sourceArchiveSHA256
sourceManifestSHA256
tfVersion
converterCommit
textFabricVersion
pythonVersion
buildTimestamp
```

Keep the current compaction, post-compaction reload, and section-address test.

Make passage probes data-driven enough that a legitimate upstream removal does not make the whole updater permanently impossible to use.

---

# Phase 15 — full validation and readiness policy

Implement:

```bash
python programs/update.py validate
```

Run:

1. unit tests;
2. source manifest verification;
3. patch verification;
4. sign/tokenizer gate;
5. morphology gate;
6. source-schema gate;
7. build/ledger;
8. compacted reload;
9. section addressing;
10. marker conservation;
11. census/invariants;
12. documentation/report generation;
13. package smoke test.

Generate:

```text
reports/release-readiness.md
build/update/readiness.json
```

Centralize blockers in `programs/release_policy.py`, e.g.:

```python
BLOCKERS = {
    "checksum_failure",
    "archive_layout_ambiguous",
    "new_unmapped_source_construct",
    "new_structural_repair",
    "new_exclusion",
    "new_lossy_signature",
    "new_morph_failure",
    "build_failed",
    "ledger_failed",
    "marker_conservation_failed",
    "census_failed",
    "package_smoke_failed",
}
```

The publisher consumes `readiness.json` only when `publishable == true`.

---

# Phase 16 — census and documentation deltas

Keep `programs/census.py` as the generated source of volatile counts.

Add:

```text
reports/census-diff.md
```

Compare at least node types, slots, words, analyses, documents, cluster families/points/spans, exclusions, and duplicated `docid` counts.

Count changes are normally informational; only explicit invariants fail the release.

When the documentation generator exists, run it after the new TF build so feature/reference pages cannot describe the previous dataset.

---

# Phase 17 — package release assets

Create:

```text
programs/package_release.py
```

Output:

```text
dist/TLHdig-TF-<tag>.zip
dist/reports-<tag>.zip
dist/provenance.json
dist/SHA256SUMS
```

Before publication, unpack the generated corpus archive in a clean temporary directory, load it with `tf.fabric.Fabric`, run section probes/small invariants, and verify package checksums.

Once `app/` exists, add standard Text-Fabric `complete.zip` generation and public-release smoke testing.

---

# Phase 18 — GitHub release publisher

Create:

```text
programs/publish_release.py
```

or implement the thin release step with `gh` in Actions.

Workflow permission:

```yaml
permissions:
  contents: write
```

Idempotency rules:

```text
release tag absent                create
same tag + identical provenance   no-op success
same tag + different provenance   hard failure
```

Never replace an existing published dataset asset in place.

Generate release notes from source/census diffs and validation results.

---

# Phase 19 — race protection

Capture the converter commit used for the build (`GITHUB_SHA`). Immediately before tagging/persisting release state:

```text
fetch origin/main
require origin/main == build code SHA
```

If `main` moved during the long conversion, abort publication. A later run rebuilds from the new converter code.

Do not rebase old generated artifacts onto new source code.

---

# Phase 20 — GitHub Actions workflows

Keep/rework `dataset.yml` as a reusable build/validation workflow and add something like:

```text
.github/workflows/upstream.yml
```

Recommended triggers:

```yaml
on:
  workflow_dispatch:
  schedule:
    - cron: "17 4 * * *"
```

Use concurrency:

```yaml
concurrency:
  group: tlhdig-upstream-update
  cancel-in-progress: false
```

Architecture:

```text
discover job
  ├─ same record → stop successfully
  └─ new record → update job
                    ├─ download/extract/prepare
                    ├─ build/validate
                    ├─ always upload diagnostic reports
                    └─ publish only if readiness is green
```

Keep Actions artifacts for diagnostics only; public data goes to GitHub Releases.

Document that scheduled workflows in inactive public repositories can be disabled after long inactivity. Add external triggering later if permanent unattended monitoring is required.

---

# Phase 21 — optional Zenodo DOI for derived TLHdig-TF

After GitHub Releases work reliably:

1. enable the TLHdig-TF repository in Zenodo's GitHub integration;
2. add `CITATION.cff` and optionally `.zenodo.json`;
3. relate each TLHdig-TF release to the exact upstream TLHdig DOI;
4. verify GitHub releases are archived.

This is separate from using Zenodo as the upstream source-discovery service.

---

# Phase 22 — tests

## Unit tests

### Zenodo

- record parsing;
- latest link;
- parent/concept bootstrap;
- file selection;
- version fallback;
- checksum parsing.

### ZIP

- absolute path;
- traversal;
- symlink;
- duplicate normalized path;
- size limits;
- valid archive.

### source diff/state

- added/removed/changed/unchanged;
- NFC/NFD filenames;
- unchanged exclusion carries;
- changed exclusion does not;
- unchanged repair carries;
- changed repair is rediscovered;
- unchanged morphology anomaly carries;
- changed anomaly becomes novel.

### publisher

- new release;
- identical existing release no-op;
- conflicting existing release failure.

## Integration fixtures

Create synthetic source releases representing:

```text
v1 baseline
v2 adds normal XML
v3 changes malformed XML fixable mechanically
v4 introduces unmapped schema construct
v5 requires crossing-tag structural repair
```

Expected:

```text
v2 automatic green path
v3 automatic green path if repair is classified safe
v4 candidate build, publication blocked
v5 candidate build, publication blocked
```

---

# Phase 23 — migrate Beta 0.3

Before trusting updates:

1. query Zenodo API for `20328284`;
2. generate `upstream.lock.json`;
3. create `source-state/20328284/source.json`;
4. migrate/copy current `corpus.sha256`, `patches.yaml`, exclusion and known-lossy state;
5. convert morphology residuals into explicit anomaly signatures;
6. rebuild 0.3 through the new dynamic source API;
7. require semantically identical TF output apart from intentional provenance metadata.

This proves the refactor itself did not silently change the corpus.

---

# Phase 24 — replay the real 0.2 → 0.3 update

Use:

```text
0.2: Zenodo 15459134
0.3: Zenodo 20328284
```

Run the updater as though the current lock were 0.2.

It must:

1. discover 0.3;
2. select its differently named ZIP without filename assumptions;
3. verify checksum;
4. extract safely;
5. diff source files;
6. regenerate source state;
7. build and validate TF;
8. generate readiness reports;
9. stop/publish according to the review policy.

Make this historical replay a release-engineering acceptance test.

---

# Recommended PR sequence

## PR 1 — source abstraction

- `upstream.toml`
- current `upstream.lock.json`
- `source-state/20328284`
- dynamic `SourceContext`
- no behavior change for 0.3

## PR 2 — Zenodo discovery/download

- Records API client
- latest-version discovery
- checksum verification
- safe extraction
- corpus-root detection

## PR 3 — source diff and state migration

- SHA diff
- byte-identity carry-forward rules
- versioned patch/exclusion/lossy state
- reports

## PR 4 — source-quality gates

- morphology signatures
- source-schema drift
- common raw/repaired source iterator
- remove cross-version dependence on hard-coded `ENCRYPTED`

## PR 5 — update orchestrator

- `update.py`
- readiness JSON/policy
- census diff
- 0.2 → 0.3 integration replay

## PR 6 — packaging/publication

- deterministic derived archive
- provenance
- SHA256SUMS
- smoke test
- GitHub Release publisher

## PR 7 — scheduled workflow

- cheap daily discovery
- conditional full build
- concurrency/race guards
- review artifacts
- green-path publication

## PR 8 — standard TF release

After the app is stable:

- `complete.zip`
- clean-cache `use()` test
- README/distribution documentation
- optional Zenodo GitHub integration

---

# Definition of done

- [ ] scheduled discovery does not rebuild when the Zenodo record is unchanged;
- [ ] new versions are identified by immutable record ID/DOI;
- [ ] archive filename is not guessed;
- [ ] Zenodo checksum and local SHA-256 are verified/recorded;
- [ ] extraction is path-safe and bounded;
- [ ] XML root is discovered structurally;
- [ ] XML files are SHA-diffed against previous release;
- [ ] old exceptions carry only for identical bytes;
- [ ] each published source record has versioned source state;
- [ ] patches are regenerated/versioned;
- [ ] new structural repairs block unattended publication;
- [ ] new/changed exclusions block unattended publication;
- [ ] known-lossy state is hash-aware;
- [ ] morphology uses explicit exception signatures;
- [ ] AOxml schema drift is gated;
- [ ] source gates have explicit raw/repaired semantics;
- [ ] build accepts runtime source context;
- [ ] compacted TF reload and section addressing pass;
- [ ] marker conservation and census pass;
- [ ] reports/docs regenerate from the new build;
- [ ] packaged data reloads in a clean directory;
- [ ] green updates create immutable GitHub Releases;
- [ ] reruns are idempotent;
- [ ] conflicting existing release tags fail;
- [ ] publication aborts if converter `main` changed during build;
- [ ] blocked updates leave useful reports but no public release;
- [ ] historical 0.2 → 0.3 replay passes;
- [ ] standard Text-Fabric public `use()` path is tested once the app/release layer exists.
