# Research: app-facing feature documentation and Text-Fabric links

Issue: #43

## Question

What documentation surface does the shipped Text-Fabric app actually need, and how should it be generated without creating a second manual feature inventory or a new documentation hosting stack?

## Current app-link behavior is deterministically wrong

Current `app/config.yaml` contains:

```yaml
docs:
  docRoot: https://github.com
  docBase: '{docRoot}/{org}/{repo}/blob/main'
  docPage: README
  docExt: .md
  featurePage: docs/features
```

There is no explicit `featureBase`.

Under pinned Text-Fabric 13.1.0 the relevant defaults are:

```text
docUrl      = {docBase}/{docPage}{docExt}
featureBase = {docBase}/features/<feature>{docExt}
featurePage = home
```

`tf.advanced.links` constructs the feature-documentation landing URL by replacing `<feature>` in `featureBase` with `featurePage`.

Because TLHdig-TF overrides `docBase` to the repository root, the implicit per-feature URL becomes:

```text
https://github.com/alexsosn/TLHdig-TF/blob/main/features/<feature>.md
```

and the current `featurePage: docs/features` makes the landing URL:

```text
https://github.com/alexsosn/TLHdig-TF/blob/main/features/docs/features.md
```

Neither target exists. `docs/features/` is absent on current main. This is a path-contract bug, not merely missing prose.

## One `featureBase` template serves both landing and individual feature links

Text-Fabric uses the same `featureBase` template for:

1. individual feature pages, by substituting the feature name;
2. the app's `Feature docs` landing link, by substituting `featurePage`.

A layout with a real file inside the feature directory therefore fits the API naturally:

```text
docs/features/0_home.md
docs/features/lemma.md
docs/features/joined.md
...
```

with:

```yaml
featureBase: '{docBase}/docs/features/<feature>{docExt}'
featurePage: 0_home
```

BHSA uses this exact convention: its `docs/features/` contains `0_home.md` plus individual feature pages, and its app uses `featurePage: 0_home`. This is a transferable Text-Fabric convention rather than Hebrew-specific behavior.

A `README.md` landing page could also work, but `0_home.md` maps directly onto TF/BHSA behavior and does not rely on GitHub's special directory-README rendering.

## Scope boundary with #46

#46 owns the comprehensive researcher-facing manual: corpus scope, graph model, Hittitological semantics, morphology, cuneiform, provenance, conversion, quality, querying, reproducibility, references, and navigation.

#43 should therefore generate only the feature-reference surface required by the app and wire the app to it. It should expose enough stable metadata for a researcher to know what a feature is, but should not grow into the complete corpus manual.

## Shipped feature surface

`tf/0.3.0/BUILD-COMPLETE` records:

```text
tfVersion=0.3.0
features=139
```

The core directory contains the released `.tf` files. The generated reference should discover the release from `TF_VERSION` and the actual `.tf` files rather than maintain a handwritten list.

The optional provenance module `tf-provenance/0.3.0` separately contains:

- `src_span.tf`;
- `srcxml.tf`.

Its README explicitly states that these are not required for ordinary reading/querying and add byte-exact source round-trip data. They must never be presented as default-loaded core features.

## Feature metadata available in the shipped artifact

Current `.tf` headers already expose stable release metadata such as:

- feature kind (`@node` or `@edge`);
- `@edgeValues` for valued edge features;
- `@description`;
- `@valueType`;
- corpus/source version;
- TF artifact version;
- license/attribution/source DOI where emitted.

For example `joined.tf` is an edge feature with `@edgeValues`; `joinLeft.tf` is an unvalued edge even though its header also carries `@valueType=str`. Therefore valued-edge classification must use `@edgeValues`, not `valueType` or body shape.

The warp/config files need explicit treatment:

- `otype` is structural node-type data;
- `oslots` is the TF slot-mapping warp edge;
- `otext` is Text-Fabric text/section/format configuration rather than an ordinary scholarly feature.

They should be documented as Text-Fabric infrastructure, not silently omitted and not presented as domain annotations.

## Semantic source of truth

`programs/tlhdig/featuremeta.py` is the converter-side canonical semantic description registry for generated corpus features.

For release documentation, however, the shipped `.tf` header is the authoritative statement of what the release contains. Otherwise documentation can accidentally describe a planned converter state rather than the artifact users actually load.

The safe contract is:

1. generate pages from the shipped header;
2. where a feature is governed by `featuremeta.DESCRIPTIONS`, assert the shipped `@description` equals the canonical converter description;
3. fail generation/check mode on divergence rather than choosing one silently;
4. use a tiny explicit documentation-only map only for TF warp/config roles that are not corpus semantic features.

This avoids two independently maintained semantic inventories.

## Generator must stream headers only

Several feature files are tens of megabytes (`oslots`, sign text features, and optional provenance files). Loading full `.tf` files simply to render metadata would make documentation generation needlessly scale with corpus body size.

A feature-doc metadata reader should:

- open the `.tf` file as text;
- consume only the header up to the first blank line;
- parse marker lines and `@key=value` lines;
- never inspect the feature body.

The implementation should have a regression test proving it stops at the header boundary.

## Generated page contract

A per-feature page needs only stable release facts:

- feature name;
- module (`core` or optional provenance);
- kind (`node`, `edge`, `valued edge`, or TF infrastructure/config);
- description;
- value type when meaningful;
- source/corpus version and artifact version where present;
- source DOI/license/attribution links or text when present;
- a generated-file notice.

Avoid volatile facts such as `dateWritten`. Avoid corpus-wide value counts in #43 because they require reading bodies and belong to broader schema/reference work if later justified.

`0_home.md` should group links into:

- core node features;
- core edge features;
- core valued-edge features;
- Text-Fabric warp/config features;
- optional provenance features, visibly marked opt-in.

## Hosting decision

No MkDocs or GitHub Pages deployment is needed for #43.

Repository Markdown is sufficient because:

- the app already links to GitHub blob pages;
- the problem is the current path composition, not rendering capability;
- generated files can be version-controlled and checked for drift;
- adding a documentation deployment stack would add maintenance without improving this app contract.

#46 may separately decide whether a richer documentation site is worthwhile for the complete manual.

## Validation requirements

The feature-doc tooling should support deterministic generation and check mode. At minimum it must detect:

- a released core `.tf` feature with no generated page/index entry;
- an optional provenance feature being omitted or mislabeled as core;
- stale generated output;
- converter-description/header drift for canonical corpus features;
- wrong `featureBase`/`featurePage` app configuration;
- incorrect edge-valued classification;
- accidental full-body reads.

The app URL contract can be checked locally by applying the documented Text-Fabric substitution rules; ordinary CI must not depend on GitHub availability.

## Artifact impact

This work changes documentation, app configuration, generator/check tooling, and tests only. It does not change TF nodes, edges, feature values, source conversion, or immutable `tf/0.3.0` / `tf-provenance/0.3.0` artifacts and therefore requires no new TF version.

## Conclusion

The smallest correct #43 implementation is an explicit app `featureBase`, a TF-native `docs/features/0_home.md` landing, generated per-feature pages derived from streaming release headers, and a deterministic drift/completeness check. Comprehensive semantic documentation remains under #46; a documentation hosting stack is unnecessary here.
