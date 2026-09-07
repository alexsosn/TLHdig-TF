# Research: predecessor identity and release-delta certification

**Issue:** #38  
**Base:** `main` at `5c63f3dcf39a5bdc77ad69531ac1cf2deaef93f8`

## Question

Can the canonical release certifier currently distinguish a self-consistent Text-Fabric artifact from a self-consistent artifact whose graph/data changed outside the intended release scope?

## Current answer: no

`programs/release_check.py` currently runs the `release-v3` gate set:

1. corpus identity;
2. repair manifest;
3. sign round-trip;
4. morphology;
5. structure;
6. manuscript joins;
7. Contract A graph;
8. marker conservation;
9. tag inventory;
10. provenance split;
11. alignment;
12. external-reference acquisition;
13. external-reference comparison;
14. app validation;
15. census;
16. tracked code-tree stability.

Those gates establish that one artifact is internally consistent with the current source, converter invariants and declared baselines. None names a predecessor release or an intended set of artifact changes.

`tlhdig.certification.certify()` records:

- the current artifact's module-aware digest and feature count;
- source/TF versions;
- code commit;
- hashes of corpus/repair/sign-reference inputs;
- known-defect baselines;
- the ordered gate outcomes;
- before/after artifact and input stability.

It receives no predecessor identity and computes no predecessor delta. A runner that reports all gates passed can therefore certify any artifact that is self-consistent under those gates, including one whose node numbering or unrelated feature bodies differ from its predecessor.

This is the exact class reported by #38: a wrong-order artifact passed all required gates because the artifact was coherent on its own.

## Current shipped evidence also has no predecessor fact

`tf/0.3.0/RELEASE-CERTIFICATION.json` is a successful `release-v3` manifest with 139 feature files and module-aware digest

```text
sha256:93790f9e283c3c3d29d8a751b1eecbb7fd908745470aa36b9cec0525b90182d1
```

It records the 16 required gates and the three required release inputs, but no predecessor version/digest, intended-change set or observed-change set.

The repository currently contains `tf/0.1.0`, `tf/0.2.0` and `tf/0.3.0`. GitHub's Releases API currently exposes the published `tlhdig-0.3_tf-0.2.0` release; the current in-tree `0.3.0` artifact is certified but is not yet a GitHub release. This matters for migration: adding stronger certification evidence to 0.3.0 does not require rewriting the published 0.2.0 release.

## Evidence from the one-off 0.2.0 -> 0.2.1 checker

PR #11's branch contains `programs/check_docid_raw_release.py`; it is not present on current `main`.

That checker demonstrates two useful properties:

1. it compares **every serialized TF feature body** between predecessor and candidate, across both the main and provenance modules;
2. it permits only `docid_raw.tf` to differ, then performs issue-specific semantic/source checks for that feature.

This would have caught the wrong-document-order artifact because node-order changes perturb many feature bodies.

It is deliberately release-specific, however:

- predecessor/current versions are hard-coded;
- the permitted feature is hard-coded;
- it assumes both versions are present in the checkout;
- it contains source-semantic assertions specific to `docid_raw`;
- its result is not a required `release-v3` gate or cryptographically recorded predecessor fact.

The reusable part is the *artifact delta primitive*, not the issue-specific script.

## What a generic delta comparison must compare

Comparing complete `.tf` bytes is too strict for a version transition because Text-Fabric headers contain expected release-local metadata such as `@version` and `@dateWritten`.

Comparing only bodies is appropriate for ordinary node/edge features and catches:

- node renumbering / traversal changes (`otype`, `oslots`, node-feature bodies);
- edge changes;
- changed feature values;
- added or removed feature files;
- changes in the optional provenance module.

`otext.tf` is special: it is configuration metadata and normally has no data body. A generic comparator must therefore compare its semantic configuration while ignoring only release-local volatile fields (`@version`, `@dateWritten`). Otherwise section types/features or text-format changes could bypass the delta contract.

Feature descriptions and other non-`otext` metadata are documentation/schema metadata rather than graph data. The predecessor gate should not make a harmless description/date/version edit look like a graph rewrite. Existing artifact digest and documentation/config gates remain responsible for current-artifact integrity.

The natural changed-feature identity is module-qualified, for example:

```text
main:docid_raw.tf
main:otype.tf
provenance:srcxml.tf
```

An exact observed set is stronger than an allowlist subset: if a release declares a feature as intentionally changed but it did not change, that discrepancy should be visible rather than silently accepted.

## Predecessor identity must be pinned separately from location

A path such as `tf/0.2.0` is not sufficient identity. The comparator must verify a pinned module-aware predecessor digest before using the bytes as the baseline.

The predecessor's *acquisition mechanism* should not be owned by the comparator. Distribution work (#39/#47) plans to retire older in-tree versions and make released artifacts independently retrievable. The release checker should therefore require a materialized predecessor artifact and verify its declared digest; a future workflow can obtain those bytes from an in-tree directory, GitHub release asset or another deterministic source without changing comparison semantics.

For the current repository layout the default materialization path can remain `tf/<predecessorVersion>` plus the matching `tf-provenance/<predecessorVersion>` module.

## The intended delta must itself be a release input

The set of intended changes cannot safely be inferred from the candidate artifact: doing so would certify the defect it is supposed to catch.

It needs a small committed release-delta specification prepared before certification, containing at least:

- schema/version;
- candidate `tfVersion`;
- predecessor `tfVersion`;
- pinned predecessor module-aware digest;
- exact expected changed feature identities.

That specification should be hashed into `RELEASE-CERTIFICATION.json` as a required release input, just like the corpus/repair/sign-reference locks. Issue-specific semantic gates remain separate: a delta declaration says *where change is permitted/expected*, not *whether that change is philologically correct*.

## Adoption / policy-version problem

`release_policy.POLICY` is currently `release-v3`. `stamp._check_full()` requires the manifest's `policy` to equal the single current `release_policy.POLICY`, and then compares `requiredGates`/`inputs` against the current constants.

Therefore simply changing the canonical gate/input set to add predecessor certification would make the existing fully certified 0.3.0 `release-v3` stamp fail ordinary verification. Rewriting old full-certification evidence every time the policy evolves would contradict immutable-release/audit semantics.

A safe migration requires the verifier to recognize supported historical policy specifications. New certifications can use `release-v4`; existing `release-v3` manifests must continue to verify according to the exact v3 gate/input/baseline contract they actually recorded.

The artifact digest algorithm can remain `tlhdig-tf-modules-v2`; the new contract concerns predecessor/delta evidence, not the identity algorithm for one artifact.

## Adoption baseline

A predecessor contract cannot retroactively reconstruct an independently declared intended-delta manifest for every historical transition. The repository needs one explicit adoption boundary.

`tf/0.3.0` is the practical adoption baseline because:

- it is the current certified artifact;
- it already has full `release-v3` evidence;
- it has not yet been published as a GitHub release;
- future TF versions can be required to name 0.3.0 (or a later certified version) as predecessor;
- the already published 0.2.0 release does not need to be mutated.

A baseline escape hatch must be hard-bound to exactly this version in the versioned policy; it must not be a generic `baseline: true` option usable by future releases.

## Workflow interaction

`.github/workflows/certify-dataset.yml` re-runs `release_check.py` when certification code/policy changes and commits certification evidence. A policy-v4 implementation will therefore re-certify current 0.3.0 after merge unless the workflow is changed.

That is acceptable only if:

- no `.tf` feature body or provenance feature body changes;
- 0.3.0 is explicitly the policy-v4 adoption baseline;
- v3 evidence remains verifiable in history;
- the workflow records the new stronger certification rather than silently changing corpus data.

The implementation PR itself should not hand-edit generated certification evidence. The canonical workflow remains the writer after the reviewed code lands.

## Required failure semantics

A future non-baseline release must not receive `BUILD-COMPLETE` when any of these is true:

- delta specification is missing/malformed or names a different candidate version;
- predecessor artifact is absent;
- predecessor bytes do not match the pinned predecessor digest;
- actual changed feature set differs from the exact declared set;
- a main/provenance feature is added or removed without declaration;
- `otext` semantic config changes without declaration;
- predecessor comparison errors or cannot read a feature.

All such conditions are hard release failures, not availability skips.

## Scope conclusion

Issue #38 can be fixed without changing corpus conversion, node/edge values or TF feature schema. The required changes are release-certification infrastructure, a versioned delta input, tests and policy-verifier compatibility. No TF artifact version bump is justified; post-merge re-certification of 0.3.0 is certification-metadata evolution only and must leave every `.tf` body unchanged.
