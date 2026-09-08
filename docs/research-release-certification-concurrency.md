# Research: canonical release-certification concurrency

Issue: #68
Baseline: `main` at `44ea6ccccc88762caf77a98c0b5f53a150759e2b` after the certified TF 0.4.0 / sign-language release.

## Question

Can repeated pushes to one release branch start obsolete copies of the expensive canonical certification workflow, and if so can they be cancelled without weakening the existing stale-writer protection?

## Observed failure mode

During TF 0.4.0 finalization, several commits landed on `research/sign-lang-19` while `Certify shipped dataset` runs were still active. GitHub consequently executed multiple copies of the same workflow for the same branch/ref.

The clearest captured run is Actions `34263510099`, job `102187047238`:

1. it checked out branch commit `1b254b251c0e030ca84822453e17299dc983f461`;
2. the full `release-v5` gate suite completed successfully;
3. it created a local certification-evidence commit `70f338db`;
4. the branch had advanced meanwhile;
5. the ordinary `git push origin HEAD:${GITHUB_REF_NAME}` was rejected as non-fast-forward (`fetch first`).

This demonstrates two separate properties:

- release semantics/artifact validity were not the cause of that failure: certification itself passed;
- stale evidence could not overwrite the newer branch head. The ordinary non-force push is a safety property that must remain unchanged.

Actions history for the same branch shows repeated `Certify shipped dataset` push runs close together during finalization. While those long runs occupied hosted runners, exact-head PR CI was delayed/queued.

## Current workflow contract

`.github/workflows/certify-dataset.yml` currently has:

- `workflow_dispatch` and path-filtered `push` triggers;
- `contents: write` only because it commits generated evidence;
- a single long `certify` job;
- no top-level `concurrency` declaration;
- no force push, pull, rebase, or branch reset before publishing evidence.

Therefore each triggering commit is independently schedulable even when a newer commit on the same ref makes the older certification result non-publishable.

## Desired scheduling invariant

For a given Git ref, only the newest invocation of this workflow is useful. A newer invocation should cancel an older in-progress invocation for the same ref before both consume the full release-gate budget.

Different refs must remain independent: certification on `main`, a release branch, or another feature branch must not cancel each other.

The concurrency key must therefore be stable across commits on the same ref. It must **not** contain `github.sha`, because including the commit SHA would give every push a unique group and preserve the race.

A suitable key is:

```yaml
concurrency:
  group: certify-dataset-${{ github.ref }}
  cancel-in-progress: true
```

`github.ref` also gives `workflow_dispatch` on the same branch the same serialization domain.

## Safety analysis

Cancellation is scheduling hygiene, not evidence publication logic. The existing stale-writer protection remains necessary because cancellation is cooperative and a job may already be in its final publish step when a new run starts.

Accordingly the implementation must retain the current ordinary push exactly in spirit:

```sh
git push origin HEAD:${GITHUB_REF_NAME}
```

No `--force`, `--force-with-lease`, `git pull`, rebase, reset, or retry-on-top-of-new-head may be introduced by #68.

## Scope boundary

#68 owns only same-ref workflow serialization. It does not decide which repository changes invalidate release evidence. That broader fail-closed dependency/freshness problem is tracked by #69.

The change must not alter:

- TF/provenance bytes;
- release policy or required gates;
- release inputs;
- certification manifest/stamp schema;
- evidence push semantics.

## Research conclusion

The runner waste is a same-workflow/same-ref concurrency defect, while the observed non-fast-forward rejection proves stale publication already fails safely. Add branch/ref-scoped Actions concurrency with cancellation, and regression-test both the grouping rule and preservation of non-force publication semantics.