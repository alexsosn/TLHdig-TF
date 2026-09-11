# Research: one current pre-alpha artifact on `main` (#115)

## Scope

TLHdig-TF is pre-alpha and has no compatibility promise for every generated intermediate corpus. The active policy is one current generated dataset plus its optional provenance module. This research defines the final destructive cleanup after #116 retired recursive certification and #118 establishes clean current-tree rebuilds.

The cleanup is intentionally narrower than a versioning redesign. The current physical path remains `0.4.0`; this work removes historical generated siblings from the active tree, updates live consumer guidance, and adds a small layout regression guard.

No historical Git commits/tags are rewritten. Old research/plan documents remain historical evidence where their old paths are explicitly part of what they were describing.

## Current generated layout

At post-#116 `main`, both generated roots contain exactly four sibling version directories:

```text
tf/
  0.1.0/
  0.2.0/
  0.3.0/
  0.4.0/

tf-provenance/
  0.1.0/
  0.2.0/
  0.3.0/
  0.4.0/
```

`0.4.0` is the current supported development artifact. The destructive ownership set is therefore exactly these six trees:

- `tf/0.1.0`
- `tf/0.2.0`
- `tf/0.3.0`
- `tf-provenance/0.1.0`
- `tf-provenance/0.2.0`
- `tf-provenance/0.3.0`

`tf/0.4.0` and `tf-provenance/0.4.0` are explicitly outside the deletion set and must remain byte-identical through this cleanup.

## Why keep the version-named current path

There is no user benefit in introducing `tf/current` during this cleanup.

The current version path is already coherent across active code and documentation:

- `programs/tlhdig/__init__.py` declares `TF_VERSION = "0.4.0"`;
- `programs/build.py`, current validation and manifest code derive paths from that constant;
- `app/config.yaml` loads version `0.4.0` under `/tf`;
- README direct `Fabric` examples use `tf/0.4.0`;
- the current build manifest records `tf/0.4.0` and `tf-provenance/0.4.0`.

A `current` alias would add another naming layer and app/distribution migration while solving no present problem. Pre-alpha mutability is a policy property: bytes at `0.4.0` may be replaced as the converter evolves until the project deliberately adopts stable compatibility semantics.

## Runtime dependency audit

Repository searches for `tf/0.1.0`–`tf/0.3.0` are dominated by:

1. the generated historical trees themselves;
2. dated research, plans and old reviews documenting previous states;
3. old release/certification research that is no longer active policy.

The active build, app and current validator do not require a predecessor dataset.

Historical documents should not be mass-edited just to remove old path strings. For example, a 2026-08 research note saying that measurements were taken on `tf/0.1.0` is more accurate if it keeps that statement. Git history still makes the referenced bytes recoverable.

## Live documentation exception: Agora integration

`docs/AGORA-INTEGRATION.md` is active consumer documentation, not merely historical research. It currently has two different temporal layers:

- current direct loading is correctly documented as `Fabric(locations="tf/0.4.0")`;
- a quoted Agora registry example still shows an old ref and `tf_path: tf/0.1.0`, followed by text explaining that the pin is stale.

Once `tf/0.1.0` is absent from `main`, this must not look like supported current installation guidance. The cleanup should update the live section to the current registry/install contract if the external registry has already moved, or clearly label the old YAML as historical state and state the current required path/ref coordination.

The cleanup must not invent an Agora ref without checking the actual registry state when implementation begins; Agora is external and may have changed since this research snapshot.

## Repository/CI cost

Hosted Actions runs repeatedly show shallow checkout materializing roughly 25,000 repository paths, with fetch/checkout taking a substantial fraction of a minute before Python work begins. The repository currently carries three complete obsolete main snapshots plus three provenance snapshots.

Deleting them reduces active-tree clone/checkout/disk cost for every new user and CI job. This is directly aligned with the pre-alpha priority of easy local installation and low unnecessary disk use.

This cleanup does not rewrite Git history, so an existing clone's object database will not immediately shrink until Git maintenance/reclone. The benefit is to the active tree, fresh clones, sparse consumers and future commits—not retroactive repository-history erasure.

## Deletion mechanism

Hundreds of generated feature files should not be deleted through hundreds of contents-API commits. Git supports constructing one new tree from the current tree with the six historical subtree entries removed, then one commit pointing to that tree.

The GitHub connector exposes the required Git-object operations (`create_tree`, `create_commit`, `update_ref`), so the implementation can be one atomic destructive commit after RED is observed.

Safety rule: tree deletion entries must name the six exact version-root paths. Do not enumerate/glob version patterns at runtime and do not delete an entire `tf` or `tf-provenance` parent.

The current `0.4.0` subtree SHAs should be recorded immediately before constructing the deletion commit and checked again in the resulting tree.

## Regression policy after cleanup

The repository needs a small policy test, not release machinery.

The useful invariant is:

```python
supported generated directory names under tf/ == {TF_VERSION}
supported generated directory names under tf-provenance/ == {TF_VERSION}
```

This catches accidental reintroduction of `0.5.0` alongside `0.4.0` during pre-alpha rather than replacing the current artifact, and it catches a forgotten historical directory.

The test should also assert that the active current paths exist and contain the expected minimum entry points (`otype.tf` for main and expected provenance files/module where applicable).

Do not make this test scan historical Git refs/tags or enforce semantic version ordering. It is an active-tree layout assertion only.

## RED shape

After #118 is merged and this branch is synchronized with updated `main`, add tests/docs before deletion. RED should fail only because the six historical siblings still exist and because live Agora documentation still exposes a deleted-path-looking example.

At minimum:

1. generated root directory set equals `{TF_VERSION}` for `tf`;
2. generated root directory set equals `{TF_VERSION}` for `tf-provenance`;
3. `tf/<TF_VERSION>/otype.tf` exists;
4. current `BUILD-MANIFEST.json` exists and ordinary manifest verification remains the integrity gate;
5. active app config resolves `TF_VERSION`;
6. current README/user-facing direct-load guidance resolves `TF_VERSION`;
7. active Agora integration guidance does not recommend one of the historical deleted paths as a current installation target.

Historical research docs are explicitly excluded from the stale-string assertion.

## Manifest and #118 interaction

Historical sibling deletion must not require regenerating the current manifest: the current manifest's output identity is closed-world only over `tf/<TF_VERSION>` and `tf-provenance/<TF_VERSION>`. Removing sibling directories is outside that identity.

Before deletion, require #118 merged so clean rebuilds cannot inherit obsolete files inside the current tree. After deletion, run `check_build_manifest.py` against unchanged current bytes and ordinary corpus/app CI.

If current `0.4.0` bytes or current code inputs are changed while synchronizing this branch, stop and follow the normal manifest refresh process rather than treating the cleanup as metadata-only.

## Relationship to #122

#122 addresses wall-clock `@dateWritten` injected by Text-Fabric and future clean-build byte reproducibility. That defect does not make historical siblings necessary.

#115 can remove `0.1.0`–`0.3.0` after #118 as long as the committed current artifact validates against its own manifest. #122 can then make future replacements byte-reproducible without carrying predecessor artifacts.

## Adversarial review focus

The final independent review should attempt to prove that the deletion:

- removed or modified `tf/0.4.0`;
- removed or modified `tf-provenance/0.4.0`;
- deleted source XML, reports, app files or converter code through an over-broad tree operation;
- left any historical generated sibling behind;
- introduced a `current/` alias or a second supported path;
- broke app/direct loading;
- invalidated the committed current manifest;
- rewrote historical research claims unnecessarily;
- left active consumer documentation pointing users at a deleted path;
- added predecessor/history checks back into ordinary validation.

Any blocker gets a focused regression before correction and a fresh exact-head review.

## Conclusion

The safe final #115 cleanup is straightforward once #118 lands: keep the existing `0.4.0` physical current paths, remove exactly six historical sibling trees in one atomic Git-tree commit, update live Agora consumer guidance, and add a small active-tree layout regression test. Git history remains the archive; `main` stops paying clone, checkout and review costs for obsolete generated pre-alpha snapshots.
