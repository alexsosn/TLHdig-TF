# TLHdig-TF researcher documentation

TLHdig-TF is a pre-alpha Text-Fabric conversion of the TLHdig corpus. This manual describes the **current generated corpus**, its graph model, the distinctions preserved from the source, the information derived by the converter, and the limitations that still matter for research use.

The original TLHdig remains the authoritative interface for consulting individual texts. TLHdig-TF is intended primarily for corpus-scale querying and reproducible computational analysis.

## Start here

- [About the corpus](about.md) — scope, source identity, versions and status.
- [Data model](data-model.md) — node types, slots, structural containment and graph relations.
- [Feature reference](features/0_home.md) — generated reference for the shipped TF features.
- [Text formats](text-formats.md) — transliteration, separators, cuneiform-facing formats and display semantics.
- [Editorial markup](editorial.md) — damage, restoration, erasure and other editorial structures.
- [Identifiers and navigation](identifiers.md) — document identities, section addresses, duplicate identifiers and source-record identity.
- [Morphology](morphology.md) — candidate analyses, ambiguity, selector state and parse status.
- [Cuneiform](cuneiform.md) — line-level source cuneiform, sign alignment and confidence limits.
- [Provenance](provenance.md) — pinned source, repairs, conversion and the optional source-provenance module.
- [Quality and limitations](quality.md) — executable validation, current known defects and appropriate caution.
- [Querying](querying.md) — small Text-Fabric query patterns for the current graph.
- [References](references.md) — upstream, Text-Fabric and project reference material.

## Current-status sources

The prose manual deliberately avoids duplicating large generated inventories. For the exact current state use:

- [`../KNOWN-ISSUES.md`](../KNOWN-ISSUES.md) for the maintained limitation register;
- [`../reports/census.md`](../reports/census.md) for current node counts and basic invariants;
- [`../reports/alignment.md`](../reports/alignment.md) for cuneiform-alignment coverage and diagnostics;
- [`../reports/markers.md`](../reports/markers.md) and [`../reports/contract_a_graph.md`](../reports/contract_a_graph.md) for source-conservation checks;
- [`RELEASE.md`](RELEASE.md) for current-build validation and `BUILD-MANIFEST.json` semantics.

During pre-alpha the repository supports one current generated artifact. Its schema and bytes may change as correctness work lands; historical generated snapshots are not a compatibility promise.
