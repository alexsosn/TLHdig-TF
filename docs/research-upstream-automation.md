# Research: automatic upstream discovery, rebuild, validation, and publication for TLHdig-TF

## Scope

TLHdig-TF should be able to detect a new published TLHdig XML corpus version on Zenodo, download the correct archive, verify it, unpack it safely, rebuild the Text-Fabric dataset, regenerate validation reports, and publish a new immutable TLHdig-TF release.

This design is grounded in the current `alexsosn/TLHdig-TF` codebase, the published TLHdig Beta 0.2 and 0.3 Zenodo records, Zenodo's Records/version model, GitHub Actions/Releases, and Text-Fabric's release/data-sharing conventions.

The central constraint is that TLHdig-TF's current safeguards are deliberately tied to one immutable source release. Automation therefore cannot mean replacing `corpus/TLHdig-0.3` and rerunning `build.py`. Each upstream release needs its own identity, repair state, exception state, validation evidence, and derived-release provenance.

---

## 1. Current repository state

### 1.1 Source identity is hard-coded to Beta 0.3

`programs/tlhdig/__init__.py` contains:

```python
SOURCE_VERSION = "0.3"
TF_VERSION = "0.1.0"
```

`programs/tlhdig/paths.py` hard-codes:

```python
CORPUS = ROOT / "corpus" / "TLHdig-0.3"
ZENODO_DOI = "10.5281/zenodo.20328284"
ZENODO_ZIP_MD5 = "f9acbc8db3111cc7dd88d82f7819a912"
```

The existing distinction between upstream source version and TF converter/schema version is correct and should remain. A third identity is needed: the immutable derived release that binds one Zenodo record to one TLHdig-TF converter revision.

### 1.2 The source corpus is bundled in Git

The repository contains `corpus/TLHdig-0.3/`. Future upstream releases should preferably be downloaded into an ephemeral work directory rather than adding another hundreds-of-megabytes XML tree to Git history. Reproducibility does not require duplicating an immutable Zenodo archive in every Git revision if its record ID, DOI, checksums, and per-file manifest are retained.

### 1.3 `corpus.sha256` is a release pin

`programs/tlhdig/corpusid.py` records `relative path -> SHA-256` and detects missing, altered, and unexpected XML files. `build.py` refuses to build when the source differs from that manifest.

That is exactly the right behavior after a source release has been selected. It cannot also serve as update discovery: a legitimate TLHdig 0.4 would intentionally fail the 0.3 manifest. Source manifests therefore need to become versioned.

### 1.4 Repair state is source-release-specific

`programs/patches.yaml` is not a generic recipe. Each entry is pinned to the SHA-256 of the exact source file and stores exact byte replacements. `verify_patches.py` rejects changed source bytes.

This is a strong design property and should be preserved. A new upstream release receives a new patch manifest, even when filenames are unchanged.

### 1.5 Repair discovery is already largely automatable

`programs/make_patches.py` already scans the corpus, finds XML files that do not parse, runs repair detectors, retains patches only when the result parses, writes a patch manifest, and reports unrepaired files.

This is the core of the future source-preparation stage.

### 1.6 Not every repair is safe to auto-approve

`programs/tlhdig/repair.py` separates normal detectors from `LAST_RESORT = (detect_crossing_tags,)`. The current repository has already identified crossing-tag fixes that move structural boundaries and require philological judgement.

The updater should classify repairs into:

- **automatic/mechanical**: byte-local syntax repairs whose interpretation is not structurally ambiguous;
- **review required**: boundary-moving structural repairs, at minimum crossing-tag repairs.

A review-class repair should not prevent an automated candidate build and report, but it must prevent automatic public publication.

### 1.7 Exclusions and lossy allowances are also 0.3-specific

`programs/excluded.txt` intentionally makes new exclusions fail instead of disappearing inside a balanced total. `check_signs.py` similarly uses a checked-in known-lossy list so that a new source-loss case fails.

For cross-version automation, path alone is insufficient. An approval should carry forward only when the relative path and source SHA-256 are unchanged. A changed file at the same path must be re-evaluated.

### 1.8 Morphology thresholds are calibrated to 0.3

`check_morph.py` currently gates on aggregate residuals (roughly 520 parse failures and 20 dangling selectors). This was a sensible improvement over an always-passing gate, but an unattended update must not automatically increase those thresholds when a new source release adds anomalies.

The robust model is an explicit anomaly signature, for example:

```text
(file SHA-256, failure kind, mrp index, hash/raw signature)
```

Known signatures on byte-identical source files carry forward; novel signatures block promotion and appear in the update report.

### 1.9 The current dataset workflow is a rebuild check, not an updater

`.github/workflows/dataset.yml` currently runs monthly/on demand, builds the bundled source, runs census and marker checks, and uploads reports as an Actions artifact.

It does not query Zenodo, detect new versions, download/unpack a source archive, regenerate source state, publish TF data, or create an immutable GitHub release.

---

## 2. Zenodo discovery

### 2.1 TLHdig versions are separate immutable Zenodo records

Known published versions include:

```text
Beta 0.2
record: 15459134
DOI: 10.5281/zenodo.15459134
file: TLHdig_0.2.0-beta.zip
checksum: md5:93e71e2560f5e109c87713d5590cb059
```

and:

```text
Beta 0.3
record: 20328284
DOI: 10.5281/zenodo.20328284
file: TLHbasisONLINE25_1_ZENODO_Beta_03.zip
checksum: md5:f9acbc8db3111cc7dd88d82f7819a912
```

The filename convention changed completely. The updater must not infer a future filename from the current one.

### 2.2 Use the Zenodo Records API and version links

Discovery should use the public Records API (`GET /api/records/:id`) rather than scraping HTML. Starting from the known current record, retrieve the record's parent/concept/version links and follow the documented latest-version relation.

The canonical update identity is the immutable version-specific Zenodo record ID/DOI. Human version strings are useful metadata, not the primary comparison key.

Recommended version-label priority:

1. `metadata.version` if present;
2. strict extraction from a title such as `Beta Version 0.4`;
3. fallback `zenodo-<record_id>`.

### 2.3 File selection must fail rather than guess

Initial policy can be deliberately strict:

```text
select downloadable files ending in .zip
require exactly one candidate
```

If a future record has zero or multiple candidate archives, discovery becomes a review condition. Do not choose the first file, the largest file, or a guessed filename.

### 2.4 Verify Zenodo checksum and compute SHA-256

Download streaming should verify the checksum supplied by Zenodo and compute a local SHA-256 in the same pass. Persist both. Zenodo's checksum verifies the downloaded object against the record; SHA-256 becomes TLHdig-TF's own strong archive identity.

---

## 3. Safe extraction and corpus discovery

Do not use an unchecked `ZipFile.extractall()` on a remotely supplied archive.

Reject:

- absolute paths;
- `..` traversal;
- entries escaping the extraction root after normalization;
- symlinks;
- duplicate normalized paths;
- archives exceeding explicit compressed/uncompressed bounds.

After extraction, find the corpus root by structure rather than archive filename. The current corpus contains many `CTH ..._XML_...` directories; the updater should identify one unambiguous root containing the expected XML population.

---

## 4. Introduce an upstream lock and versioned source state

Recommended static configuration:

```text
programs/upstream.toml
```

containing provider, seed/current record and source-file-selection policy.

Recommended generated lock:

```text
programs/upstream.lock.json
```

with:

- parent/concept record ID;
- current version-specific record ID and DOI;
- title and friendly version label;
- publication date;
- chosen archive key and size;
- Zenodo checksum;
- archive SHA-256;
- XML count and source-manifest digest.

Source-specific state should become:

```text
programs/source-state/<zenodo-record-id>/
  source.json
  corpus.sha256
  patches.yaml
  excluded.tsv
  known_lossy.tsv
  morph_exceptions.tsv
```

Use the immutable Zenodo record ID as the directory key.

---

## 5. Carry approvals forward by bytes, not paths

For old source A and new source B compute:

```text
unchanged = same normalized relative path + same SHA-256
changed   = same path + different SHA-256
added
removed
```

For unchanged files it is legitimate to carry forward approved repairs, exclusions, known-lossy allowances, and morphology anomaly signatures.

For changed files every such approval is invalid until re-derived/re-reviewed. This follows directly from the existing patch design, where a file hash is part of repair identity.

---

## 6. Source preparation for a new release

### 6.1 Inventory and diff

Generate at least:

```text
reports/upstream.md
reports/upstream-diff.md
```

with counts/lists of added, removed, changed and unchanged XML, subcorpus/CTH directory changes, and total source bytes.

### 6.2 Rediscover parse repairs

Reuse/refactor `make_patches.py` to produce a version-specific manifest and classify proposed repairs as automatic or review-required.

### 6.3 Recompute exclusions safely

Add a source-preparation stage that distinguishes:

- convertible as-is;
- convertible after approved repair;
- unchanged previously approved exclusion;
- new/changed unconvertible file.

A new/changed unconvertible file blocks unattended publication. Do not append it automatically to an allowlist.

### 6.4 Recompute lossy and morphology exception signatures

Carry previous allowances only for unchanged bytes. Novel tokenization-loss or morphology-failure signatures block promotion.

---

## 7. Detect AOxml schema drift

Syntactically valid XML can still introduce a new element or attribute that the converter silently ignores. The updater therefore needs a source-schema inventory:

- element qualified/local names;
- attributes per element;
- occurrence counts;
- low-cardinality structural values where useful.

Compare with the previous release and classify new constructs as:

```text
known mapped
known intentionally ignored
new/unmapped
```

A new/unmapped construct blocks automatic publication until the Contract-B mapping is updated.

---

## 8. Centralize raw/repaired source access

Current gates inspect source differently: some apply repairs, some parse raw files and skip failures. A multi-version updater should provide a common source-document abstraction exposing:

```text
relative path
raw bytes
repaired bytes
source SHA-256
repair status
exclusion status
```

Individual gates can still be logically independent, but each must state whether it validates raw source, repaired converter input, or both. No gate should pass merely because all newly broken files were skipped.

---

## 9. Build provenance

Refactor `build.py` to accept a runtime corpus/source-state instead of import-time `CORPUS = ...0.3`.

The build completion marker should include at least:

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
```

Keep the current post-compaction reload and section-address probe: they are strong publication gates.

---

## 10. Reports and release readiness

A new upstream release should regenerate existing reports and add deltas:

```text
reports/upstream.md
reports/upstream-diff.md
reports/schema-diff.md
reports/repair-summary.md
reports/census.md
reports/census-diff.md
reports/markers.md
reports/morphology.md
reports/release-readiness.md
```

`release-readiness.md` should summarize every gate in one table. Publication should consume a machine-readable `readiness.json`, not infer success from missing files or shell output.

A green update requires, among other things:

- Zenodo checksum and extraction pass;
- no new unmapped AOxml constructs;
- no new review-class structural repairs;
- no new/changed exclusions;
- no novel lossy/morphology failures;
- build ledger and compacted reload pass;
- section addressing works;
- marker conservation passes;
- census invariants pass;
- documentation/report generation passes;
- release package reloads.

---

## 11. Publication

### 11.1 Actions artifacts are diagnostics, not releases

Continue uploading diagnostics with `actions/upload-artifact`, including on blocked runs, but publish research data through immutable GitHub Releases.

### 11.2 Text-Fabric release convention

Once the planned TF app exists, publish Text-Fabric's standard `complete.zip` containing app/data/resources and smoke-test the exact public `tf.app.use()` access path from a clean cache.

Before the app is ready, publish a deterministic derived-data ZIP plus reports and provenance.

### 11.3 Release tags bind source and converter versions

Recommended:

```text
tlhdig-0.3_tf-0.1.0
tlhdig-0.4_tf-0.1.0
tlhdig-0.4_tf-0.1.1
```

Fallback when no friendly source version can be parsed:

```text
zenodo-<record-id>_tf-<tf-version>
```

A new upstream source does not by itself require a TF schema-version bump.

### 11.4 Provenance asset

Every release should include `provenance.json` with exact Zenodo record/DOI/archive checksums, converter commit, TF version, Text-Fabric/Python versions, output archive checksum, and major corpus counts.

### 11.5 Optional derived-data DOI

Zenodo's GitHub integration can archive TLHdig-TF GitHub releases and assign the derived project its own DOI. That DOI should remain separate from, and related to, the upstream TLHdig dataset DOI.

---

## 12. Polling cadence and durability

Zenodo metadata checks are cheap; daily discovery is preferable to monthly rebuilding. A schedule such as `17 4 * * *` avoids the top-of-hour Actions load.

There is one operational limitation: GitHub can disable scheduled workflows in inactive public repositories after long inactivity (documented as 60 days). Therefore GitHub Actions schedule + manual dispatch is sufficient for the first implementation, but a truly durable watcher may need an external scheduler that triggers the workflow.

No documented Zenodo webhook was found for “new version of this record”, so the architecture should assume polling.

---

## 13. Idempotency and race safety

Every stage should be rerunnable.

- Same latest Zenodo record as lock: successful no-op.
- Existing downloaded archive with matching checksums: reuse.
- Existing version-specific source state with matching identity: reuse/verify.
- Existing release tag with identical provenance/checksums: no-op.
- Existing release tag with different provenance: hard failure.

During a long update build, remember the converter commit used. Immediately before publication verify that remote `main` still points to that commit. If code changed, abort publication and let the next run rebuild. Do not rebase old build artifacts onto new converter code.

---

## 14. Recommended architecture

```text
programs/upstream/
  zenodo.py
  discover.py
  download.py
  extract.py
  diff.py
  state.py

programs/
  update.py
  prepare_source.py
  build.py
  package_release.py
  publish_release.py

programs/source-state/
  <zenodo-record-id>/
    source.json
    corpus.sha256
    patches.yaml
    excluded.tsv
    known_lossy.tsv
    morph_exceptions.tsv
```

High-level interface:

```bash
python programs/update.py discover
python programs/update.py run --latest --no-publish
python programs/update.py run --record 20328284 --no-publish
python programs/update.py run --latest --publish-if-green
```

---

## 15. Historical integration test

A particularly valuable end-to-end test is to replay the real published update:

```text
0.2: Zenodo 15459134
0.3: Zenodo 20328284
```

Run the updater as though the lock were still on 0.2. It should detect 0.3, select the correct archive despite the filename convention change, verify it, unpack it, diff the sources, regenerate version-specific state, rebuild and validate the TF corpus, and either publish or stop according to the new review policy.

This provides a realistic test of how much source-state adaptation a genuine TLHdig release requires.

---

## 16. Sources

### TLHdig-TF

- https://github.com/alexsosn/TLHdig-TF
- `programs/build.py`
- `programs/tlhdig/__init__.py`
- `programs/tlhdig/paths.py`
- `programs/tlhdig/corpusid.py`
- `programs/tlhdig/repair.py`
- `programs/make_patches.py`
- `programs/verify_patches.py`
- `programs/check_signs.py`
- `programs/check_morph.py`
- `programs/check_markers.py`
- `programs/census.py`
- `.github/workflows/ci.yml`
- `.github/workflows/dataset.yml`

### TLHdig Zenodo records

- Beta 0.2: https://zenodo.org/records/15459134
- Beta 0.3: https://zenodo.org/records/20328284

### Zenodo

- REST API: https://developers.zenodo.org/
- records/version model: https://help.zenodo.org/docs/deposit/about-records/
- version management: https://help.zenodo.org/docs/deposit/manage-versions/
- GitHub integration: https://help.zenodo.org/docs/github/

### Text-Fabric

- data sharing: https://annotation.github.io/text-fabric/tf/about/datasharing.html
- repository/release checkout: https://annotation.github.io/text-fabric/tf/advanced/repo.html
- release ZIP generation: https://annotation.github.io/text-fabric/tf/advanced/zipdata.html

### GitHub

- scheduled workflow events: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- workflow syntax: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- releases REST API: https://docs.github.com/en/rest/releases/releases
- Actions artifacts: https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts
