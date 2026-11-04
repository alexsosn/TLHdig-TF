# Research: certification publication must be branch-scoped

Issue: #82

Date: 2026-09-09

This research is frozen before production workflow changes.

## Current repository behavior

Canonical certification is `.github/workflows/certify-dataset.yml`. It is write-enabled (`contents: write`) and currently has:

```yaml
on:
  workflow_dispatch:
  push:
    paths: ...
```

with no `branches`, `branches-ignore`, `tags`, or `tags-ignore` filter. The publication step ends with:

```sh
git push origin HEAD:${GITHUB_REF_NAME}
```

The concurrency key is correctly full-ref scoped (`certify-dataset-${{ github.ref }}`) and cancellable. That contract belongs to #68 and must not regress here.

The other full-build workflow, `.github/workflows/dataset.yml`, is `workflow_dispatch`/schedule only and uploads reports; it does not publish certification evidence to a Git ref. There is no repository workflow whose intended release/certification contract requires canonical evidence to be written from a tag ref. The currently published GitHub Release is a separate release object targeting `main`.

## Current GitHub Actions semantics

Verified against the current GitHub Actions documentation on 2026-09-09:

- Workflow syntax: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- Context reference: https://docs.github.com/en/actions/reference/workflows-and-actions/contexts

Relevant documented behavior:

1. If neither branch nor tag filters are defined for `push`, the workflow can run for pushes affecting branches **or tags**.
2. If only a `branches`/`branches-ignore` filter is defined, pushes affecting tags do not run that workflow.
3. `paths`/`paths-ignore` filters are **not evaluated for pushes of tags**. Therefore the current `paths:` block does not protect canonical certification from tag pushes.
4. `github.ref` is fully formed: branch refs use `refs/heads/<name>`, tag refs use `refs/tags/<name>`.
5. `github.ref_name` is only the short branch-or-tag name.
6. `github.ref_type` is explicitly `branch` or `tag`.

## Failure mode

A tag push can enter the current write-enabled certification workflow despite the `paths:` list. Once gates pass, publication assumes `GITHUB_REF_NAME` denotes a branch and executes `git push origin HEAD:${GITHUB_REF_NAME}`.

That is not an acceptable safety boundary:

- `GITHUB_REF_NAME` deliberately erases whether the source was a branch or tag;
- a tag and branch may share the same short name;
- correctness would depend on Git refspec resolution/rejection rather than an explicit repository contract;
- future trigger edits could re-introduce tag entry even if a single declarative filter were later weakened.

No evidence was found that canonical certification should ever publish from a tag-triggered context. Tags/releases are distribution identities; canonical certification evidence is committed into a branch history.

## Candidate controls

### A. `push.branches: ['**']`

Supported directly by GitHub. Because only branch filters are defined, tag pushes are excluded. It composes with the existing `paths:` filter: both branch and path conditions must match.

Strength: declarative and cheap. Weakness: a future workflow edit could remove/widen it.

### B. `push.tags-ignore: ['**']`

Also excludes tag pushes, but expresses the policy negatively and is less direct than saying certification pushes are branch-only.

### C. runtime `github.ref_type == 'branch'` / `GITHUB_REF_TYPE` guard

Provides defense in depth and also protects `workflow_dispatch` or a future trigger expansion. Prefer an explicit failure before checkout/gate publication rather than silently relying on the final `git push` to fail.

### D. explicit publication destination

After validating `GITHUB_REF_TYPE=branch` and `GITHUB_REF=refs/heads/<branch>`, derive the branch from the fully-qualified ref and publish to `HEAD:refs/heads/<branch>`. Do not use `GITHUB_REF_NAME` as the trust boundary.

## Selected research conclusion

Use A + C + D:

- branch-only `push.branches: ['**']` alongside existing paths;
- a small deterministic ref validator that accepts only `ref_type == 'branch'` plus `refs/heads/` and returns the branch name;
- the workflow runs that validator before certification publication and stores the validated branch;
- publication uses an explicit `refs/heads/...` destination;
- `workflow_dispatch` remains available on intended branch refs;
- same-ref concurrency remains keyed by `github.ref`, unchanged;
- no force, pull, rebase, or stale-writer behavior is introduced.

This is workflow-safety work only. It does not change TF bytes, release policy, certification semantics, or historical artifacts.
