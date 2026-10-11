# Plan: branch-scoped canonical certification publication

Issue: #82

This plan is frozen after research and before production workflow/helper changes.

## Contract

Canonical certification may publish evidence only to a Git **branch**.

The workflow keeps two independent controls:

1. Declarative trigger restriction: `push.branches: ['**']` plus the existing `paths:` filter. Tag pushes therefore do not start canonical certification.
2. Runtime fail-closed validation: before certification/publish work, validate both `GITHUB_REF_TYPE == 'branch'` and `GITHUB_REF` beginning with `refs/heads/`. Derive the destination branch only from that validated fully-qualified ref.

Publication must use an explicit destination:

```sh
git push origin HEAD:refs/heads/${CERT_BRANCH}
```

It must not use `${GITHUB_REF_NAME}` as the branch trust boundary.

`workflow_dispatch` remains supported when dispatched against a branch. A manual/tag context must fail before evidence publication.

## Implementation shape

Add `programs/tlhdig/certification_ref.py` containing a small pure validator plus CLI:

- `certification_branch(ref_type: str, ref: str) -> str`
- raises a dedicated error unless `ref_type == 'branch'`;
- requires `ref` to start with `refs/heads/`;
- rejects an empty branch suffix;
- returns the branch name unchanged, including embedded `/` characters.

The workflow invokes the module using environment-provided `GITHUB_REF_TYPE` / `GITHUB_REF`, writes the validated result to `GITHUB_ENV`, then the existing publication step uses `refs/heads/${CERT_BRANCH}`.

No URL/ref normalization, shell glob interpretation, force push, pull, fetch-rebase, or retry-on-stale behavior is added.

## RED gate

Before production changes, add tests that fail on current main for the intended reasons:

### Validator behavior

- branch + `refs/heads/main` -> `main`;
- branch with slashes -> unchanged branch name;
- tag + `refs/tags/v1` -> rejected;
- `ref_type=branch` with a tag-form ref -> rejected;
- empty/malformed branch ref -> rejected;
- branch/tag short-name collision cannot pass through short-name-only logic.

### Workflow contract

- `workflow_dispatch:` remains present;
- `push:` has an explicit branch-only filter and still retains `paths:`;
- workflow contains an explicit pre-publication ref-validation step;
- publication uses `HEAD:refs/heads/${CERT_BRANCH}`;
- publication no longer uses `HEAD:${GITHUB_REF_NAME}`;
- existing #68 concurrency remains `github.ref` scoped and cancellable;
- no force/pull/rebase is introduced.

Hosted CI must show only these new assertions failing before implementation.

## GREEN / full test gate

Implement only the helper and workflow changes above, then run:

- new targeted tests;
- existing certification-concurrency tests;
- full `programs/tests` suite;
- normal PR CI.

Because this does not alter TF artifacts or release-policy semantics, do not create a new TF version or rebuild immutable corpus data solely for #82.

## Independent adversarial review

A fresh reviewer must inspect the exact final PR head and challenge:

- tag/branch names that collide;
- branch names containing `/`;
- workflow_dispatch semantics;
- trigger filtering accidentally disabling ordinary branch certification;
- validator placed after a write-capable publication action rather than before it;
- shell/refspec ambiguity or injection;
- regression of #68 same-ref concurrency;
- force/pull/rebase or stale-writer behavior;
- hidden dependence on tag certification elsewhere in release/distribution workflows.

Any blocking finding restarts fix -> tests -> fresh independent review.

## Acceptance

- Tag pushes cannot enter canonical push-triggered certification.
- Any non-branch context that reaches the job fails closed before evidence publication.
- Branch push and intended branch manual dispatch remain supported.
- Publication targets an explicit validated branch ref.
- Existing concurrency and non-force publication guarantees remain intact.

## Execution evidence

The frozen gates were executed in order:

- RED head `7bfd13fce9e2f7dfe56a28de67d1f53f43028346`, Actions run `34322373639`: **13 failed, 592 passed**. Every failure was one of the newly frozen branch-ref contracts: missing validator, missing branch-only trigger, missing runtime validation, or the old short-name publication refspec.
- GREEN implementation head `145d04f1a77a59e3aa582defa1a8d35a6e5331f5`, Actions run `34323194327`: full repository CI **passed**.
- Canonical certification then ran successfully on that implementation and appended evidence-only bot commit `ce24745ef7711b90ba7e02f8f11309bfaf797082`, updating release certification metadata for unchanged TF 0.4.0 artifact bytes.

This final documentation-only commit deliberately follows that generated evidence so the PR once again has a human-authored exact head on which ordinary PR CI can run. `docs/**` is outside canonical certification's `push.paths`, so this note does not recursively launch another evidence commit. It changes no workflow/helper/test/artifact semantics. Final merge still requires fresh exact-head CI and logically independent adversarial review.