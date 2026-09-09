# Research: integrating sign-language preservation with current main

Issue #19 originally branched from a repository state where `release-v3` was current. While the sign-language implementation was being built and corpus-tested, `main` advanced by 57 commits and independently introduced two release-facing capabilities: generated per-feature documentation and predecessor-delta certification. Current `main` uses `release-v4` for the predecessor-aware contract and has already re-certified immutable TF 0.3.0 under that policy.

A direct merge is therefore unsafe: the feature branch had also used the name `release-v4`, but for a different required gate set containing `sign-language`. Reusing one policy identifier for two incompatible contracts would make historical/full certification ambiguous.

## Integration findings

The combined current policy must be a new `release-v5` contract. Historical contracts remain immutable:

- `release-v3`: the pre-predecessor full certification profile;
- `release-v4`: current-main predecessor-aware profile, including `predecessor-delta` and `releaseDelta`;
- `release-v5`: v4 plus the required `sign-language` gate after `structure`.

TF 0.4.0 is a post-baseline release. The certified predecessor is TF 0.3.0 with module-aware digest `sha256:93790f9e283c3c3d29d8a751b1eecbb7fd908745470aa36b9cec0525b90182d1`. Because sign-level language extends the existing `lang` node feature rather than adding another feature basename, the expected semantic serialized delta is exactly:

```text
main:lang.tf
```

The predecessor comparator deliberately ignores documentary header churn such as `@version` and `@dateWritten`; unrelated feature bodies, loader-visible value types, edge semantics, additions, removals, or config changes remain failures.

Current main also generates `docs/features/` from shipped TF headers and canonical `featuremeta` descriptions. Since 0.4.0 changes both the artifact version and the meaning/coverage of `lang`, the final build must regenerate that reference from the materialized 0.4.0 artifact before its post-build unit/docs checks and commit the deterministic pages with the artifact.

## Integration acceptance criteria

The synchronized branch must be 0 commits behind `main`; preserve main's v4 historical verification and predecessor machinery; expose 0.4.0/sign `lang` in the app; certify only `main:lang.tf` as the 0.3.0→0.4.0 semantic delta; regenerate the feature reference from 0.4.0; and rerun the exact sign-language, predecessor-delta, full unit, app, feature-doc, structure, manuscript, historical-artifact, and full release-certification gates.
