# Morphology and ambiguity

Morphological annotation is represented as a separate analytical layer. A `word` may have zero, one or several candidate `analysis` nodes; the graph does not require one candidate to be treated as authoritative when the source does not justify that choice.

## Candidate analyses

The `analyses` edge connects a word to all preserved candidates. Candidate order is represented by `analysis.index`, which follows the source `mrpN` index space rather than TF node-number order. Gaps in the source index space are meaningful evidence and are not renumbered away.

Candidate features include fields such as `lemma`, `gloss`, `morph`, `pos`, `stemclass` and `parse_ok`. Use the generated [feature reference](features/0_home.md) for exact current definitions.

## Parse status

`parse_ok` describes whether the converter could parse a source morphology record into the current structured representation. It is not a scholarly validation score. A parse failure should remain visible rather than being discarded merely because the candidate is inconvenient to query.

## Selector state

`mrpsel` and `mrpsel_kind` preserve source analysis-selection/disambiguation mechanics, including numeric and special selector cases. They must not be conflated with HFR's broader annotation workflow status.

In particular, HFR's grey/magenta presentation distinguishes workflow stages documented by HFR; the distributed per-word selector does not provide a general corpus-wide validation-stage feature. TLHdig-TF therefore does not infer such a feature or colour from `mrpsel_kind`.

## Current open morphology issues

The source contains additional morphology cases that are not yet fully modelled:

- leading HFR control/generation markers can contaminate current lexical lemma values; #92 owns the evidence-based separation;
- morphology attached to layout-only source words needs an explicit disposition (#105);
- morphology attached to nested source words needs a source-semantic model that does not duplicate textual slots (#109).

These are current limitations, not hidden exclusions. Consult [`../KNOWN-ISSUES.md`](../KNOWN-ISSUES.md) and the relevant generated morphology reports before treating annotation coverage as complete.

## Querying

When results depend on morphology, preserve the candidate identity or state your selection rule. A frequency count over analyses is not automatically the same quantity as a count over words.
