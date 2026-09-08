# Plan: fail-closed certification freshness

Issue: #69
Research: `docs/research-release-certification-freshness.md`

## Decision

Introduce a **new** full-release contract, `release-v6` with certification manifest schema 2, that cryptographically binds a deterministic **protected Git-tree identity** and requires full-stamp verification to recompute that identity against the current checkout.

Do not reinterpret release-v3/v4/v5 or schema-1 manifests. Published releases remain verified under the exact contracts they recorded.

Workflow `push.paths` becomes defense-in-depth/scheduling only; stale-evidence correctness no longer depends on it.

## Why a protected Git-tree identity

A literal byte rehash of the source corpus on every ordinary stamp check would repeatedly read gigabytes. A hand-maintained import list can drift. Git already stores cryptographic identities for tracked source files and tree structure.

The selected algorithm therefore computes a SHA-256 digest over deterministic Git tree entries for broad protected path classes. It reads Git object/tree metadata rather than corpus payload bytes while still changing whenever a tracked protected file's Git identity/path changes.

The verifier must additionally reject protected working-tree/index changes, so an unstaged or staged local edit cannot hide behind the committed HEAD tree.

This contract intentionally requires a Git checkout for **current-checkout freshness** verification under release-v6. Artifact-only consumers may still verify artifact/checksum metadata separately; they cannot claim that an unrelated local source checkout is the exact certified code tree without that checkout.

## Protected profile v1

Define one immutable profile in code, e.g. `release-source-v1`, recorded by the release-v6 policy contract.

Protected tracked classes:

- `corpus/**` — authoritative distributed source tree;
- `app/**` — app configuration/code/static resources validated by the release app gate;
- `programs/**` — release/converter/checker code and declared input/configuration;
- `requirements.txt` — Python/Text-Fabric dependency identity;
- `.github/workflows/certify-dataset.yml` — canonical certification orchestration itself.

Narrow exclusions from `programs/**` are allowed **only** for clearly non-executed development evidence:

- `programs/tests/**`;
- `programs/research_*.py`;
- `programs/shard.txt` if retained solely as research sampling metadata.

Do not exclude files merely because they are currently believed irrelevant when they can be imported/read by production release code. False-positive recertification is preferable to stale acceptance.

Generated/mutable output roots are not in the protected profile:

- `tf/**` and `tf-provenance/**` — already bound by artifact digests;
- `reports/**` — generated audit output;
- certification/stamp files under `tf/<version>/` — generated evidence;
- docs/wiki — explanatory artifacts, not release execution inputs.

Because generated outputs are excluded, the bot evidence commit after successful certification has the same protected-tree identity as its pre-evidence parent.

## Digest algorithm

Add a small independent helper module (name to be frozen during implementation, e.g. `tlhdig/protected_tree.py`) with:

1. a policy/profile table containing immutable include/exclude rules;
2. a function that enumerates tracked entries from Git for the selected profile in deterministic path order;
3. a SHA-256 digest over a version tag plus each `(path, git object identity/mode)` entry and explicit boundaries;
4. a check for staged/unstaged/untracked protected-path changes that fails closed;
5. explicit errors when Git/profile data are unavailable rather than silently skipping freshness.

The digest is not a substitute for source/corpus gates. It only proves the current protected checkout identity matches the one whose full gate suite ran.

## Manifest schema 2 / release-v6

Extend the successful certification payload with a required object:

```json
"protectedTree": {
  "algorithm": "tlhdig-protected-git-tree-v1",
  "profile": "release-source-v1",
  "digest": "sha256:..."
}
```

Release-v6 policy contract adds the required protected profile/algorithm. Schema 2 is accepted only for policies that define this requirement.

Historical schema 1 remains accepted for recorded release-v3/v4/v5 exactly as today. Do not require `protectedTree` retroactively.

## Certification writer

For release-v6:

1. resolve/verify exact Git commit as today;
2. compute protected-tree identity **before** gates;
3. compute current release-input hashes/artifact digest as today;
4. run the unchanged required release-v5 gate set unless a separately justified gate change exists (this ticket does not invent one);
5. recompute protected-tree identity after gates;
6. fail if protected identity changed or protected working tree is dirty;
7. write schema-2 evidence only after all gates, artifact stability, input stability and protected-tree stability pass.

`codeCommit` remains useful audit provenance; the protected digest is the enforcement mechanism for later current-checkout freshness.

## Full verifier

For a schema-2/release-v6 manifest, `stamp.check(..., require_full=True)` must:

- perform all existing artifact/manifest/gate/input/fidelity checks;
- validate `protectedTree` shape, algorithm, profile and SHA-256 syntax against the recorded release-v6 policy;
- recompute the current protected-tree identity from the Git checkout containing the artifact;
- reject missing Git context;
- reject staged/unstaged/untracked protected changes;
- reject any current protected digest mismatch;
- continue to accept a bot evidence commit whose only differences from `codeCommit` are excluded mutable outputs.

For schema-1 v3/v4/v5, execute the frozen existing verifier path without current protected-tree requirements.

## Repository-root contract

`stamp.check()` currently receives the TF output directory. For a repository layout `ROOT/tf/<version>`, the verifier may derive `ROOT` deterministically, but the helper/API should make repository context explicit enough to test:

- normal repository checkout;
- malformed/moved artifact path;
- missing `.git`;
- caller-provided repository root if needed by clean unit fixtures.

Do not silently search arbitrary parent directories and bind the wrong repository.

## Workflow defense in depth

After the verifier contract is GREEN, broaden `.github/workflows/certify-dataset.yml` triggers to cover the protected classes at a maintainable root level rather than an incomplete hand list, while avoiding unnecessary expensive runs for docs/research-only changes.

At minimum trigger for:

- `corpus/**`;
- `app/**`;
- production `programs/**` classes / protected release input files;
- `requirements.txt`;
- TF/provenance artifact bytes;
- canonical certifier workflow.

Exact YAML path filtering can be tuned for runner efficiency because the local verifier is now the trust boundary. #68 concurrency remains unchanged and should cancel obsolete same-ref runs.

## TDD RED sequence

Commit RED tests before production changes. Use synthetic Git repositories/fixtures where possible so tests are deterministic and do not mutate published TF artifacts.

### A. Stale protected code

Start from a valid synthetic release-v6 certification, then change a tracked transitive release module (e.g. appcheck/checker helper) without updating evidence. Current full verification must currently accept the old evidence; RED requires rejection.

### B. Declared release input

Change `programs/patches.yaml` (and separately exercise another input class such as signrefs lock) while preserving old evidence. RED requires stale rejection.

### C. App configuration

Change `app/config.yaml` only. RED requires stale rejection even with unchanged TF bytes.

### D. Source corpus

Change one tracked source file under `corpus/**` without changing `corpus.sha256`. RED requires freshness rejection immediately; a future certification run would additionally fail the corpus gate.

### E. Dependency declaration

Change `requirements.txt`. RED requires stale rejection.

### F. Dirty working tree

With HEAD unchanged, stage or modify a protected file. Full verification must fail closed.

### G. Mutable generated outputs

Change `reports/**` or certification output metadata in the synthetic repo as appropriate. Protected-tree identity itself must remain unchanged; existing certification/artifact hash checks still govern evidence correctness.

### H. Bot evidence commit

Create a child commit differing only in excluded generated certification/report outputs. Protected-tree verification must still match the pre-evidence certified identity.

### I. Historical compatibility

Frozen v3/v4/v5 schema-1 fixtures must continue to verify exactly as before and must not require Git/protectedTree.

### J. Malformed/missing profile

Release-v6 evidence with missing/unknown profile, wrong algorithm, malformed digest or no Git checkout must fail closed.

Each hosted RED should fail only because the new protected-tree contract is not implemented; existing historical/artifact tests remain green.

## Implementation order

1. add policy/profile constants and pure protected-tree helper;
2. add schema-2 writer support gated only by release-v6;
3. add verifier branch for release-v6 protected identity;
4. switch current policy to release-v6 only after writer+verifier tests are green;
5. update workflow path coverage as defense in depth;
6. run canonical certification on the exact final protected head;
7. allow evidence bot commit; verify protected identity still passes;
8. run exact-head ordinary CI.

Do not rewrite historical artifact bytes simply to upgrade metadata.

## Full test gate

- targeted protected-tree adversarial tests;
- complete unit/adversarial suite;
- historical policy/stamp compatibility suite;
- full ordinary corpus/app/release CI;
- canonical release-v6 certification on a quiet exact head;
- post-evidence exact-head verification;
- explicit test that #68 concurrency still cancels obsolete same-ref certification runs without altering protected identity semantics.

## Independent adversarial review

A logically separate reviewer must challenge:

- broad roots that still omit actual gate dependencies;
- exclusions that accidentally hide executable inputs;
- hashing only HEAD while ignoring dirty index/worktree state;
- circular inclusion of generated evidence;
- bot evidence commits falsely invalidating certification;
- Git-path derivation binding the wrong repository;
- historical v3/v4/v5 behavior changed by schema-2 code;
- external/no-Git verification silently claiming freshness;
- workflow path filters being treated again as the primary trust boundary;
- release-v6 policy switched before writer/verifier are mutually GREEN.

Any blocker requires a new RED where appropriate, fix, full tests and a fresh exact-head review.

## Acceptance

- A certification-relevant tracked source/code/config/dependency change makes old release-v6 full evidence fail locally even if no workflow ran.
- Source corpus changes are detected without re-reading all corpus payload bytes during ordinary verification.
- Mutable generated outputs do not create a self-invalidating cycle.
- Evidence-only bot commits remain verifiable.
- Historical v3/v4/v5 manifests retain frozen behavior.
- Expensive workflow triggers are defense-in-depth, not the correctness boundary.
- Final exact head passes full release-v6 certification, ordinary CI and logically independent adversarial review.