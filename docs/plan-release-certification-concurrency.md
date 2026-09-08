# Plan: serialize canonical release certification per ref

Issue: #68
Research: `docs/research-release-certification-concurrency.md`

## Goal

Prevent obsolete copies of `Certify shipped dataset` from consuming runner time after a newer run for the same Git ref exists, while preserving the existing non-fast-forward stale-writer protection.

## Design

Add one top-level concurrency block to `.github/workflows/certify-dataset.yml`:

```yaml
concurrency:
  group: certify-dataset-${{ github.ref }}
  cancel-in-progress: true
```

Contract:

- the same branch/ref maps every commit to one stable group;
- different refs do not share a group;
- `github.sha` is forbidden in the group;
- cancellation is enabled;
- evidence publication remains an ordinary non-force push;
- no release gate, policy, input, artifact, report schema, or TF byte changes.

## TDD sequence

### RED

Before changing the workflow, add `programs/tests/test_certification_concurrency.py` that reads the workflow as text and requires:

1. a top-level `concurrency:` section;
2. a group expression containing `github.ref` (or an equivalently stable ref identity);
3. `cancel-in-progress: true`;
4. the group does not contain `github.sha`;
5. the evidence command still uses ordinary `git push origin HEAD:${GITHUB_REF_NAME}`;
6. no `--force`, `--force-with-lease`, `git pull`, or `git rebase` appears in the evidence-publish block.

The hosted RED must fail only because the concurrency contract is absent. Existing tests should remain green.

### GREEN

Add the minimal top-level concurrency block. Do not amend the publish script or release-gate configuration to satisfy the test.

## Test gate

After GREEN:

- targeted concurrency tests pass;
- full unit/adversarial suite passes;
- ordinary PR CI passes;
- changing the canonical workflow triggers its own certification run under the new group;
- canonical certification completes successfully or, if superseded by a newer same-ref push, the newest run is the one allowed to complete;
- after any evidence commit, exact-head PR CI must be fully green.

Because this ticket changes only workflow scheduling, generated certification evidence may update its recorded code commit but the TF/provenance artifact digest must remain unchanged from certified 0.4.0.

## Independent adversarial review

On the exact final head, challenge:

- accidental use of `github.sha`, making concurrency ineffective;
- a global group that lets one branch cancel another;
- placement of `concurrency` under the wrong YAML node;
- cancellation disabled by quoting/type mistakes;
- a changed/forceful evidence-push strategy;
- unrelated release-policy/gate/artifact changes;
- a final branch head without valid certification evidence or exact-head CI.

Any blocker requires a new RED where appropriate, a fix, complete relevant tests, and a fresh independent review.

## Completion

Merge only the exact reviewed/green head. The PR should fix #68. #69 remains independently open for certification dependency freshness.