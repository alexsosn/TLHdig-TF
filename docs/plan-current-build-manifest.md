# Plan: replace release certification with current-build validation (#116)

Status: frozen implementation plan after `docs/research-current-build-manifest.md`.

## 1. Scope and migration order

This PR changes the active validation contract only. It does not delete historical `tf/0.1.0`–`0.3.0` trees and does not rename `tf/0.4.0`. The parent #115 will perform that destructive cleanup after this PR establishes direct current-artifact hash verification.

The current artifact remains:

- main: `tf/<TF_VERSION>` (`tf/0.4.0` today);
- optional provenance: `tf-provenance/<TF_VERSION>`.

These directories are mutable pre-alpha build outputs. `TF_VERSION` remains a schema/converter identity, not an immutable-publication promise.

## 2. New current-build primitives

Add `programs/tlhdig/build_manifest.py` with no release-policy imports.

Constants:

- `MANIFEST = "BUILD-MANIFEST.json"`;
- `SCHEMA = 1`;
- aggregate hash algorithm identifier local to this manifest schema.

Functions must cover:

1. SHA-256 of a regular input file;
2. closed-world inventory of regular output files in main/provenance modules;
3. deterministic aggregate output hash that includes module label + relative path + file digest;
4. deterministic input identities;
5. manifest construction/writing only after successful validation;
6. verification against current input files, current output files, expected current paths/version, and expected gate names.

Output inventory rules:

- include every regular file recursively under both current module directories;
- exclude only `tf/<TF_VERSION>/BUILD-MANIFEST.json` itself and paths under derived `.tf/` cache directories;
- reject symlinks rather than following them;
- preserve module membership in keys/hash input;
- missing provenance directory is allowed only if the manifest itself says no provenance files; an unexpected add/remove changes identity.

Manifest shape:

```json
{
  "schema": 1,
  "sourceVersion": "0.3",
  "tfVersion": "0.4.0",
  "codeCommit": "<40 hex>",
  "paths": {
    "main": "tf/0.4.0",
    "provenance": "tf-provenance/0.4.0"
  },
  "inputs": {
    "corpusManifest": "sha256:...",
    "repairManifest": "sha256:...",
    "exclusions": "sha256:...",
    "signrefLock": "sha256:...",
    "dependencies": "sha256:..."
  },
  "outputs": {
    "algorithm": "tlhdig-current-tree-v1",
    "digest": "sha256:...",
    "files": {
      "main:LICENSE": "sha256:...",
      "main:otype.tf": "sha256:...",
      "provenance:srcxml.tf": "sha256:..."
    }
  },
  "validation": {
    "success": true,
    "gates": ["..."]
  }
}
```

The exact JSON ordering/indentation is deterministic. `codeCommit` is provenance, not a requirement that later verifier HEAD equal the producing commit; the explicit input/output hashes are the active drift contract.

## 3. Canonical current validator

Replace `programs/release_check.py` with `programs/validate_current.py`.

Define one ordered `GATES` tuple containing exactly these substantive commands:

1. `corpus-identity` → `programs/check_corpus_identity.py`;
2. `repair-manifest` → `programs/verify_patches.py`;
3. `sign-round-trip` → `programs/check_signs.py`;
4. `morphology` → `programs/check_morph.py`;
5. `structure` → `programs/check_structure.py`;
6. `sign-language` → `programs/check_sign_language.py`;
7. `manuscript-joins` → `programs/check_manuscript_joins.py`;
8. `contract-a-graph` → `programs/check_contract_a_graph.py`;
9. `marker-conservation` → `programs/check_markers.py`;
10. `tag-inventory` → `programs/check_tags.py`;
11. `provenance-split` → `programs/check_provenance_split.py`;
12. `alignment` → `programs/check_alignment.py`;
13. `fetch-signrefs` → `programs/fetch_signrefs.py --mode release`;
14. `check-signrefs` → `programs/check_signrefs.py --mode release`;
15. `app` → `programs/check_app.py`;
16. `census` → `programs/census.py`.

There is no predecessor gate and no versioned release-policy registry.

`validate_current.py` will:

- remove a stale current `BUILD-MANIFEST.json` before starting, so a failed run cannot leave apparent success;
- reject tracked source/code/config changes before validation, excluding generated `tf/**`, `tf-provenance/**`, and `reports/**`;
- resolve a full Git commit identity from HEAD, with `TLHDIG_CODE_COMMIT`/`GITHUB_SHA` only as consistent fallbacks;
- snapshot input hashes and output inventory before gates;
- run every required gate sequentially;
- for external sign-reference gates, require explicit status `passed` as well as exit code zero; unavailable/skipped is failure for complete current-build validation;
- fail immediately on any other non-zero gate;
- recompute inputs/outputs after all gates and require exact stability;
- require tracked code/config to remain clean and Git HEAD unchanged;
- write `BUILD-MANIFEST.json` only after all of the above pass;
- immediately verify the written manifest before returning success.

Gate result history does not need to be persisted individually: the manifest is written only after the complete fixed gate tuple passes and stores that tuple plus `success: true`. Failed runs remain diagnosable through command output and existing reports.

## 4. Independent verifier

Add `programs/check_build_manifest.py`.

It loads `tf/<TF_VERSION>/BUILD-MANIFEST.json` and calls the pure verifier with the canonical current input map and canonical gate names. It returns non-zero for:

- missing/malformed/unsupported manifest;
- wrong source/TF version or current paths;
- changed/missing/extra main or provenance file;
- main↔provenance move;
- changed current reproducibility input;
- missing/extra/reordered current gate contract;
- invalid success/code-commit fields;
- symlink in current output inventory.

It does not parse historical certificate/stamp formats.

## 5. Build/staging integration

Update `programs/build.py`:

- remove `stamp` import;
- before writing, remove stale `BUILD-MANIFEST.json`, legacy `BUILD-COMPLETE`, and legacy `RELEASE-CERTIFICATION.json` from the current output if present;
- final instruction becomes `run programs/validate_current.py`;
- comments say current pre-alpha artifact, not immutable release.

Update `programs/publish_dataset.sh`:

- describe itself as staging the validated current generated artifact;
- require `python3 programs/check_build_manifest.py`;
- keep cache removal, GitHub file-size guard, and explicit `git add -f` of current main/provenance modules.

No snapshot/tag creation is added.

## 6. Workflow integration

Update `.github/workflows/dataset.yml` to run `programs/validate_current.py` after build.

Update `.github/workflows/ci.yml` to replace `check_stamp.py` with `check_build_manifest.py` and update immutable-release wording.

Delete `.github/workflows/certify-dataset.yml`. No replacement write-enabled workflow is created.

`source-path-evolution.yml` is outside this ticket unless it imports deleted release modules.

## 7. Remove obsolete active machinery

Delete active code whose only purpose is historical release certification:

- `programs/release_check.py`;
- `programs/check_stamp.py`;
- `programs/release-delta.json`;
- `programs/tlhdig/certification.py`;
- `programs/tlhdig/release_policy.py`;
- `programs/tlhdig/release_delta.py`;
- `programs/tlhdig/certification_ref.py` if no remaining non-certification caller exists;
- certificate-only tests (`test_certification.py`, `test_stamp.py`, `test_release_delta*.py`, `test_certification_ref.py` if present).

Also remove legacy `BUILD-COMPLETE` and `RELEASE-CERTIFICATION.json` from the current `tf/<TF_VERSION>` directory. Historical artifact directories are untouched in this PR.

Historical docs may retain descriptions as historical records. Operational docs/tests must not direct users/developers to deleted commands.

## 8. TDD / RED gates

Before production implementation, add failing tests for:

- `build_manifest` output inventory distinguishes main/provenance and detects changed/extra/missing files;
- current manifest input hashing detects an input edit;
- malformed/symlinked outputs fail closed;
- validator gate set contains all 16 substantive gates and no predecessor gate;
- manuscript and sign-language checks remain required;
- sign-reference skip with exit zero is still a failed complete validation;
- output/input mutation during a gate prevents manifest creation;
- dirty/changing checkout prevents manifest creation;
- successful synthetic validation writes a manifest that the verifier accepts;
- verifier rejects output drift after success;
- workflows no longer reference historical certification/stamp commands and no dedicated `certify-dataset.yml` remains.

Hosted PR CI must show the RED failure before production files are added/replaced.

## 9. Test gate after implementation

Run on the exact implementation head:

```text
python -m pytest programs/tests -q
```

Then rely on PR CI for the repository's ordinary corpus gates against the committed current artifact. The new `check_build_manifest.py` CI step must verify the committed current manifest after the old certificate files are removed.

The full `dataset.yml` rebuild is useful hosted evidence but is not required to mutate the PR branch; it validates that a clean checkout can rebuild and validate the current artifact without predecessor data.

## 10. Independent adversarial review

Review the exact final diff from a fresh context and attack these failure modes:

- a substantive former release gate disappeared accidentally;
- current validation can succeed after an explicit external-data skip;
- manifest inventory ignores extra files or module membership;
- manifest recursively hashes itself;
- generated `.tf/` caches create platform-dependent drift;
- symlinks escape the artifact tree;
- dirty/changing code can be recorded as a clean producing commit;
- the verifier incorrectly requires producing commit == later manifest commit;
- old certificate/predecessor imports remain active;
- deleting the write-enabled workflow also deleted the only clean rebuild path;
- current staging can commit unvalidated bytes.

Any blocking finding requires fix → tests → fresh exact-head review.
