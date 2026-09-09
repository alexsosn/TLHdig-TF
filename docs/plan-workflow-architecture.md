# Plan: consolidate GitHub Actions without weakening release safety

Issue: #104
Research: `docs/research-workflow-architecture.md`

Status: plan complete; implementation must begin with RED tests/sentinels.

## Goal

Replace the default practice of creating ticket-specific workflow YAML with a small stable set of capability-specific entry points while preserving or strengthening every release-safety invariant.

This is an orchestration refactor. It must not alter corpus bytes, conversion semantics, scientific gates, or historical release verification.

## Non-goals

- Do not delete or rewrite historical Actions runs.
- Do not create a generic write-capable remote command runner.
- Do not combine release materialization and certification into one trust boundary.
- Do not change TF/source versions merely for workflow consolidation.
- Do not weaken protected-tree coverage, predecessor-delta checks, or immutable artifact policy.
- Do not remove `source-path-evolution.yml` until equivalent reproducibility evidence is proven.

## Architecture

### Stable workflow identities

Long-lived:

- `.github/workflows/ci.yml`
- `.github/workflows/dataset.yml`
- `.github/workflows/certify-dataset.yml`

Planned:

- `.github/workflows/research.yml`
- `.github/workflows/materialize-release.yml`

Migration candidate after equivalence proof:

- `.github/workflows/source-path-evolution.yml`

Ticket-local `research-*`, `apply-*`, `build-final-*`, `finalize-issue*`, and `sync-*` workflow files become forbidden by repository policy except for a documented emergency escape hatch that must itself be reviewed.

## Phase 1 — workflow architecture policy and read-only research runner

This is the safest independent first PR.

### RED tests

Add `programs/tests/test_workflow_architecture.py` with failures against current behavior for:

1. a policy/registry module defining the canonical workflow identities;
2. `research.yml` existing as a stable workflow;
3. `research.yml` declaring only `contents: read` (or stricter) permissions;
4. no `contents: write`, `actions: write`, secrets inheritance, or repository publication step;
5. no shell `eval` / arbitrary command input;
6. task execution delegated to a tested repository registry/CLI rather than hard-coded ticket scripts;
7. a validated explicit checkout ref input;
8. research output restricted to stdout/Actions artifact paths;
9. repository docs stating that new ticket-local workflow identities are not the default.

### GREEN implementation

Add a small module such as `programs/tlhdig/workflow_tasks.py` plus `programs/run_research_task.py`.

The registry maps stable task names to argument-vector builders. It must reject unknown task names and invalid refs/inputs before subprocess execution. Do not concatenate user inputs into a shell command.

Initial registered task should be the existing source-path-evolution reproduction path, because it has a known expected report and pinned external archives. If moving its download mechanics into repository code becomes too broad for Phase 1, register a smaller existing pure-repository research task first and leave source-path evolution for Phase 2.

`research.yml` should:

- be `workflow_dispatch` only initially;
- have explicit `task` and `ref` inputs;
- use `permissions: contents: read`;
- checkout the requested ref;
- call the registry CLI;
- upload only a designated output directory if present;
- have no secrets and no write/publication action.

### GREEN gates

- targeted architecture tests;
- full unit suite;
- ordinary CI on exact head;
- logically independent adversarial review focused on input injection, permission escalation, ref confusion, and accidental publication.

Do **not** remove `source-path-evolution.yml` in Phase 1 unless exact output parity is demonstrated in hosted CI.

## Phase 2 — migrate reproducible research and enforce bounded workflow set

### Research gate

Inventory remaining branch-local research workflow requirements after Phase 1 has been used at least once. Confirm which need public downloads, large artifacts, or special environment setup.

### RED tests

- source-path evolution produces byte-identical `reports/source-path-evolution.md` through the stable runner;
- policy rejects committed ticket-local workflow naming patterns on `main`;
- an explicit allowlist documents canonical workflow filenames;
- the policy test ignores historical branch/run identities and inspects only the candidate tree.

### GREEN

- migrate source-path evolution to the stable research task;
- delete `.github/workflows/source-path-evolution.yml` only after parity is GREEN;
- add contributor/agentic-loop documentation: create repository code/tests, not a new YAML identity, for normal research.

### Review attack

Verify the generic research runner cannot be converted into a write-token executor by a branch-controlled task definition. Prefer the **task registry from the checked-out default/trusted workflow source**, or otherwise make the no-secret/read-only boundary explicit enough that arbitrary branch code has no publication authority.

## Phase 3 — tested immutable release materializer

This is separate from the research-runner PR because it carries write authority.

### Research gate

Extract the invariants from successful/failed historical `build-final-*` workflows and canonical certification:

- exact expected head;
- target version absence;
- historical artifact immutability;
- release-delta baseline;
- protected-tree stability before/after gates;
- branch head unchanged before publish;
- narrow force-add of named ignored artifact paths;
- generated reports only;
- no workflow self-deletion;
- post-publication independent certification.

Record representative historical orchestration failures as regression requirements, including ignored `tf/` staging and workflow-file write rejection.

### RED unit/integration tests

Create a repository module/CLI, provisionally `tlhdig.materialize_release`, and prove RED for:

1. expected SHA differs from branch head;
2. target `tf/<version>` already exists;
3. target provenance version already exists;
4. requested version differs from `TF_VERSION`;
5. protected source tree changes while gates run;
6. remote branch advances while gates run;
7. a historical artifact changes;
8. artifact staging attempts to include an unexpected path;
9. ignored `tf/<version>` is omitted unless explicitly force-added;
10. certification is not treated as part of materialization success.

Use tiny temporary Git repositories and injectable command/gate runners; do not require a full 400 MB corpus build to test control flow.

### GREEN implementation

`materialize-release.yml`:

- `workflow_dispatch` only;
- typed inputs: target branch, expected SHA, target TF version;
- minimal `contents: write`; no unrelated permissions/secrets;
- checkout/fetch exact branch;
- invoke the tested Python materializer;
- publish only if all guards remain true;
- never edit/delete workflow files.

The Python command owns policy decisions and produces a machine-readable materialization report.

The workflow is a thin transport layer, not the implementation.

### Hosted integration

Before retiring any future `build-final-*` mechanism, run one non-publishing dry-run against the current release and one real next-version materialization when a scientifically justified artifact change is ready. The first real use must receive an independent adversarial review before publication.

## Phase 4 — simplify certification triggers

Only after ticket-local release workflows are no longer normal:

### RED

Tests must prove that protected code/tests/policy changes trigger or require fresh certification without depending on globs for temporary workflow filenames.

### GREEN

- remove obsolete temporary-workflow path globs from `certify-dataset.yml` if and only if the protected-tree profile no longer needs such files;
- retain canonical certification workflow self-trigger and relevant protected source/test paths;
- keep per-ref stale-run cancellation;
- preserve branch-only publication validation.

Do not infer correctness solely from trigger coverage: `stamp.check(..., repo_root=...)` remains the local fail-closed correctness boundary.

## Phase 5 — documentation and cleanup

- document canonical workflow responsibilities and permissions;
- document the agentic rule: research code + tests first, stable workflow entry point second; new workflow file only by explicit architecture exception;
- remove superseded branch-local workflow files on active branches when safe, without rewriting history;
- leave historical Actions identities/runs untouched.

## TDD sequencing rule

Every phase is independently mergeable and gets its own RED → GREEN → full CI → logically independent adversarial review loop.

Do not implement Phase 3 merely because Phase 1 is green. Write authority makes release materialization a distinct risk class.

## Acceptance checks

The consolidation is complete when:

- routine research no longer needs a new workflow identity;
- immutable release publication no longer needs a self-deleting `build-final-*` workflow;
- there is no generic write-token arbitrary-command runner;
- canonical certification remains independent;
- exact-head/stale-head/immutability/protected-tree safety is enforced by tested repository code;
- main's workflow set is bounded, documented, and enforced by tests;
- current corpus/release gates and historical stamp verification remain unchanged.

## First implementation slice

Start only with **Phase 1: architecture policy + read-only stable research runner**. It has no corpus artifact or release-policy impact and can be reviewed independently from the privileged materializer design.
