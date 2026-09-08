# Plan: supported distribution contract for TLHdig-TF

Issue: #47. Research gate: `docs/research-distribution-contract.md`.

This document freezes the **plan gate** before RED tests or production distribution changes. #39 owns the workflow/mechanics that actually build and attach release assets; this plan defines the consumer-visible contract those assets must satisfy.

## 1. Design principles

1. **One certified release identity.** App/browser, downloadable assets, low-level Fabric, Agora, and documentation must all derive from the same machine-readable version metadata.
2. **One canonical TF layout.** Do not maintain separate “browser corpus”, “Agora corpus”, and “manual-download corpus”. All are views or packages of the same `tf/<TF_VERSION>` bytes.
3. **Provenance is opt-in.** `tf-provenance/<TF_VERSION>` is a separate compatible module, never an implicit dependency of ordinary app/browser use.
4. **Selective loading is a manifest, not a fork.** A core/essential feature list names a subset of the canonical main artifact; it does not create a second independently versioned corpus unless benchmarks later prove that unavoidable.
5. **Stable, historical, and development modes are explicit.** Default cache convenience must not be confused with reproducibility.
6. **Fail closed on divergence.** A release is not publishable if tag, TF version, app version, asset metadata, certification, or Agora metadata disagree.
7. **Reuse Text-Fabric-native formats.** Prefer `complete.zip` and standard per-folder TF zips over bespoke archive structures.

## 2. Canonical machine-readable release metadata

Introduce one generated/validated repository metadata document, provisionally `distribution.json`, whose schema is owned by #47 while asset production consumes it under #39.

Required fields:

```json
{
  "sourceVersion": "0.3",
  "tfVersion": "X.Y.Z",
  "releaseTag": "tlhdig-0.3_tf-X.Y.Z",
  "certificationPolicy": "release-vN",
  "main": {
    "relative": "tf",
    "version": "X.Y.Z",
    "artifactDigest": "sha256:...",
    "asset": "tf-X.Y.Z.zip"
  },
  "provenance": {
    "relative": "tf-provenance",
    "version": "X.Y.Z",
    "artifactDigest": "sha256:...",
    "asset": "tf-provenance-X.Y.Z.zip",
    "optional": true
  },
  "app": {
    "completeAsset": "complete.zip"
  },
  "essential": {
    "manifest": "essential"
  }
}
```

Exact digest values are generated only after canonical certification. The metadata checker must compare rather than trust duplicated version strings.

The metadata file is **not** a second certification system. `RELEASE-CERTIFICATION.json` remains authoritative for the certified dataset digest/policy; distribution metadata projects that identity into consumer filenames and tags.

## 3. Distribution matrix

| Audience | Canonical supported path | Version semantics | Physical source |
| --- | --- | --- | --- |
| Interactive TF user | `use("alexsosn/TLHdig-TF", checkout="latest")` for current stable; explicit release tag for reproducible history | published release or explicit tag | `complete.zip` / TF release machinery |
| TF browser user | `text-fabric alexsosn/TLHdig-TF --checkout=latest` for current stable; explicit tag where supported for historical work | same as app | same release / `complete.zip` |
| Python low-level analyst | downloaded/extracted main module + `Fabric(locations=...)`; optionally TF module acquisition | explicit TF version | `tf-X.Y.Z.zip` |
| Resource-sensitive analyst | same main artifact, loading feature names from generated `essential` manifest | explicit TF version | main artifact only |
| Provenance-heavy researcher | main artifact plus explicit separate provenance module | identical TF version required | `tf-X.Y.Z.zip` + `tf-provenance-X.Y.Z.zip` |
| Offline/manual consumer | download assets + checksum/metadata, extract, verify, load locally | explicit release tag/version | GitHub Release assets |
| Developer/contributor | shallow/full source checkout + local `Fabric` / rebuild | commit/branch (`clone`/`hot`) | Git repository |
| Agora / automation | registry points to machine-readable certified release identity; materializer obtains same main artifact or an exact pinned equivalent | explicit release version/ref, never floating historical path | release asset preferred; pinned repository ref only if implementation requires |

The public docs must explain that default empty TF checkout can reuse an existing cache. `latest` is the supported “current stable” acquisition request; a concrete tag is the supported reproducibility request; `hot`/clone are development requests.

## 4. Release assets

The release produced by #39 should expose the minimum non-overlapping assets justified by TF behavior:

### Required candidate: `complete.zip`

Purpose: efficient app/browser acquisition including app code and canonical main data.

Acceptance:

- produced by supported TF collection tooling or byte-for-byte compatible layout;
- clean-cache `use()` consumes it successfully under pinned Text-Fabric 13.1.0;
- app and loaded data report the expected same TF version;
- optional provenance is absent unless explicitly requested;
- offline reopen works from the populated TF cache.

### Required candidate: `tf-<version>.zip`

Purpose: standard one-version main-module artifact for manual/low-level consumers and tooling.

Acceptance:

- standard TF zip layout;
- extracts into a directly loadable version directory;
- all files are covered by distribution checksum metadata;
- artifact bytes correspond to the certified main-module digest.

### Conditional but strongly expected: `tf-provenance-<version>.zip`

Purpose: explicit optional source-provenance module.

Acceptance before publication:

- exact TF 13.1 module syntax tested from a clean cache;
- version must equal the main artifact version;
- ordinary app/browser loading remains green without it;
- checksum/digest coverage is independent and complete.

No other archive format should be introduced without a measured consumer requirement.

## 5. Essential/core feature manifest

Generate an `essential` text file from canonical feature metadata plus structural requirements, not by hand-maintained duplication.

Minimum algorithm:

1. always include TF warps needed to load/navigate (`otype`, `oslots`, `otext` where appropriate to the loader contract);
2. include section features required by `otext`;
3. include every feature referenced by default text formats;
4. include the minimal document/line/word identity and common morphology feature set documented for low-resource analysis;
5. validate every named feature exists in the main module for current `TF_VERSION`;
6. do not include provenance-only features from `tf-provenance`;
7. emit deterministically and gate drift in CI.

Research/performance gate before claiming value: compare main `loadAll()` with `Fabric.load("file:.../essential")` (or exact pinned-TF equivalent) for startup, memory, and cache footprint on a clean environment. If improvement is immaterial, keep selective loading documented but do not over-market it.

## 6. Version invariant

A deterministic checker must enforce all repository-local relationships:

- `tlhdig.TF_VERSION` == app `provenanceSpec.version`;
- current main directory is `tf/<TF_VERSION>`;
- optional provenance directory, if advertised, is `tf-provenance/<TF_VERSION>`;
- `distribution.json.tfVersion` == `TF_VERSION`;
- `distribution.json.sourceVersion` == `SOURCE_VERSION`;
- release tag parses to the same source + TF versions;
- certification policy/digest in distribution metadata match the canonical certification evidence;
- every advertised asset filename encodes the same TF version where appropriate;
- essential manifest names only main-module features;
- no default app `moduleSpecs` silently makes provenance mandatory.

Networked release/Agora checks consume the same local metadata but run separately so ordinary unit CI does not depend on GitHub availability.

## 7. Release publication sequence

The safe sequence is:

1. implement/merge corpus changes and allocate a new immutable `TF_VERSION`;
2. build exact immutable `tf/<version>` + compatible optional provenance;
3. run full canonical certification and commit certification evidence;
4. generate/validate distribution metadata and essential manifest against those exact bytes;
5. #39 packaging workflow creates TF-native assets from the certified directories;
6. clean-consumer integration validates assets before public support claims;
7. publish/tag GitHub Release on the exact reviewed merged commit;
8. update Agora from the same machine-readable release metadata;
9. verify Agora resolves the same version/digest;
10. only then update docs/status to call the path supported.

A GitHub Release must never target a pre-merge PR commit or a tree lacking the final certification evidence.

## 8. Agora contract

Replace the current floating `tf/0.1.0` + default-branch semantics with one of two acceptable implementations, in preference order:

### A. Release-asset materialization

Agora registry records:

- repository;
- release tag / TF version;
- main asset name or release-metadata pointer;
- expected digest/checksum.

Materializer downloads/verifies/extracts the standard main TF artifact and hands the directory to Context-Fabric.

### B. Exact-ref sparse checkout

If Agora cannot yet consume assets, pin an exact tag/SHA and `tf_path: tf/<same version>`. The registry checker must reject a mismatched path/ref/version.

In either case Agora must not follow a floating default branch while retaining a historical version path.

Agora is a consumer of the corpus release contract, not a second release authority.

## 9. Cache/update contract

Document and test:

- `latest`: explicit current published release acquisition;
- concrete tag: reproducible version acquisition;
- `local`: no-network reopen of already acquired data;
- default empty checkout: convenience/cache-first behavior, not guaranteed newest;
- `hot` / commit SHA / clone: development only.

Clean-environment tests must isolate `TF_DATA`/home/cache locations so maintainer caches cannot make an invalid path pass.

## 10. Integrity contract

A release-level checksum manifest should list SHA-256 for each downloadable asset. It must be derivable from the exact uploaded bytes, because internal module digests and archive-byte digests answer different questions.

Verification layers:

1. **archive checksum**: downloaded file was not changed;
2. **module digest / certification**: extracted TF module is the certified corpus artifact;
3. **release metadata**: tag/version/app/asset relationships are coherent.

Do not claim that a checksum of `complete.zip` alone proves the internal canonical TF digest unless extraction is also compared with certification metadata.

## 11. Historical-release retention

#39 owns when old `tf/*` directories leave `main`. #47 requires that removal not make old analyses irreproducible.

Before retiring a published version from the Git tree:

- its immutable GitHub Release assets must exist;
- asset checksums and certification metadata must be retrievable;
- low-level extracted load must pass;
- app/history acquisition behavior must be documented or a manual asset path supplied;
- predecessor certification must be able to materialize its pinned baseline without relying on the removed in-tree directory.

## 12. RED gate to implement next

Before packaging/config production code, add failing deterministic tests for:

1. no canonical `distribution.json` contract currently exists;
2. current/live release version can diverge from app/TF version without a local invariant;
3. asset names/tag can disagree with `TF_VERSION`;
4. a distribution manifest can advertise missing checksums/digests;
5. an essential feature manifest can name nonexistent or provenance-only features;
6. default app config could accidentally add the provenance module;
7. an extracted standard main-module fixture must be directly Fabric-loadable;
8. version-mismatched provenance must be rejected;
9. a consumer test must be able to force an isolated cache/home rather than inherit maintainer state;
10. an Agora metadata projection with `tf_path` version != release version must fail validation.

Networked/hosted RED tests should separately demonstrate the current real-world mismatch (GitHub Release 0.2.0 / current main 0.3.0 / Agora 0.1.0 at research time) without making ordinary CI permanently depend on live APIs.

## 13. Production ownership / conflict boundaries

- **#47 owns:** metadata schema, invariant checker, essential manifest contract, consumer matrix, clean-consumer tests, docs of supported paths.
- **#39 owns:** asset build/upload workflow, repository size/retention mechanics, old-version tree cleanup.
- **canonical release certification owns:** module digest and release-policy evidence.
- **Agora repo owns:** registry/materializer changes; TLHdig-TF tests only the projection/metadata it exports.
- **#44/#45 own:** final browser support and end-to-end browser/app gate.
- **#46 owns:** researcher manual integration once distribution behavior is real.

Do not implement duplicate asset workflows in #47.

## 14. Independent adversarial review questions

Final review must attempt to break the design by asking:

- Can a warm cache make `use()` report success while selecting the wrong release?
- Can app code and main data resolve from different releases?
- Can `latest` or a floating Agora ref silently change a reproducible analysis?
- Does `complete.zip` actually contain the certified bytes or merely a plausible version directory?
- Can optional provenance become mandatory through app config or an over-broad complete bundle?
- Does `essential` omit a feature needed by default formats/section navigation?
- Are archive checksums computed before the final uploaded bytes are known?
- Can Agora point to a different corpus generation while retaining a matching-looking label?
- Can old release retrieval fail after Git cleanup?
- Is any advertised path untested from an isolated empty environment?

Any blocking finding restarts implementation → tests → fresh independent review.
