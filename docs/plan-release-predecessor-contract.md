# Plan: predecessor-aware release certification

**Issue:** #38  
**Research prerequisite:** `docs/research-release-predecessor-contract.md`

Execution protocol: **research → plan → RED → implementation → test → logically independent adversarial review**. Production certification code does not change before this plan is committed.

## 1. Compatibility boundary

Introduce canonical policy **`release-v4`**. Preserve `release-v3` as a supported historical full-certification policy so the currently committed 0.3.0 evidence continues to verify before post-merge re-certification.

Policy v4 keeps the existing module-aware artifact digest algorithm (`tlhdig-tf-modules-v2`) and the existing modes/baselines. It changes two policy-owned sets:

- required gate: add `predecessor-delta`;
- required input: add `releaseDelta`.

`stamp.check(..., require_full=True)` must select the recorded policy contract from the manifest rather than demanding that every historical manifest equal the latest `POLICY` constant.

Do **not** weaken historical verification: a release-v3 manifest is valid only against the exact v3 gate/input/fidelity contract it actually recorded. Unknown policies remain failures.

## 2. Adoption boundary

Set one explicit policy-v4 predecessor baseline:

```text
DELTA_BASELINE_TF_VERSION = 0.3.0
```

Commit `programs/release-delta.json` for current 0.3.0 as:

```json
{
  "schema": 1,
  "tfVersion": "0.3.0",
  "baseline": true
}
```

Baseline mode is valid **only** when both the spec and current `TF_VERSION` equal the policy constant above. A later release cannot opt out by writing `"baseline": true`.

No published 0.2.0 artifact is modified. The existing 0.3.0 `.tf` feature bodies are not modified. After merge, the existing canonical certification workflow may replace only 0.3.0 certification metadata with release-v4 evidence because 0.3.0 has not yet been published as a GitHub release.

## 3. Future release-delta specification

For every post-baseline TF version require:

```json
{
  "schema": 1,
  "tfVersion": "<candidate>",
  "predecessorVersion": "<previous certified release>",
  "predecessorDigest": "sha256:<64 hex>",
  "expectedChanges": [
    "main:feature.tf",
    "provenance:feature.tf"
  ]
}
```

Validation rules:

- candidate version must equal runtime `TF_VERSION` and current artifact directory name;
- predecessor version must be non-empty and differ from candidate;
- predecessor digest must be a valid SHA-256 module-aware artifact digest;
- expected changes must be a sorted duplicate-free list of module-qualified `.tf` basenames;
- module is exactly `main` or `provenance`;
- arbitrary paths, globs and wildcards are rejected.

The intended set is **exact**, not an upper-bound allowlist. Observed changes must equal it.

## 4. Delta comparison semantics

Add a small `tlhdig.release_delta` module with no network behavior.

For each module (`tf/<version>`, `tf-provenance/<version>`):

1. enumerate serialized `*.tf` files;
2. added/removed files count as changes;
3. for ordinary node/edge features compare bytes after the TF metadata/body separator (`\n\n`);
4. for `otext.tf`, compare config lines after excluding only `@version=` and `@dateWritten=`;
5. qualify every changed name as `main:<name>` / `provenance:<name>`;
6. sort deterministically.

Before comparing, compute `stamp.full_digest(predecessor)` and require exact equality with the pinned `predecessorDigest`. Wrong baseline bytes are a hard failure.

Any unreadable/malformed TF feature is a hard failure.

This gate intentionally answers only *where serialized graph/config data changed*. Issue-specific semantic correctness remains owned by the feature ticket's tests/gates.

## 5. Predecessor materialization contract

The checker resolves the default predecessor at `ROOT/tf/<predecessorVersion>`; the matching provenance module follows the existing `tf-provenance/<version>` convention.

It does not fetch predecessors. If the predecessor is absent, certification fails explicitly.

This leaves acquisition to #39/#47: after old versions are retired from the Git tree, the release workflow may materialize a pinned GitHub release asset at that same temporary layout before invoking the unchanged delta checker. The pinned digest prevents an incorrect materialization from being accepted.

## 6. Gate evidence and cryptographic binding

Extend `certification.GateOutcome` with optional structured evidence. `certification.certify()` copies evidence into that gate's manifest row.

The `predecessor-delta` gate records at least:

For baseline adoption:

```json
{
  "baseline": true,
  "tfVersion": "0.3.0",
  "expectedChanges": [],
  "actualChanges": []
}
```

For later releases:

```json
{
  "baseline": false,
  "tfVersion": "...",
  "predecessorVersion": "...",
  "predecessorDigest": "sha256:...",
  "expectedChanges": [...],
  "actualChanges": [...]
}
```

A passed v4 predecessor gate without structurally valid evidence must not verify as a publishable full certification.

`release-delta.json` is also hashed under manifest `inputs.releaseDelta`, so both the declared policy and the comparison result are bound by `BUILD-COMPLETE`.

## 7. `release_check.py` integration

- add `predecessor-delta` to `GATES` before the final code-tree-stability gate;
- add `releaseDelta` to `release_inputs()`;
- implement the predecessor gate as an internal gate analogous to `code-tree-stable`;
- a `release_delta` validation/comparison exception produces `GateOutcome("failed", 1, evidence={"error": ...})`;
- no skip state exists for predecessor comparison;
- leave subprocess gate semantics unchanged.

The final code-tree-stability gate remains last.

## 8. Workflow integration

Update `.github/workflows/certify-dataset.yml` path triggers to include:

- `programs/release-delta.json`;
- `programs/tlhdig/release_delta.py`.

Do not add network acquisition in this ticket.

The post-merge certification workflow remains the canonical writer of generated `BUILD-COMPLETE` / `RELEASE-CERTIFICATION.json`. The implementation PR must not hand-edit those generated files.

## 9. RED gate

Before production changes add tests that fail against current main for the intended reasons:

### Comparator/spec RED

- current non-baseline spec with wrong/missing predecessor digest is rejected;
- unexpected changed feature is rejected;
- declared change that did not occur is rejected;
- added/removed feature is detected;
- provenance-module change is module-qualified and detected;
- node/order change in `otype.tf` is detected;
- `otext` section/config change is detected;
- only `@version` / `@dateWritten` changes in `otext` do not count;
- future `baseline: true` is rejected.

### Certification/policy RED

- current policy is release-v4 with `predecessor-delta` and `releaseDelta` required;
- v4 full stamp requires valid predecessor gate evidence;
- historical release-v3 full manifest still verifies after v4 becomes current;
- unknown policy fails;
- canonical `release_check` refuses to certify when predecessor gate fails;
- successful v4 certification records gate evidence and releaseDelta input identity.

RED is valid only when failures show that current code lacks the predecessor contract/policy compatibility, not because fixtures are malformed.

## 10. GREEN / full test gate

Run focused tests first, then the full repository suite:

```text
python -m pytest programs/tests/test_release_delta.py \
  programs/tests/test_certification.py \
  programs/tests/test_release_check.py \
  programs/tests/test_stamp.py -q
python -m pytest programs/tests -q
```

Then require normal PR CI green, including corpus identity, repairs, sign round-trip, morphology, app, stamp, tag, provenance, alignment and external sign-reference gates.

Because the PR changes no `.tf` feature data, ordinary CI must continue to validate the existing release-v3 0.3.0 stamp through historical-policy support.

After merge, inspect the canonical certification workflow result and verify any generated 0.3.0 release-v4 metadata still describes the identical module-aware artifact digest and no `.tf` file changed.

## 11. Independent adversarial review gate

A logically separate final review must challenge:

- whether a future version can abuse baseline mode;
- whether an incorrect predecessor can pass by version name alone;
- subset-vs-exact expected-change mistakes;
- feature additions/removals escaping comparison;
- provenance changes escaping a main-only comparator;
- node renumbering escaping due metadata normalization;
- `otext` section/format changes being ignored as metadata;
- overly broad ignored metadata fields;
- v3 compatibility accepting malformed/unknown historical policies;
- a v4 manifest passing without cryptographically bound delta declaration/evidence;
- accidental mutation of published 0.2.0 or current 0.3.0 `.tf` data;
- coupling predecessor comparison to today's in-tree storage despite planned release-asset distribution.

Any blocking finding returns to RED → implementation → full test → fresh independent review.

## 12. Artifact/version impact

No TF feature/node/edge/schema change; no `TF_VERSION` bump.

Policy identity changes from release-v3 to release-v4. Existing v3 evidence becomes historical-but-verifiable. Current 0.3.0 may be re-certified under v4 as the explicit adoption baseline by the canonical workflow, without changing TF feature bodies.
