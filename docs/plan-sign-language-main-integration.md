# Plan: reconcile sign-language preservation with current main

Research basis: `docs/research-sign-language-main-integration.md`. This integration plan supersedes only the old release-policy/version assumptions in `docs/plan-sign-language.md`; the sign-language semantic and conservation contracts remain unchanged.

## Contract changes

1. Preserve immutable historical `release-v3` and `release-v4` policy contracts.
2. Define current `release-v5` as the predecessor-aware v4 gate/input contract plus required `sign-language` immediately after `structure`.
3. Keep `releaseDelta` as a required input and predecessor evidence mandatory in v5.
4. Change `programs/release-delta.json` to TF 0.4.0, predecessor TF 0.3.0, the pinned certified predecessor digest, and exactly `main:lang.tf` in `expectedChanges`.
5. Merge current-main app documentation settings with TF 0.4.0 and expose `lang` on sign display.
6. Merge current-main release checker and add the independent sign-language gate without duplicating predecessor logic.
7. Generalize certification cleanup trigger to temporary `build-final-*` workflows.
8. During the final artifact build, regenerate `docs/features/` from TF 0.4.0 before tests; stage the generated reference with the immutable artifact.

## Integration RED

The explicit merge commit intentionally retains current-main v4/app/release files while restoring the already-tested sign-language converter/checker/tests. Existing issue-19 integration tests must fail because the current policy/app do not yet advertise the new sign-level feature. This is the hosted RED proving the merge conflict is real rather than silently resolved.

## GREEN tests

After reconciliation, run at minimum:

- full `programs/tests` suite, including main's predecessor-delta and feature-doc adversarial suites;
- release-policy identity assertions: v3 and v4 historical contracts plus current v5;
- predecessor-delta check against built TF 0.4.0, requiring exactly `main:lang.tf`;
- deterministic feature-reference generation/check;
- exact sign-language conservation over 3,365,129 source signs;
- structure and manuscript graph regression gates;
- app contract and census;
- byte immutability of historical TF/provenance releases;
- canonical `release_check.py --mode regression-valid` under v5 from the final cleaned protected-tree head.

## Final review

The final logically-independent adversarial review must attack both feature semantics and integration semantics: policy-name uniqueness, historical v3/v4 verification, v5 gate/input completeness, exact predecessor delta, generated `lang` documentation, app/version behavior, branch synchronization, and absence of unrelated serialized corpus changes. Any blocker restarts implementation/test/certification and requires a fresh review.
