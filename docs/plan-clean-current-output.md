# Plan: clean current-artifact rebuild output (#118)

Status: frozen after `docs/research-clean-current-output.md`.

Sequence: research → plan → deterministic RED → minimal implementation → unit/integration GREEN → hosted current-artifact rebuild/validation → exact-head logically independent adversarial review → guarded merge.

## 1. Public behavior

No Text-Fabric schema, feature semantics, CLI arguments, or user query surface changes.

The build contract changes: `python programs/build.py` must generate the current main/provenance modules from a clean owned output state. Files left by an earlier schema/converter must not influence the new artifact.

## 2. Cleanup primitive

Add a narrow helper in `programs/build.py`:

```python
def reset_current_output(
    main_dir: Path,
    provenance_dir: Path,
    *,
    main_parent: Path,
    provenance_parent: Path,
) -> None:
    ...
```

Exact name may vary, but behavior is frozen:

- validate both targets before deleting either;
- reject a target if it is a symlink;
- require each expected parent itself to resolve to the repository's intended `tf` / `tf-provenance` directory passed by the caller;
- require each target's lexical/resolved relationship to be exactly one direct child of its expected parent;
- reject the parent itself, nested descendants, traversal/escape targets, and mismatched parents;
- if valid target exists, remove the entire target tree;
- recreate the main directory only; provenance remains lazily recreated by `split_provenance()`.

Do not glob sibling versions or implement a feature allow/prune list.

## 3. Build orchestration

Keep source/preflight ordering:

1. read repair manifest and corpus file list;
2. verify pinned corpus identity;
3. parse exclusion configuration;
4. reset both current output trees;
5. create ledger and run `convert.build()`;
6. enforce ledger/marker invariants;
7. regenerate `LICENSE`, compact, split/regenerate provenance;
8. leave validation to `programs/validate_current.py`.

Remove `clear_validation_metadata()` from the normal flow because whole-tree reset removes the old manifest and retired metadata automatically.

A conversion failure after reset returns failure with no inherited old manifest.

## 4. RED tests

Create focused tests before production code. At minimum:

- reset removes stale main `.tf` feature;
- reset removes stale provenance `.tf` feature;
- reset removes old `BUILD-MANIFEST.json`, retired `BUILD-COMPLETE` / `RELEASE-CERTIFICATION.json`, generated companions, and nested `.tf/` caches;
- sibling version trees remain byte-for-byte untouched;
- a symlink used as either current target causes failure before either owned tree is deleted, and external symlink target contents remain untouched;
- nested current target (for example `tf/0.4.0/nested`) and wrong-parent target fail before deletion;
- simulated `convert.build()` failure observes that the old current manifest/tree was already removed and returns failure;
- source-identity failure occurs before reset and therefore does not destroy current output;
- a small/synthetic successful orchestration cannot retain a stale feature from the old tree.

The RED commit must contain tests/docs only. Existing tests should continue to pass except the new expectations requiring the absent reset behavior.

## 5. Minimal implementation

Expected production scope is primarily `programs/build.py`. A separate helper module is allowed only if it materially simplifies fail-closed path testing; do not create a generalized filesystem-cleaning abstraction.

Use standard-library filesystem operations (`shutil.rmtree`, `Path.mkdir`). No new dependency.

No changes to converter feature emission, Text-Fabric internals, current manifest schema, or publication semantics.

## 6. GREEN gates

On the implementation head require:

- full `python -m pytest programs/tests -q`;
- ordinary PR CI, including corpus identity, repair/sign/morphology/app/tag/provenance/alignment/signref checks and `check_build_manifest.py` against the committed current artifact;
- a hosted clean Dataset workflow run after the current artifact/manifests are rebuilt as needed, proving full conversion + `validate_current.py` still succeeds.

Because changing `programs/build.py` invalidates the #116 code identity in the committed manifest, update/revalidate the current `BUILD-MANIFEST.json` from the successful hosted build before final ordinary CI. Do not hand-edit its hashes.

## 7. Documentation

Update `docs/RELEASE.md` only as needed to state that `build.py` resets the current generated version directories before conversion and that a failed rebuild leaves an unvalidated partial/absent current artifact rather than preserving stale output.

Do not add another certification or rollback mechanism.

## 8. Independent adversarial review

Freeze the exact GREEN head and review from the raw diff plus #118 research. Try to demonstrate:

- cleanup can escape `tf/<TF_VERSION>` or `tf-provenance/<TF_VERSION>`;
- one suspicious target can be detected only after the other has already been deleted;
- symlinks are followed;
- sibling historical/current-version directories are deleted;
- old manifest/caches/generated companions survive;
- converter failure can still leave a previously valid manifest;
- source-preflight failure unnecessarily destroys a valid current build;
- provenance output is not recreated correctly;
- manifest/staging behavior can accept a half-old/half-new artifact.

Any blocker gets a focused regression test before the correction, then full GREEN and a fresh exact-head review.

## 9. Merge gate

Before merge, refetch `main`; synchronize if needed; require exact-head ordinary CI, successful hosted rebuild/validation evidence, and a no-blocker review. Merge with an expected-head SHA.

## Non-goals

- preserving the previous generated current artifact after a local failed build;
- atomic two-artifact swaps;
- deleting historical sibling version directories (#115 owns that cleanup);
- changing the current manifest schema;
- feature-level prune lists;
- corpus/schema changes.