# Research: cancel superseded ordinary PR CI runs

Issue: #147  
Observed: 2026-10-03  
Baseline: `main@12f2c8285cbf2b00c78d08dcb77363976d5ec506`

## Observed failure mode

Ordinary `.github/workflows/ci.yml` has no workflow- or job-level `concurrency`
declaration.

During #144, rapid research/TDD corrections created these ordinary PR runs for
successive heads:

| head | run |
|---|---:|
| `a024c5a` | 37109461164 |
| `883101c` | 37109650115 |
| `1e0c873` | 37109662590 |
| `bf9d902` | 37109739986 |
| `29ddfb4` | 37109886504 |
| `bdc749a` | 37109903578 |
| `0542d52` | 37110111582 |
| `0409cfe` | 37110330139 |

The old runs were not semantically required. For example, bdc749a passed unit tests,
corpus identity, repair application, sign round-trip, morphology, app configuration,
feature docs, tag inventory, provenance split, alignment and external sign-reference
checks, then failed only because the committed current-build manifest had not yet been
refreshed for the new code identity. Newer heads already superseded it while it kept
using runner capacity.

This is the ordinary-CI analogue of the historical certification overlap addressed by
#68. #68 does not change `.github/workflows/ci.yml`.

## GitHub Actions semantics

Current GitHub documentation states:

- workflow- or job-level `concurrency` groups permit at most one running member of a
  group; by default only one pending member is retained;
- `cancel-in-progress: true` also cancels a currently running member when a newer
  member enters the same group;
- concurrency-group names are repository-wide, so a workflow identifier should be part
  of the key when unrelated workflows must not cancel one another;
- for an open `pull_request` event, `github.ref` is the merge ref
  `refs/pull/<pull_request_number>/merge`;
- for a `push`, `github.ref` is the pushed branch/tag ref.

Sources:

- https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency
- https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#github-context
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request

## Required grouping behavior

The ordinary workflow has two trigger families:

```yaml
on:
  push:
    branches: [main]
  pull_request:
```

The desired behavior is asymmetric:

- successive heads of **one PR** should share a concurrency group and cancel older
  ordinary CI;
- different PR numbers must not share a group even if source branch names collide;
- a `main` push must never be cancelled by PR activity;
- this ticket does not need to serialize or cancel separate push-only/write-enabled
  workflows.

A raw `github.head_ref` group is rejected because it is the source branch name, not
the PR identity. Two PR contexts can therefore collide by branch naming.

A raw `github.ref` group is safe for PR identity because PR refs contain the PR
number. It would also group successive `main` pushes. That is not necessary for this
ticket, and using a unique run ID for non-PR events keeps the change maximally narrow.

Selected group expression:

```yaml
concurrency:
  group: >-
    ${{ github.workflow }}-
    ${{ github.event_name == 'pull_request' && github.ref || github.run_id }}
  cancel-in-progress: true
```

Equivalent single-line formatting is acceptable.

For PR runs this evaluates to the workflow name plus `refs/pull/N/merge`, stable for
all successive heads of PR N. For `main` push runs it includes `github.run_id`, so
every push remains independent and cannot be cancelled by another push or by a PR.

`github.workflow` keeps the group namespace separate from any other workflow that may
also adopt concurrency later.

## Scope and safety

Ordinary CI is read-only with respect to the repository. It checks out code, installs
dependencies and runs validators; it has no `contents: write` permission and no
publication step. Cancelling a stale run therefore cannot strand a partial repository
write.

The current one-shot workflows used by #144 and #142 are separate workflow files and
do not inherit concurrency from `ci.yml`. Their write/push semantics remain
unchanged.

No corpus bytes, TF artifacts, validation semantics or release policy should change.

## Conclusion

Add PR-scoped cancellation to ordinary `ci.yml` only, using the PR merge ref as the
stable PR identity and a unique fallback for non-PR runs. This is a CI ergonomics and
runner-efficiency change; it must not alter which gates the newest head runs.


## Hosted behavioral verification

The implementation head `747e0802568e9d7873dbf1e2b9e008552c49556a` started ordinary
PR CI run **37143667386**. A documentation-only successor commit is intentionally
pushed while that run is queued so GitHub, rather than a static test, demonstrates
whether the selected group cancels a superseded run of this same PR.


First probe result: run **37143667386** completed with conclusion `cancelled` when
successor run **37143693272** for head `67ef7ec935989101b463112337c4a7fbe7c81979`
entered the same PR group. A second documentation-only successor now targets
37143693272 to verify the behavior repeats.
