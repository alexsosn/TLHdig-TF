# Research: GitHub Actions workflow architecture

Issue: #104

Status: research complete; no workflow topology changes in this commit.

## Question

How can TLHdig-TF stop creating a new GitHub Actions workflow identity for each research, patching, and release-materialization step without weakening the exact-head, immutable-artifact, protected-tree, least-privilege, and independent-certification guarantees accumulated by the release pipeline?

## Current repository state

At the researched `main` head (`76c56678ceb176c6e23335863772830e0e0173d0`) only four workflow files are retained:

1. `.github/workflows/ci.yml`
2. `.github/workflows/dataset.yml`
3. `.github/workflows/certify-dataset.yml`
4. `.github/workflows/source-path-evolution.yml`

The Actions history nevertheless contains more than one thousand runs and many branch-local workflow identities. A current research branch (`research/mrp-markers-92`) already demonstrates the recurring pattern: it contains the four main workflows plus a ticket-specific `research-mrp-markers.yml`. The certification-freshness work similarly needed a temporary `apply-protected-stability-green-69.yml` only to apply a small exact-string patch and run tests.

This is not just cosmetic UI clutter. Each new YAML identity can:

- create another workflow run and consume scarce runner concurrency;
- accidentally trigger canonical certification when protected workflow paths change;
- require workflow-file write permissions that ordinary `GITHUB_TOKEN` publishing paths intentionally do not have;
- make stale-run and branch-head races harder to reason about;
- embed procedural patch/build logic in YAML where it is difficult to unit-test;
- leave branch-local workflows queued after their useful evidence has already been captured.

The current certification-freshness cycle provided a concrete example: a clean RED CI run and a stale full certification occupied runners while a temporary GREEN patcher remained queued. This is an orchestration cost, not a corpus-science requirement.

## What the existing long-lived workflows actually do

### `ci.yml`

Purpose: ordinary pull-request / main regression coverage. It is read-only and runs the unit/integration suite plus corpus identity, repair, sign, morphology, app, documentation, provenance, alignment, and ordinary external-reference checks.

Conclusion: **canonical and long-lived**. It is the correct default validation surface for source changes.

### `dataset.yml`

Purpose: on-demand/monthly reproducible full corpus build followed by full release certification, uploading reports as an Actions artifact. It does not publish a new immutable repository release.

Conclusion: **canonical and long-lived**, although the substantial build/release procedure should continue to live in versioned Python rather than grow in YAML.

### `certify-dataset.yml`

Purpose: independently verify the committed artifact and publish generated certification evidence. It intentionally has `contents: write`, branch/ref validation, exact protected-tree freshness checks in repository code, and per-ref concurrency with stale-run cancellation.

Conclusion: **canonical, privileged, and deliberately separate**. It must not be folded into a generic research/maintenance runner. Certification is an independent verification boundary, not a convenience subroutine of materialization.

### `source-path-evolution.yml`

Purpose: reproduce one historical research report by downloading two pinned upstream archives, executing three analysis scripts, and diffing the checked-in report.

Conclusion: useful evidence, but **not a canonical workflow class**. It is exactly the kind of read-only research workload that can use a stable generic research entry point or be represented by ordinary tests plus an explicit reproducibility command.

## Workflow classes seen in development history

The recurring branch-local identities fall into four functional classes:

1. **Research runners** — execute one or more `programs/research_*.py` / analysis utilities, sometimes download pinned public data, and upload or compare evidence. They need no write token.
2. **GREEN/apply patchers** — use an ephemeral workflow to modify branch files, run tests, commit, and push. They need `contents: write` and are the riskiest genericization target.
3. **Release materializers** — build a new immutable `tf/<version>` + provenance module, run release gates, and publish artifact/report bytes. They need strong exact-head and immutability guards plus narrowly scoped writes.
4. **Certification** — independently verify already-committed artifact bytes and publish certification evidence. This must remain a separate privileged workflow.

These classes should not share one all-powerful generic runner.

## GitHub Actions constraints relevant to the design

GitHub documents that reusable workflows may receive the caller's token permissions but **cannot elevate them**. This is useful for a least-privilege architecture: a read-only caller cannot become write-capable merely by invoking shared setup/test logic.

`workflow_dispatch` supports typed/defaulted inputs on a stable workflow file on the default branch. This makes a stable entry point practical without creating a new workflow identity per ticket.

Concurrency groups are repository-wide names. Per-ref serialization is therefore appropriate for publication flows; obsolete validations may use `cancel-in-progress: true`, while a release publication path must decide explicitly whether cancellation or FIFO semantics are safe. Reusing the same concurrency group carelessly across caller and reusable workflow can cancel the caller itself.

References:

- GitHub Docs, *Reusing workflow configurations*: reusable workflows and permission non-elevation.
- GitHub Docs, *Triggering a workflow*: `workflow_dispatch` inputs/default-branch behavior.
- GitHub Docs, *Concurrency*: repository-wide concurrency groups and cancellation/queue semantics.

## Safety properties that must survive consolidation

The architecture must preserve all of these even if the YAML count falls:

- exact target branch/ref validation before publication;
- explicit expected-head / stale-head rejection for mutating jobs;
- protected-tree identity and post-gate stability;
- immutable target-version absence before materialization;
- predecessor/release-delta checks where the release contract requires them;
- historical artifact immutability;
- no publication when the branch advances during long gates;
- independent certification after artifact publication;
- narrow staging: never blanket-add ignored/generated trees unintentionally;
- least privilege: research jobs remain `contents: read`; publication capability is not available to arbitrary branch scripts;
- no secrets exposed to arbitrary research code;
- ordinary PR CI remains independently runnable from materialization/certification.

## Architecture options

### A. One universal workflow

A single manual workflow accepts an arbitrary command, branch, and write/read mode.

Rejected. It creates a generic remote-code-execution surface with a write token. Input validation cannot make arbitrary branch code safe enough for release publication, and it collapses the independent certification boundary.

### B. Reusable workflow for everything

Move all jobs to one `workflow_call` file and invoke it from CI, research, materialization, and certification.

Rejected as the primary architecture. Reuse can reduce setup duplication, but the security boundaries still require distinct callers/permission envelopes. A reusable workflow is an implementation-sharing mechanism, not a permission model.

### C. Small stable workflow set with capability-specific entry points

Recommended.

Keep:

- `ci.yml` — read-only routine regression checks;
- `dataset.yml` — reproducibility/full-build report generation;
- `certify-dataset.yml` — privileged canonical independent certification.

Add only if justified by TDD safety tests:

- `research.yml` — stable **read-only** manual research runner;
- `materialize-release.yml` — stable **privileged, exact-head-bound** immutable release materializer.

Retire ticket-specific `research-*.yml`, `apply-*.yml`, `build-final-*.yml`, `finalize-issue*.yml`, and `sync-*.yml` as the default development mechanism.

`source-path-evolution.yml` becomes the first candidate to migrate to the stable research/reproducibility path.

## Stable read-only research runner

A generic research runner is safe enough only if it has no publication capability:

- `permissions: contents: read`;
- no repository/org secrets;
- checkout explicit requested ref;
- input path validated to a narrow repository-owned namespace (for example `programs/research_*.py` or a registered research task name);
- execute through an argument array / Python entry point, never shell `eval`;
- output only via Actions artifacts or stdout;
- no `git push`, release creation, issue mutation, or workflow mutation.

Even though checked-out branch code can execute arbitrary Python, the damage radius is intentionally limited by the read-only/no-secret token. This runner is for evidence generation, not applying patches.

A registry of named research tasks is safer and more reproducible than accepting an arbitrary shell command. The registry can live in tested repository code and map a task name to command/required public inputs.

## Do not build a generic write-capable patch runner

The repeated `apply-*.yml` pattern should end, but the replacement should **not** be a manual workflow that accepts arbitrary patch text/commands under `contents: write`.

Preferred order:

1. use normal GitHub/API/connector commits for source edits;
2. let ordinary CI validate them;
3. where multi-file atomicity is important, add a tested repository command that performs one narrowly defined maintenance operation, then invoke that operation from an explicitly scoped stable workflow only if there is a recurring use case.

This prevents convenience automation from becoming a general write-token executor.

## Stable immutable release materializer

Release materialization is recurring and merits a dedicated stable workflow, but its procedural contract should live in Python (for example `programs/materialize_release.py`) with unit tests.

Minimum inputs/guards:

- target branch;
- **expected commit SHA** supplied by the caller/agent;
- target TF version, which must equal repository version metadata;
- target `tf/<version>` and `tf-provenance/<version>` must not already exist at the expected head;
- branch remote head must equal expected SHA before build;
- build from that exact SHA;
- run full release gates and historical-immutability checks;
- re-check branch remote head and protected-tree identity after long gates;
- force-add only the explicitly named new immutable artifact/provenance/evidence paths;
- publish artifact commit without editing/deleting workflow files;
- canonical `certify-dataset.yml` independently certifies the committed artifact afterward.

The workflow YAML should only perform checkout/setup and invoke the tested materializer command. It should not contain release policy logic.

## Why temporary workflow self-deletion should stop

Self-deleting one-shot workflows have repeatedly created two classes of release trouble:

- ordinary `GITHUB_TOKEN` writes may be unable to modify workflow files even when `contents: write` is present;
- deleting/adding a release workflow is itself a protected-tree change, which forces another certification cycle and can make a just-produced manifest stale.

A stable materializer removes both problems. Release source identity no longer changes merely because an orchestration helper cleans itself up.

## Recommended canonical set

Target main-tree workflow identities:

1. `ci.yml`
2. `dataset.yml`
3. `certify-dataset.yml`
4. `research.yml` (if the registered-task prototype proves useful)
5. `materialize-release.yml` (after exact-head/least-privilege RED gates are in place)

`source-path-evolution.yml` should migrate out of the canonical set after equivalent reproducibility coverage exists.

Five stable capability-specific workflows are preferable to three workflows plus an unbounded stream of ticket-local identities. The acceptance target is therefore **bounded and intentional**, not the smallest possible integer.

## Research conclusions

1. The main problem is not current `main` YAML count; it is creation of new branch-local workflow identities and privileged one-shot mutation flows.
2. Certification must remain separate from materialization.
3. Read-only research is the safest first consolidation target.
4. Generic write-capable maintenance is specifically rejected.
5. Release materialization should be generalized only around exact-head + immutable-target semantics implemented and tested in repository code.
6. Stable workflows should never self-delete as part of publication.
7. The workflow architecture itself needs regression tests so future agentic work defaults to stable entry points rather than recreating one-shot YAML.

## Implementation gate

No topology changes should be made until a separate plan defines RED tests for:

- allowed canonical workflow identities;
- permission envelopes;
- absence of generic shell/eval inputs in read-only research;
- exact-head/stale-head behavior of materialization code;
- immutable target rejection;
- branch-advance rejection after gates;
- narrow artifact staging;
- certification trigger coverage after removing temporary-workflow globs;
- independent certification remaining mandatory.
