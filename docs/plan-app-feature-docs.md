# Plan: app-facing feature documentation and Text-Fabric links

Issue: #43
Research: `docs/research-app-feature-docs.md`

## Goal

Make every released app-visible Text-Fabric feature resolve to a maintained generated reference page, give the app a working feature-documentation landing page, and make documentation drift fail deterministically in CI.

This plan is intentionally narrower than #46's comprehensive corpus manual.

## Public layout

Generate:

```text
docs/features/
  0_home.md
  <core-feature>.md
  <optional-provenance-feature>.md
```

`0_home.md` is the app-facing landing page and groups features by role/module.

The earlier broad documentation plan used `docs/features.md` as a placeholder for the future feature index. For the app-facing surface owned by #43, that placeholder is superseded by the Text-Fabric/BHSA-style `docs/features/0_home.md` landing page plus per-feature pages. #46 may extend this generated hierarchy, but should not create a competing feature-semantic source or a second app landing contract.

Update `app/config.yaml` to use:

```yaml
docs:
  docRoot: https://github.com
  docBase: '{docRoot}/{org}/{repo}/blob/main'
  docPage: README
  docExt: .md
  featureBase: '{docBase}/docs/features/<feature>{docExt}'
  featurePage: 0_home
```

The corpus-documentation landing remains the root README for this ticket. #46 may later move that landing to a comprehensive docs index.

## Implementation structure

Add a reusable library:

```text
programs/tlhdig/featuredocs.py
```

with responsibilities:

- streaming `.tf` header parsing;
- core + optional-module feature discovery;
- feature classification;
- canonical-description validation;
- deterministic Markdown rendering;
- expected-output calculation;
- write/check mode.

Add a narrow CLI:

```text
programs/build_feature_docs.py
```

Default behavior writes generated pages for `TF_VERSION`; `--check` exits nonzero if tracked output is missing, stale, internally broken, or contains unexpected generated pages.

#46 can reuse/extend the library rather than replacing it.

## Header contract

`read_header(path)` must stop at the first blank line and return enough structured metadata to distinguish:

- `@node`;
- `@edge`;
- `@edge` + `@edgeValues`;
- metadata fields (`description`, `valueType`, `version`, source/license/DOI fields, etc.).

It must not parse the feature body.

Malformed headers should fail with a path-specific error rather than silently generate incomplete documentation.

## Feature classes

### Core corpus features

Discover every `*.tf` in `tf/<TF_VERSION>`.

For ordinary non-warp features:

- classify node vs edge vs valued edge from header markers;
- require a non-empty shipped description;
- when the feature appears in `featuremeta.DESCRIPTIONS`, require exact equality with the shipped header description.

### Text-Fabric warp/config files

Treat `otype`, `oslots`, and `otext` as explicit infrastructure classes. They still receive pages and index entries because they are shipped app-visible TF files, but their documentation must identify them as Text-Fabric structural/configuration data rather than TLHdig annotations.

Use a small fixed documentation-role map for these three names only.

### Optional provenance module

Discover `*.tf` in `tf-provenance/<TF_VERSION>` and render pages into the same docs namespace. Mark every page and index entry as **optional provenance module; not loaded by default**.

Do not add the provenance module to app defaults or `moduleSpecs`.

## Generated page content

Each feature page is deterministic and contains stable release metadata only:

- title/name;
- module;
- kind;
- description;
- value type where present;
- TF artifact/source version;
- source DOI/license/attribution metadata where present;
- relative link back to `0_home.md`;
- generated notice pointing to the release `.tf` header as source.

Do not emit `dateWritten`, body counts, file sizes, current timestamps, or machine-dependent paths.

## Landing-page content

`0_home.md` states the generated TF version and groups sorted links into:

1. core node features;
2. core edge features;
3. core valued-edge features;
4. Text-Fabric infrastructure/config features;
5. optional provenance features.

The optional section explicitly states how it differs from the default core app data; detailed loading instructions remain in provenance/distribution documentation.

## Drift/check contract

`build_feature_docs.py --check` must compare the complete expected generated tree with the tracked `docs/features` tree and fail for:

- missing expected page;
- stale page content;
- unexpected stale generated page;
- missing released feature from the landing page;
- broken relative Markdown link inside the generated page set;
- canonical description mismatch;
- malformed feature header.

The generated files should carry a recognizable generated marker so the checker can safely distinguish stale generated pages from future handwritten companion material if that becomes necessary. For #43, the directory is planned to contain generated pages only.

## App-link validation

Extend app/documentation tests so they assert:

- `featureBase` is explicit and resolves `<feature>` into `docs/features/<feature>.md`;
- `featurePage` resolves to `docs/features/0_home.md`;
- both the landing page and representative node/edge feature pages exist;
- every relative link emitted by the generated reference resolves within the generated tree;
- the shipped feature-doc tree passes generator check mode.

Do not use live HTTP as the required CI mechanism.

## RED gate

Before production code/config/docs generation, commit failing tests covering at least:

1. streaming header parser classifies a node feature;
2. unvalued edge classification does not treat `valueType` as edge values;
3. `@edgeValues` classifies a valued edge;
4. parser stops at the first blank line and does not consume an adversarial body;
5. warp/config features receive infrastructure classification;
6. optional provenance feature is marked optional;
7. description mismatch against canonical metadata fails;
8. generated expected set includes every discovered core `.tf` file;
9. check mode detects a missing/stale generated page;
10. current app docs config fails the desired explicit `featureBase` / `0_home` contract.

The initial RED commit must precede any implementation/config/generated-doc changes. If independent review later identifies an uncovered acceptance contract, add a new failing regression test before its fix and record that review-driven RED evidence separately.

## Implementation gate

After RED evidence:

- implement `featuredocs.py`;
- implement `build_feature_docs.py`;
- generate the tracked `docs/features` tree;
- fix `app/config.yaml`;
- integrate check mode into the existing app/docs validation path or CI with the smallest non-duplicative change.

Prefer reusing `programs/check_app.py` only for app-link existence/config checks; keep full generated-tree drift checking in the dedicated feature-doc command if coupling them would make the app gate expensive or conceptually muddled. Header-only generation should nevertheless be cheap enough for ordinary CI.

## Test gate

Run at minimum:

```text
python -m pytest programs/tests/test_featuredocs.py -q
python programs/build_feature_docs.py --check
python programs/check_app.py
python -m pytest programs/tests -q
```

CI must also pass the repository's existing corpus/release gates. Record generator runtime/memory or at least confirm it remains header-only and does not scale with feature body size.

No generated TF artifact or certification stamp may change.

## Independent adversarial review gate

The final reviewer must challenge:

- documentation generated from converter intentions instead of the shipped release;
- a released `.tf` file omitted from reference coverage;
- optional provenance presented as core/default-loaded;
- valued/unvalued edge misclassification;
- warp/config files presented as scholarly annotations;
- full-body reads of multi-megabyte features;
- stale/broken GitHub URL composition;
- broken relative links within the generated Markdown tree;
- branch-specific links that will break release use;
- checker behavior that deletes or overwrites non-generated docs unsafely;
- volatile metadata causing perpetual drift;
- test fixtures that simply mirror implementation logic;
- any accidental changes under immutable `tf/0.3.0`, `tf-provenance/0.3.0`, or certification files.

Blocking findings require another implementation → test → independent-review cycle.

## Artifact/version impact

None. This is documentation/app/tooling only and must not allocate a new TF version.

## Completion

#43 is complete when:

- the app's Feature docs and per-feature links resolve to real repository Markdown targets;
- every shipped core feature and both optional provenance features are represented with correct classification;
- generation/check mode is deterministic and header-only;
- generated relative links are internally valid;
- description drift is gated;
- all CI/release checks pass;
- independent adversarial review has no blocking findings.
