# Research: fail-closed release-certification freshness

Issue: #69  
Baseline: `main` at `d72dbd7b874ef6334c3332de1a7f0d7b8605e3f9` (certified TF 0.4.0 evidence head).  
Related scheduling fix: #68 / PR #73 is intentionally separate.

## Question

Can the repository continue accepting an old successful full-release certification after certification-relevant code, configuration, dependencies, or declared inputs have changed? If so, what identity should a future policy bind so stale evidence fails locally rather than relying on GitHub Actions to notice every relevant path?

## Current release-v5 evidence

`programs/release_check.py` runs these required gates:

1. corpus identity;
2. repair manifest;
3. sign round-trip;
4. morphology;
5. structure;
6. sign language;
7. manuscript joins;
8. Contract A graph conservation;
9. marker conservation;
10. tag inventory;
11. provenance split;
12. cuneiform alignment;
13. external sign-reference fetch;
14. external sign-reference validation;
15. app consistency;
16. census;
17. predecessor delta;
18. tracked-tree stability.

The certification manifest hashes four declared release inputs: `programs/corpus.sha256`, `programs/patches.yaml`, `programs/signrefs.lock.json`, and `programs/release-delta.json`. It also records the resolved Git commit, known-defect counters, artifact digest, gate outcomes, and input stability before/after the gate suite.

During a certification run, `tracked_changes()` rejects tracked source/code/config modifications outside mutable release outputs, and `resolve_commit()` rejects a Git HEAD / environment-SHA disagreement. This proves one run used one clean checkout. It does not make that certification automatically stale after a later checkout changes.

## Verifier boundary

`programs/check_stamp.py --require-full` delegates to `tlhdig.stamp.check()`.

The full verifier currently proves that:

- TF/provenance bytes match the module-aware artifact digest;
- `BUILD-COMPLETE` hashes the exact certification manifest;
- stamp and manifest agree on source version, TF version, mode, and a syntactically valid 40-character `codeCommit`;
- the recorded policy exists and its historical required gate/input contract is satisfied;
- every required gate recorded `passed` with return code 0;
- predecessor-delta evidence is valid where the recorded policy requires it;
- required input identities are present and are syntactically valid SHA-256 values;
- known-defect baselines satisfy the recorded policy.

It does **not** prove that the current checkout still has the source/code/config/dependency tree represented by `codeCommit`, nor does it recompute the current four release inputs and compare them with the manifest. A later checkout can therefore retain an internally valid old manifest after certification-relevant tracked files have changed.

This is a freshness defect, not evidence that the explicit 0.4.0 exact-head certification was invalid.

## Workflow trigger audit

The canonical `Certify shipped dataset` workflow currently refreshes evidence for a manually curated `push.paths` set. It covers TF/provenance feature bytes, `release_check.py`, `release-delta.json`, `check_*.py`, all tests, four selected `tlhdig` modules, itself, and temporary release workflows.

The dependency surface is broader. Concrete currently relevant classes include:

- gate entrypoints that are not named `check_*.py`, including `verify_patches.py`, `fetch_signrefs.py`, and `census.py`;
- transitive local modules imported by the gate entrypoints: `appcheck`, `paths`, `corpusid`, `repair`, `source`, `signs`, `morph`, `structure`, `brackets`, manuscript helpers, sign-reference loaders, cuneiform helpers, feature metadata/documentation code, stamp code, and others;
- declared inputs `patches.yaml`, `corpus.sha256`, and `signrefs.lock.json`;
- fidelity baselines `known_lossy.txt`, `contract_a_known.txt`, and the code constant supplying `KNOWN_WORD_DEFICIT`;
- `app/config.yaml` and app consistency dependencies;
- `requirements.txt`, which controls Text-Fabric, lxml, pytest, and PyYAML versions used by canonical certification;
- checker-specific tracked lookup/configuration tables where applicable.

`programs/research_release_certification_dependencies.py` reproduces this audit by extracting the current gate entrypoints, recursively following local Python imports, adding explicit non-code release inputs, reading the workflow path filter, and reporting covered/uncovered paths as deterministic JSON. Its import closure is deliberately conservative research evidence rather than a production dependency resolver.

## Concrete stale-evidence adversarial cases

On release-v5, ordinary full-stamp verification can remain satisfied after changing a certification dependency while leaving TF bytes and the old certification files untouched. RED tests should later demonstrate at least these classes independently:

1. change a transitive validator module such as `tlhdig/appcheck.py`;
2. change `programs/patches.yaml` or another declared release input;
3. change `app/config.yaml` or another gate configuration dependency;
4. change `requirements.txt`;
5. change another validator/data dependency omitted from the current workflow filter.

The future verifier should reject stale evidence for the relevant protected classes even if no GitHub workflow happened to run.

Generated certification/report changes must not create a self-invalidating cycle. Mutable outputs include `tf/**`, `tf-provenance/**`, `reports/**`, `BUILD-COMPLETE`, and `RELEASE-CERTIFICATION.json`; the artifact and certification hashes already bind the appropriate generated bytes separately.

## Historical-policy constraint

The repository deliberately verifies a manifest against the **policy it recorded**, not against whatever `release_policy.POLICY` happens to be current today. Existing tests exercise frozen release-v3/v4 behavior. Release-v5 is now published by TF 0.4.0.

Therefore adding a new protected-source identity must be a new policy/schema contract (candidate: release-v6 / schema 2), not a reinterpretation that retroactively makes v3/v4/v5 artifacts unverifiable.

## Options

### 1. Broaden `push.paths` only

Advantages: small change, easy to understand.

Failure: correctness still depends on a manually maintained list, and a future omitted dependency silently recreates the bug. It also increases expensive certification frequency. During current development, an intentionally failing RED change under `programs/tests/**` started the long canonical certifier before its PR CI obtained a runner. Widening triggers indiscriminately would worsen runner contention.

Conclusion: useful only as defense in depth.

### 2. Hash an explicit hand-maintained dependency list

Advantages: verifier can fail locally and the identity can exclude mutable outputs.

Failure: another manually maintained dependency list can drift from actual imports/gate configuration. It improves enforcement but does not eliminate dependency-discovery risk.

Conclusion: viable only if the protected roots are broad and intentionally conservative.

### 3. Protected tracked-tree identity

Bind a deterministic digest of certification-relevant tracked roots to the certification manifest and independently recompute it during full-stamp verification. Exclude generated TF/provenance/report evidence to avoid circularity. Use broad stable roots rather than enumerating every imported file individually—for example the release/checker Python code, canonical app config/code, declared input/lock/manifests, dependency declarations, and canonical certification workflow.

Advantages:

- stale evidence fails at verification time even when Actions did not trigger;
- transitive local module changes are naturally covered by root inclusion;
- the contract is easier to audit than an import-by-import allowlist;
- generated evidence can remain outside the protected identity;
- workflow paths become performance/freshness hints rather than the security boundary.

Cost: broad roots may invalidate evidence for changes that do not semantically alter a gate. That is preferable to silently blessing stale evidence, but the selected roots should avoid research/docs/tests if they do not participate in release semantics.

## Runner-efficiency observation

#68 solves redundant copies of certification **on one ref**. It intentionally does not serialize different feature branches. The live repository currently demonstrates that behavior: unrelated branch certifiers can run independently, which is correct isolation but means an overly broad trigger policy can still consume scarce runners across many branches.

The #69 design should therefore separate two concerns:

- verifier correctness: cryptographically bind protected certification dependencies;
- Actions scheduling: trigger expensive recertification only where useful, with broader but deliberate path coverage as defense in depth.

## Research conclusion

Release-v5 evidence is internally strong for one immutable certification run but is not self-invalidating against later certification-relevant checkout changes. The workflow path filter is incomplete and cannot be the sole correctness mechanism even if expanded.

The planning phase should design a new frozen release-policy contract that records a deterministic protected-tree identity and makes `stamp.check(..., require_full=True)` recompute it for that policy. Mutable generated outputs must remain outside that identity, historical v3/v4/v5 verification must remain unchanged, and workflow trigger changes should be treated as runner-efficiency/defense-in-depth rather than the primary freshness guarantee.
