# Plan: serialize canonical release certification per ref

Issue: #68. Research: `docs/research-certification-concurrency.md`.

This freezes the plan before RED/implementation.

## Contract

Add a top-level concurrency policy to `.github/workflows/certify-dataset.yml`:

```yaml
concurrency:
  group: certify-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

Equivalent group text is acceptable only if it includes both workflow identity and exact ref identity. Do not use a repository-global constant group.

## RED

Before changing the workflow, add a test that parses the workflow text and requires:

1. a top-level `concurrency` mapping;
2. `cancel-in-progress: true`;
3. the group contains `github.ref` (or an equally exact ref-scoped expression);
4. the group contains workflow identity so an unrelated workflow cannot collide accidentally.

Hosted RED must fail only because the current workflow has no concurrency contract.

## GREEN

Change only `.github/workflows/certify-dataset.yml` by adding the top-level concurrency block. Do not change:

- release gate commands;
- trigger paths;
- permissions;
- checkout behavior;
- certification/evidence generation;
- final ordinary `git push` semantics;
- corpus/app/TF/provenance bytes.

## Test gate

Run the full repository unit suite. Because changing the canonical workflow itself triggers certification, verify that the resulting workflow run starts on the exact GREEN head. If another push supersedes it, the old run should be cancelled rather than spending the full certification budget.

Ordinary PR CI must remain green apart from any pre-existing build-stamp expectation on branches that do not contain newly generated certification evidence.

## Independent review

Review the exact final patch separately from implementation and challenge:

- repository-global grouping that serializes unrelated branches;
- a group missing workflow identity;
- `cancel-in-progress: false` or omitted;
- accidental edits to release gates or push semantics;
- a concurrency change that masks rather than preserves non-fast-forward safety;
- coupling this ticket to #69 dependency-freshness work.

Any blocker repeats fix → tests → fresh review.

## Merge / propagation

Merge #68 independently into `main` once exact-head CI and independent review are green. Active release branches that predate the merge may apply the same reviewed workflow-only change before their next certification trigger; doing so changes the protected head and therefore requires certification on that resulting head.