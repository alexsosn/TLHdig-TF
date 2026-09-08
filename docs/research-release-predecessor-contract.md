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

The now-closed PR #11 branch contains `programs/check_docid_raw_release.py`; it is not present on current `main`.

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

Comparing complete `.tf` bytes is too strict for a version transition because Text-Fabric headers contain release-local and documentary metadata such as `@version`, `@dateWritten` and descriptions.

The initial research assumption that ordinary node/edge feature bodies alone were sufficient did not survive adversarial review. Text-Fabric uses ordinary feature headers to interpret the same serialized body differently:

- the first header line distinguishes `@node` from `@edge`;
- `@valueType=str|int` controls value interpretation;
- `@edgeValues` distinguishes valued from unvalued edge features.

Therefore an ordinary feature's predecessor identity must compare a normalized **semantic header** (`@node`/`@edge`, effective `@valueType`, effective `@edgeValues`) together with the exact serialized body. This catches node renumbering/traversal changes, edge changes, feature-value changes and changes in loader-visible feature semantics without treating documentary metadata edits as graph changes.

Added or removed feature files count as changes and the side that exists must still parse as a structurally valid Text-Fabric feature. Main and optional provenance modules are compared independently and every change is module-qualified.

A second adversarial pass showed that configuration handling cannot be tied to the literal basename `otext.tf`. Text-Fabric supports supplemental configuration features such as `otext@...`; their serialized first header is still `@config`. A generic comparator must therefore dispatch **every** `.tf` feature by its first header (`@node`, `@edge`, `@config`) rather than by basename. All `@config` features compare semantic configuration while ignoring only release-local writer fields (`@version`, `@dateWritten`). Otherwise a valid supplemental config feature is either rejected as malformed or escapes the intended config semantics.

Feature descriptions, attribution, licence, language and similar ordinary-feature metadata are documentary/provenance metadata rather than graph/value semantics. The predecessor gate should not make a harmless wording/date/version edit look like a data rewrite. Current-artifact digest and the relevant documentation/configuration gates remain responsible for integrity of those bytes.

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

For the current repository layout the default materialization path can remain `tf/<predecessorVersion>` plus the matching `tf-provenance/<predecessorVersion>` module. A predecessor version is an identifier, not a filesystem path, so the checker must reject path separators and traversal components before resolving it.

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

Adversarial review showed that binding the escape hatch to the version string alone is insufficient. Certification deliberately permits release-output paths to change during a build, so a later self-consistent but different artifact could otherwise be written under `tf/0.3.0` and re-certified as the adoption baseline. Release-v4 must therefore freeze **both** the adoption version and its already-certified module-aware digest in the immutable policy contract:

```text
TF version: 0.3.0
Digest: sha256:93790f9e283c3c3d29d8a751b1eecbb7fd908745470aa36b9cec0525b90182d1
```

The mutable `release-delta.json` declaration must repeat that digest, and both the predecessor gate and independent stamp verifier must require the declaration, gate evidence and actual artifact bytes to agree with the frozen policy value. Future policies may choose another migration boundary; historical release-v4 verification must continue to use release-v4's frozen values.

## Workflow interaction

`.github/workflows/certify-dataset.yml` re-runs `release_check.py` when certification code/policy changes and commits certification evidence. A policy-v4 implementation will therefore re-certify current 0.3.0 after merge unless the workflow is changed.

That is acceptable only if:

- no `.tf` feature body or provenance feature body changes;
- 0.3.0 is explicitly the policy-v4 adoption baseline and its module-aware digest remains exactly the frozen digest above;
- v3 evidence remains verifiable in history;
- the workflow records the new stronger certification rather than silently changing corpus data.

The implementation PR itself should not hand-edit generated certification evidence. The canonical workflow remains the writer after the reviewed code lands.

## Required failure semantics

A future non-baseline release must not receive `BUILD-COMPLETE` when any of these is true:

- delta specification is missing/malformed or names a different candidate version;
- predecessor artifact is absent;
- predecessor bytes do not match the pinned predecessor digest;
- predecessor version is path-shaped rather than one version component;
- actual changed feature set differs from the exact declared set;
- a main/provenance feature is added or removed without declaration;
- an existing added/removed feature is malformed;
- ordinary feature kind, value type or edge-value semantics change without declaration;
- any `@config` semantic configuration changes without declaration, including supplemental config features;
- a `.tf` file has an unsupported/malformed first feature-kind header;
- predecessor comparison errors or cannot read a feature.

The one-time adoption baseline must likewise fail if its declaration, evidence or actual 0.3.0 bytes do not match the immutable release-v4 baseline digest. All such conditions are hard release failures, not availability skips.

## Scope conclusion

Issue #38 can be fixed without changing corpus conversion, node/edge values or TF feature schema. The required changes are release-certification infrastructure, a versioned delta input, tests and policy-verifier compatibility. No TF artifact version bump is justified; post-merge re-certification of 0.3.0 is certification-metadata evolution only and must leave every `.tf` byte unchanged.
