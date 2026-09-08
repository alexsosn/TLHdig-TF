# Research: canonical release certification concurrency

Issue: #68.

This freezes the research gate before changing `.github/workflows/certify-dataset.yml`.

## Observed failure mode

During 0.4.0 finalization, several pushes to `research/sign-lang-19` triggered overlapping `Certify shipped dataset` runs. Each run checked out its triggering SHA, spent roughly the full release-certification time validating the corpus, then attempted to commit generated certification evidence back to the same branch.

The important concrete case is Actions run `34263510099` on commit `1b254b251c0e030ca84822453e17299dc983f461`:

- the full `release_check.py --mode regression-valid` suite passed;
- the run generated `tf/0.4.0/BUILD-COMPLETE` and `tf/0.4.0/RELEASE-CERTIFICATION.json`;
- its evidence commit was `70f338db`;
- `git push origin HEAD:research/sign-lang-19` was rejected non-fast-forward because the branch had advanced.

The later quiet-head run `34265773657` started on `ae016a2c08871eb3a3c6cd9371bb2c9f28fdf0de`, but before it could finish the branch advanced again through the independent review RED/GREEN pair `c71cdf2…` → `9451e8c…`. That run is therefore also incapable of publishing valid evidence for the current head.

This is **not** a corpus-semantic failure. It is same-workflow/same-branch concurrency plus legitimate branch advancement.

## Safety property already working

The final push is an ordinary fast-forward push. A stale certification run cannot force-push, rebase, or attach evidence generated from an older protected tree to a newer branch. The observed non-fast-forward rejection is desirable and must remain unchanged.

The defect is wasted work and delayed convergence: obsolete runs continue consuming the expensive release suite even after a newer push makes their result unpublishable.

## GitHub Actions concurrency mechanism

GitHub Actions supports workflow/job concurrency groups. With a group that is stable for one workflow + branch/ref and `cancel-in-progress: true`, a newer run cancels an older in-progress run in the same group while leaving unrelated branches independent.

The contract needed here is branch/ref scoped, not repository-global:

- two certification runs on `research/sign-lang-19` must serialize/cancel;
- a certification run on another branch must not cancel it merely because the workflow name is the same;
- stale-run push semantics remain ordinary non-force Git behavior.

A suitable group can include `${{ github.workflow }}` and `${{ github.ref }}`. `github.ref` is preferable to a manually parsed branch name because it is the event's exact ref identity and keeps tags/branches distinct.

## Current workflow gap

`.github/workflows/certify-dataset.yml` currently has no top-level `concurrency:` block. Therefore rapid pushes can schedule overlapping full release certifications for the same ref.

No release gate, artifact byte, certification policy, path trigger, or evidence writer needs to change to solve #68.

## Boundary with #69

#68 answers **which same-ref run should be allowed to continue**. #69 separately owns **what code/config/input changes invalidate old certification evidence**. A concurrency block must not be treated as a substitute for fail-closed dependency identity.

## Research conclusion

The smallest safe fix is top-level workflow concurrency with:

- a group containing workflow identity and exact ref;
- `cancel-in-progress: true`.

The existing final non-fast-forward push remains the second line of defense. RED must prove the current workflow lacks this contract before the workflow changes.