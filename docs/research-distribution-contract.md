# Research: supported distribution paths for TLHdig-TF

Issue: #47 — define and implement proper supported distribution paths for TLHdig-TF.

This document freezes the **research gate** before distribution design or production packaging changes. It coordinates with #39, which owns release-asset production, repository-retention cost, and old in-tree artifact retirement. This ticket owns the consumer-facing contract: which acquisition path each audience should use, how versions resolve, and how all paths converge on one certified TF release.

Measurements and repository observations below are current as of 2026-09-08. Exact size/time figures are observations, not permanent API constants.

## 1. Current version surfaces do not converge

Current `main` before the active 0.4.0 release lane has:

- `TF_VERSION = 0.3.0`;
- `app/config.yaml` `provenanceSpec.version: "0.3.0"` and `relative: /tf`;
- no automatic optional-provenance module in the app;
- a GitHub release only for tag `tlhdig-0.3_tf-0.2.0`;
- that release has **no attached assets**;
- the live Agora/context-fabric catalog still points TLHdig-TF at `tf/0.1.0`.

The Agora entry is especially unsafe as a version contract. It says to follow the upstream default branch while keeping `tf_path: tf/0.1.0`, so repository identity can advance while the logical version label remains fixed. The recorded catalog measurement for that route is also expensive: 388 MB source, about 4.6 GB compiled cache / 5.1 GB total cache, 2.1 GB peak RSS, and 1,740 seconds first load on its recorded machine.

The active sign-language release lane (#55) is preparing immutable TF 0.4.0 under release-policy `release-v5`; this research branch does not change or advertise that version until it is merged and certified.

**Finding:** there is currently no single release identity shared by app/browser, GitHub Release, and Agora.

## 2. Text-Fabric 13.1 acquisition semantics

This repository pins `text-fabric==13.1.0`; distribution must be designed for the pinned behavior, not for assumed latest TF behavior.

TF distinguishes checkout selectors for app code, main data, and optional modules. Relevant selectors are:

- default `""`: prefer an already cached local copy; otherwise use latest online release; if no release exists, fall back to latest commit;
- `local`: cached data only;
- `latest`: force the latest release;
- `hot`: latest online commit;
- `clone`: a developer checkout under the Git clone area;
- a concrete release tag;
- a concrete commit SHA.

The important consequence is that default `use()` is intentionally **cache-sticky**. It is ergonomic, not a reproducibility guarantee. A previously cached older version may continue to be selected unless the caller explicitly asks for a release/tag or refreshes acquisition.

`use()` and the TF browser can select app code separately from data. Therefore app/data compatibility must be checked explicitly; a correct app `provenanceSpec.version` is necessary but is not by itself a complete consumer-version contract.

## 3. TF-native release packaging already exists

Text-Fabric has supported packaging conventions that TLHdig-TF should reuse instead of inventing a bespoke archive layout.

### Per-data-folder zips

`tf-zip <org>/<repo>/<relative>` creates a version-specific archive such as `tf-0.4.0.zip` from a standard TF directory. TF expects the exact filename/layout when using release-attached data modules.

This is a natural candidate for:

- the main `tf/<version>` module;
- an explicitly requested `tf-provenance/<version>` module if pinned-TF testing confirms the standard module syntax and asset resolution.

### `complete.zip`

TF app collection / zip-all tooling can create `complete.zip`, containing the app plus main data and the checkout metadata needed for fast app acquisition. When attached to the latest release, TF can use it as an express path instead of issuing many per-file GitHub requests.

This makes `complete.zip` the strongest candidate for the ordinary app/browser release artifact, provided a clean-cache integration test proves it against this repository and pinned TF 13.1.0.

`complete.zip` must not silently absorb TLHdig-TF's heavy optional provenance unless the TF app contract explicitly requires it. Current architecture says provenance is opt-in.

## 4. BHSA is useful as a pattern, not a template

BHSA demonstrates several compatible ideas:

- ordinary users call `use('etcbc/bhsa')` or the TF browser and TF downloads into `text-fabric-data`;
- release assets can include `complete.zip`;
- current BHSA releases also expose an `essential` feature manifest usable for selective low-level Fabric loading.

TLHdig-TF differs materially:

- its graph and compiled cache are much larger;
- `srcxml`/source spans form an explicit optional provenance layer;
- `cu` is line-level and the default text representation is transliteration;
- Agora currently loads low-level Fabric directly, not the TF app.

Therefore a BHSA-style **manifest** of essential features is worth testing, but a second independently packaged “minimal corpus” should not be introduced unless measurements show a real advantage that a feature manifest cannot provide.

## 5. Current GitHub Release is not a distribution artifact

The only current release, `tlhdig-0.3_tf-0.2.0`, has no attached assets. GitHub's automatic source tarball/zipball is a repository snapshot, not a TF-native one-version artifact:

- it includes unrelated repository content;
- it is not the `tf-<version>.zip` layout TF's data-sharing helpers produce;
- it does not solve the repository-download-overhead problem from #39;
- it does not give low-level consumers a stable checksum manifest for exactly the bytes they load.

**Finding:** #39's direct release-asset work is still required; #47 must consume that work rather than add a second packaging workflow.

## 6. Agora's live contract is repository-centric and stale

The current Agora context-fabric catalog entry is:

- repository: `alexsosn/TLHdig-TF`;
- `tf_path: tf/0.1.0`;
- acquisition strategy: repository / lazy;
- no release tag/ref pinned in the current entry;
- note says to follow the default branch while retaining the `0.1.0` path.

That is incompatible with the repository's immutable-version direction. A consumer can be on a newer repository commit while still materializing a path named after a much older schema version.

The existing TLHdig-TF integration documentation explains that Agora/Context-Fabric needs only a local TF dataset path and `otype.tf`; it does not require `app/`. That separation remains useful. What must change is **how the correct certified dataset is materialized**.

Research conclusion for planning: Agora should resolve the same machine-readable release identity as other consumers. Whether it downloads a release asset directly or sparse-checks a pinned repository ref is an Agora implementation choice, but it must not independently choose “whatever currently exists at a historical path on main”.

## 7. Optional provenance must stay opt-in

Current app config intentionally has no `moduleSpecs` entry for `tf-provenance`. Ordinary `use()` / browser loading should remain viable with main `tf/<version>` alone.

The provenance layer contains source reconstruction material and is useful for auditing/research, but it is not required for ordinary morphology, section navigation, source-faithful `webLink()`, or standard display.

Research requirement still open for the implementation lane: prove the exact TF 13.1.0 syntax and release-asset naming for loading the provenance directory as a separate module. Do not cargo-cult a BHSA module declaration into `app/config.yaml`.

## 8. Selective loading is a resource feature, not a new corpus

The live Agora measurements and existing integration notes show that `loadAll()` is expensive. Low-level `Fabric` already accepts an explicit feature list, so the lowest-maintenance path is likely:

1. one certified main TF artifact;
2. one generated `essential`/`core-features` manifest naming the features needed for common text/navigation/query work;
3. optional additional features loaded from the same artifact;
4. optional provenance loaded from its separate module only when requested.

The essential set cannot be guessed. It must include all warps and every feature required by:

- default text formats;
- section navigation;
- ordinary document/line identity;
- common word/morphology queries;
- app/browser defaults where low-level consumers want equivalent semantics.

A RED test must reject a manifest that names a nonexistent feature or omits a feature required by the declared core contract.

## 9. Integrity and release identity

The repository already has a stronger internal certification model than ordinary GitHub release metadata:

- immutable TF version directory;
- `BUILD-COMPLETE` / `RELEASE-CERTIFICATION.json` generated by canonical release certification;
- module-aware artifact digest;
- release-policy identity (`release-v5` in the active 0.4.0 lane);
- predecessor-delta declaration.

Distribution should expose, not duplicate, this identity. The release manifest/checksum design should bind at least:

- source version;
- TF version;
- release tag;
- certification policy;
- main artifact digest;
- optional provenance artifact digest;
- exact filenames/checksums of downloadable assets.

The same metadata should drive documentation and Agora registry updates where possible.

## 10. Reproducibility modes must be explicit

There are at least three legitimate user intents and they should not be conflated:

- **stable current**: explicitly acquire the latest published release;
- **reproducible historical**: name a concrete TLHdig-TF release tag/version and then reopen locally/offline;
- **development**: `hot`/commit/clone against current source work.

Default cache-sticky `use()` is convenient but should not be documented as sufficient evidence that a notebook is using the newest release. Conversely, forcing `latest` on every open is hostile to reproducible historical analyses.

## 11. Research questions resolved vs still requiring controlled tests

Resolved enough to plan:

- use TF-native zip layouts rather than a bespoke archive;
- one canonical TF layout should serve app/browser, low-level Fabric, release download, and Agora materialization;
- provenance stays opt-in;
- an essential-feature **manifest** is preferable to a second reduced corpus unless benchmarks prove otherwise;
- GitHub Release and Agora currently lag the app/main artifact version and need one release identity source;
- existing release assets are absent, so source zipballs are not an acceptable final distribution path.

Must be proven before implementation is advertised:

- clean-cache `use()` behavior against an actual TLHdig-TF release carrying `complete.zip`;
- clean-cache TF browser behavior and selected version;
- exact separate-module syntax for `tf-provenance` under Text-Fabric 13.1.0;
- direct extraction + `Fabric(locations=...)` compatibility for each proposed asset;
- the minimal useful essential feature set and its memory/startup benefit;
- Agora's preferred release-asset/ref metadata shape after its current stale entry is corrected;
- offline reopen semantics after successful pinned acquisition.

## 12. Research gate conclusion

TLHdig-TF does not need another package manager. It needs one certified version identity projected consistently into TF-native release artifacts, app/browser resolution, low-level selective loading, and Agora.

The main architectural risk is **version divergence**, not archive creation: today main/app, GitHub Release, and Agora can all refer to different TF generations. The plan must make that state machine-checkably impossible for every advertised supported path while preserving explicit developer and historical modes.
