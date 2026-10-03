# Plan: cancel superseded ordinary PR CI

Issue: #147

## Gate 1 — workflow contract RED

Add a focused unit test that parses `.github/workflows/ci.yml` and requires a
workflow-level `concurrency` mapping with:

- a group expression containing `github.workflow`;
- PR identity derived from `github.ref` under a `pull_request` condition;
- a unique non-PR fallback derived from `github.run_id`;
- `cancel-in-progress: true`.

The test should also model representative context values and assert the intended
identity relation:

- two successive heads of PR 144 -> same group;
- PR 144 vs PR 146 -> different groups;
- same source-branch spelling is irrelevant because PR refs differ;
- PR 144 vs a main push -> different groups;
- two main push run IDs -> different groups.

The first hosted run must be RED against the current workflow, before editing
`ci.yml`.

## Gate 2 — minimal workflow implementation

Add only the selected top-level `concurrency` block to `.github/workflows/ci.yml`.
Do not change triggers, permissions, jobs, gate commands or runner versions.

Prefer a group expression equivalent to:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.event_name == 'pull_request' && github.ref || github.run_id }}
  cancel-in-progress: true
```

## Gate 3 — static GREEN

Run the focused workflow-contract test and the ordinary unit suite. The test must fail
if a later edit:

- removes cancellation;
- falls back to `github.head_ref`/branch-name identity;
- makes non-PR events share a fixed group;
- drops workflow namespacing.

## Gate 4 — hosted behavioral evidence

Open the PR only after the RED history exists. Then make at least two harmless
successive commits to the PR branch while the earlier ordinary CI run is queued or
running.

Record evidence that:

- the older ordinary PR run is cancelled;
- the newest head completes the full ordinary CI;
- another PR's run is not cancelled;
- a `main` push uses a distinct group (do not create a synthetic main push solely for
  this test if normal project activity already supplies evidence).

Do not use a write-enabled one-shot workflow as the cancellation target.

## Gate 5 — logically independent adversarial review

Review the exact final SHA and challenge:

- branch/fork name collision assumptions;
- merge-ref stability;
- PR close/reopen/synchronize events;
- main push isolation;
- repository-wide concurrency-group collision with other workflows;
- whether ordinary CI contains any hidden write/publication side effect;
- whether cancellation can produce a false green on the newest head.

Merge only after exact-head ordinary CI is green.
