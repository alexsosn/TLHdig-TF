# Editorial markup and damage

TLHdig source markup records damage, restoration and other editorial interventions. TLHdig-TF models the affected extents so these states can be queried independently from the surface transliteration.

## Clusters and sign flags

Editorial ranges are primarily represented by `cluster` nodes covering the affected sign slots. Current marker families include source states such as deletion/lacuna, `laes`, erasure (`ras`), addition/restoration (`add`) and quotation/related marking (`quot`). Sign-level features expose the corresponding coverage where appropriate.

The converter and an independent validation gate compare source markers with graph coverage. Current counts belong in [`../reports/markers.md`](../reports/markers.md), not in this page.

## Spans and point statements

Not every editorial statement has a positive textual width. Some source constructs are point-like or occur at a boundary. A query about *material covered by damage* should therefore distinguish a positive-width cluster from a zero-width editorial statement rather than treating every matching node as a damaged character range.

The `width` and related cluster metadata make this distinction queryable where modelled.

## Overlap

Editorial spans may cross word or line boundaries. This is one reason the corpus uses `sign` as its slot type: the graph can represent the affected sign interval without forcing the source annotation into a word-only hierarchy.

## Source repairs and limits

Some malformed upstream XML requires byte-pinned repairs before parsing. A subset of crossing-tag repairs moves a structural boundary, so parseability alone cannot prove the intended editorial structure. Those cases remain explicitly tracked and should not be treated as fully resolved merely because the graph loads successfully.

Consult [`../reports/crossing-tag-review.md`](../reports/crossing-tag-review.md), [`../reports/contract_a_graph.md`](../reports/contract_a_graph.md) and [`../KNOWN-ISSUES.md`](../KNOWN-ISSUES.md) before making conclusions that depend on repaired spans.

## Querying rule

Filter on graph features and cluster relations, not rendered punctuation or typography. Presentation may make damage easier to read, but the graph is the query contract.
