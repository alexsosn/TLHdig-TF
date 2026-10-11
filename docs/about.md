# About TLHdig-TF

TLHdig-TF converts the published TLHdig XML corpus into a Text-Fabric graph for corpus-scale analysis. It is an independent project and is not an official TLHdig or Hethitologie-Portal Mainz product.

## Upstream and conversion versions

Two version identities are intentionally separate:

- the **source version** identifies the pinned upstream TLHdig dataset used as conversion input;
- the **TF version** identifies the current conversion model and generated Text-Fabric artifact.

Current TF version: `0.4.0`.

The current source/TF identities are also encoded in repository metadata and checked by the build-validation tooling. During pre-alpha, `main` supports one current generated artifact; older generated snapshots are not a compatibility surface.

## What comes from the source

Source XML supplies the transliterated text, source document identifiers, structure, morphology records, editorial markup, manuscript-apparatus data, line-level cuneiform where available, and source editorial history. The converter preserves source uncertainty rather than choosing a preferred scholarly interpretation without evidence.

Some values are transformed into graph-friendly representations. Derived fields and relations are documented by feature metadata and the domain pages in this manual. When a value is derived, that distinction matters: for example, sign-level cuneiform alignment is computed from line-level source material rather than copied directly from an upstream sign annotation.

## Current maturity

TLHdig-TF is an integration prototype. It already has extensive source-conservation and corpus-validation checks, but known correctness and coverage problems remain. In particular, source repairs, excluded files, ambiguous document identifiers, incomplete modelling and partial cuneiform alignment all affect how results should be interpreted.

Use [`../KNOWN-ISSUES.md`](../KNOWN-ISSUES.md) as the maintained register and generated reports for current counts. A green build means the implemented invariants hold for the current artifact; it does not mean every philological ambiguity has been resolved.

## Source consultation

For reading an individual text, photographs, linked HPM resources and the upstream scholarly presentation, consult TLHdig itself. TLHdig-TF is designed to make relationships across the corpus queryable while retaining a route back to source context.
