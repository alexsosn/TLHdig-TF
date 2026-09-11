# Research: current-build validation manifest (#116)

## Scope

Issue #115 replaces the pre-alpha immutable-release model with one replaceable current Text-Fabric artifact. This research isolates the historical release-certification machinery from the corpus/app validation that still protects user-visible correctness.

No production behavior changes in this phase.

## Current artifact/loading contract

`programs/tlhdig/__init__.py` defines `TF_VERSION = "0.4.0"`; `programs/build.py`, `programs/census.py`, the checkers, and `app/config.yaml` all resolve the current main module as `tf/<TF_VERSION>`. The app explicitly advertises `provenanceSpec.relative: /tf` and `version: "0.4.0"`. The optional provenance module is `tf-provenance/<TF_VERSION>`.

For #116, changing the physical loading path is unnecessary. Keep `tf/0.4.0` and `tf-provenance/0.4.0` as the current mutable pre-alpha paths. The parent #115 cleanup can remove older sibling directories without forcing a simultaneous Text-Fabric loader migration. The version string describes the current schema/converter line during this pre-alpha interval; it is no longer an immutable-release promise.

## What the present certification stack does

### `programs/release_check.py`

The orchestrator currently mixes three concerns:

1. substantive validation commands;
2. build-run stability checks;
3. historical release-policy/certificate semantics.

Its substantive gates are:

- corpus identity;
- repair manifest;
- sign round-trip;
- morphology;
- structure;
- sign-language conservation;
- manuscript joins;
- Contract-A graph/source conservation;
- marker conservation;
- tag inventory;
- provenance split;
- cuneiform alignment;
- locked external sign-reference acquisition/validation;
- app validation;
- fresh-process census/load.

Those remain valuable under #115.

The historical/release-only additions are `predecessor-delta`, exact equality with the versioned `release_policy.REQUIRED_*` sets, and the later certificate/stamp publication contract. `code-tree-stable` is not intrinsically historical: running a long validator while the checkout changes could produce misleading evidence. Its useful invariant should survive as a simple validator pre/post condition rather than as a release-policy gate.

### `programs/tlhdig/certification.py`

This module is a state machine whose successful output is `RELEASE-CERTIFICATION.json` plus `BUILD-COMPLETE`. It hashes release inputs, records known-defect policy modes, requires the complete versioned release gate set, checks artifact/input stability, and cryptographically binds the certificate through `stamp.write()`.

The generic ideas worth retaining are small: deterministic input/output hashing, failure on a required gate skip, and pre/post stability. The release-certificate object itself is no longer required.

### `programs/tlhdig/release_policy.py`

This file freezes `release-v3`, `release-v4`, and `release-v5`, predecessor-adoption baselines, historical gate/input sets, and mode policy. It exists so old certification manifests can remain verifiable under later code. That is exactly the compatibility burden #115 removes for active pre-alpha validation.

### `release_delta.py` / `programs/release-delta.json`

These prove that a new immutable generated version differs from its predecessor only by an expected declared delta. Once `main` carries one mutable current artifact and Git history is the development history, a predecessor artifact is not an input to deciding whether the current graph is correct. These are removable from active validation.

### `programs/tlhdig/stamp.py` and `programs/check_stamp.py`

`stamp.py` contains two generations of compatibility logic:

- a legacy digest-only `BUILD-COMPLETE` format;
- a full module-aware digest bound to `RELEASE-CERTIFICATION.json`, a versioned release policy, predecessor evidence, mode, known-defect baselines, input hashes, and code commit.

The byte-drift invariant remains necessary, but the compatibility parser and recursive certificate verification do not. A current manifest can directly enumerate/hash the two current output trees and current reproducibility inputs.

`check_stamp.py` is therefore better replaced by a manifest verifier rather than taught another certificate generation.

### Workflows

`.github/workflows/certify-dataset.yml` is write-enabled (`contents: write`), runs the full historical certifier, commits certificate/report evidence back to the branch, and contains branch/ref/concurrency protections needed only because the validation workflow mutates Git history. Under #115 that workflow has no remaining product responsibility.

`.github/workflows/dataset.yml` is still useful: it is an on-demand/monthly clean rebuild on a hosted runner. It should run the current validator after `build.py`, then upload reports. It need not publish a certificate commit.

`.github/workflows/ci.yml` already invokes most validators independently on the committed current artifact. Its `check_stamp.py` step should become current-manifest verification. The comments that call the corpus an immutable release should be updated later in the implementation.

## Test ownership audit

Tests fall into two classes.

### Retain/reframe

Tests that prove the following remain current-build requirements must survive even if their filenames change:

- manuscript-join conservation is in the canonical validator;
- sign-language conservation is in the canonical validator;
- all substantive command gates are present exactly once;
- external sign-reference validation cannot turn an explicit unavailable/skip state into a successful full current-build validation;
- dirty/changing executable inputs cannot produce a successful current manifest;
- output mutation during validation prevents success;
- reproducibility-input mutation during validation prevents success;
- generated-output modification after validation invalidates verification;
- provenance/main-module membership is part of artifact identity.

### Retire

Assertions whose only contract is one of the following should be deleted rather than translated mechanically:

- current policy name equals `release-v5`;
- historical `release-v3`/`release-v4` manifests remain verifiable;
- predecessor-delta is mandatory;
- `releaseDelta` is a mandatory current input;
- historical adoption baseline hashes remain frozen;
- `BUILD-COMPLETE` can distinguish legacy census-only versus full certificate forms;
- `RELEASE-CERTIFICATION.json` recursively matches the stamp;
- research-ready versus regression-valid is encoded as a release-certificate compatibility mode.

Historical research/plan Markdown can remain as development history; it must not be imported by active current-build code.

## Current reproducibility inputs

The current repository already pins:

- source inventory/content via `programs/corpus.sha256`;
- repair decisions via the repair manifest;
- external sign-list identities via `programs/signrefs.lock.json`;
- direct Python dependencies and supported Python `3.13.1` in `requirements.txt`.

`requirements.txt` pins Text-Fabric 13.1.0, lxml 5.4.0, pytest 8.3.4, and PyYAML 6.0.2. Transitive locking is incomplete and remains owned by #106. The current manifest should hash this dependency specification now, without pretending it is a full environment lock.

## Minimal current-build manifest

A non-recursive manifest can be generated only after all required gates pass. It should contain:

- schema identifier;
- `sourceVersion` and `tfVersion`;
- current main/provenance relative paths;
- producing code commit as provenance;
- SHA-256 identities of `corpus.sha256`, repair manifest, `signrefs.lock.json`, and `requirements.txt`;
- deterministic per-file SHA-256 values for the current main/provenance output trees, excluding the manifest itself and derived `.tf/` caches;
- deterministic aggregate tree digest for quick comparison;
- the ordered substantive validation gate names and a success marker.

Per-file hashes make an altered/missing/extra generated file diagnosable and satisfy #115's tree/file-hash requirement. Including module-relative paths in the aggregate digest prevents moving a feature between main and provenance from preserving identity.

The manifest should not contain a predecessor version/digest, historical policy name, certificate hash, or mutable self-hash.

## Code identity and the commit-cycle problem

The old write-enabled workflow could validate commit A, create certification files, then commit those files as commit B. That created the need for elaborate branch/ref/freshness reasoning.

The current manifest should treat `codeCommit` as provenance for the checkout that produced/validated the bytes, while verification of a committed artifact is based on explicit reproducibility-input/output hashes. It must not require `codeCommit == current HEAD`, because committing the generated manifest itself necessarily creates a later Git commit. Ordinary CI independently tests the code at current HEAD.

During manifest creation, however, the validator should reject a dirty tracked source/code/config tree (excluding generated TF/provenance/report outputs) and verify that HEAD did not change across the gate run. This prevents the manifest from claiming a checkout identity that was not stable while validation ran.

## Unknown/extra output behavior

Current-output identity must be closed-world for regular files below `tf/<TF_VERSION>` and `tf-provenance/<TF_VERSION>` except:

- `BUILD-MANIFEST.json` itself;
- Text-Fabric's derived `.tf/` cache directories.

An extra regular file, deleted file, changed file, or main↔provenance move must invalidate verification. Symlinked output entries should fail closed rather than be followed to arbitrary filesystem content.

## Migration boundary

#116 should change validation/certification mechanics but should not simultaneously delete `tf/0.1.0`–`0.3.0` or rename `tf/0.4.0`; that destructive repository cleanup belongs to the parent #115 after current-manifest validation exists. This sequencing gives #115 the requested safety gate before deleting historical directories.

`publish_dataset.sh` may remain only as a deliberate staging helper, but it must require the current manifest instead of historical full certification. Snapshot/tag/release publication policy is outside #116.

## Research conclusion

The release certificate can be replaced without weakening corpus correctness. The safe cut is to preserve all 16 substantive external gates plus checkout/output/input stability, replace the certificate/stamp pair with one direct build manifest and verifier, remove predecessor/historical policy dependencies from active code/tests, retire the write-enabled certification workflow, and make the existing dataset workflow run the new validator.
