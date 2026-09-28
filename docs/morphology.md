# Morphology and ambiguity

Morphological annotation is represented as a separate analytical layer. A `word` may have zero, one or several candidate `analysis` nodes; the graph does not require one candidate to be treated as authoritative when the source does not justify that choice.

## Candidate analyses

The `analyses` edge connects a word to all preserved candidates. Candidate order is represented by `analysis.index`, which follows the source `mrpN` index space rather than TF node-number order. Gaps in the source index space are meaningful evidence and are not renumbered away.

Candidate features include fields such as `lemma`, `gloss`, `morph`, `pos`, `stemclass`, `mrp_control` and `parse_ok`. Use the generated [feature reference](features/0_home.md) for exact current definitions.

## Analysis-generation control markers

TLHdig/HFR stores an upstream control run at the beginning of many source `mrpN`
first fields. The current converter separates the 21 source-observed control families
from lexical content. The cleaned citation form is exposed as `analysis.lemma`; the
complete source run is retained verbatim in sparse `analysis.mrp_control`.

The individual glyphs inside `mrp_control` are intentionally opaque here. Public HFR
documentation establishes that this syntax belongs to the annotation-generation
machinery, but does not provide enough evidence to assign a reliable linguistic meaning
to every compound run. Queries should therefore treat `mrp_control` as provenance/status
syntax rather than as morphology or as a replacement for `mrpsel`.

Every control-normalized analysis retains its exact source `mrpN` string in `raw`.
Broad leading symbols outside the researched grammar — for example `½`, `=`, `?`,
`[` and `°` — are not stripped. A future circled or parenthesized control-like run
outside the known grammar is a parse failure and is withheld from `lemma`/lexeme identity
until researched.

The corpus census and exact grammar are recorded in
[the #92 research note](research-mrp-control-markers.md).

## Parse status

`parse_ok` describes whether the converter could parse a source morphology record into the current structured representation. It is not a scholarly validation score. A parse failure should remain visible rather than being discarded merely because the candidate is inconvenient to query.

## Selector state

`mrpsel` preserves the raw source `mrp0sel` value. `mrpsel_kind` classifies that local selection/disambiguation state; it is not an annotation validation score.

The current selector cases are:

| Source `mrp0sel` case | `mrpsel_kind` | Interpretation |
|---|---|---|
| empty/missing | `none` | no source selector is supplied for the word |
| numeric selector such as `1`, `1a` or `1bR` | `analysis` | source candidate/alternative selection; multiple numeric tokens remain multiple selectors |
| `???` | `unknown` | unresolved selector state |
| `???` followed by a numeric token, such as `??? 0a` | `unknown` | still unresolved; the numeric selector is preserved as a fallback hint rather than reclassifying the word as resolved |
| `DEL` | `DEL` | source deletion/special selector state, not an analysis candidate index |
| `AKK`, `HURR`, `HAT`, `SUM`, `LUW` | matching `AKK`, `HURR`, `HAT`, `SUM`, `LUW` | source language-special selector state; these labels are preserved as selector classes rather than turned into morphological analyses |

A special selector can coexist with numeric detail. The parser preserves the numeric selector information where present while the special/`unknown` kind remains the selector class. Lower-case and upper-case suffix letters on numeric selectors are preserved separately as base/clitic alternative choices; group selectors are likewise retained rather than collapsed into one arbitrary candidate.

These fields describe **source selection/disambiguation mechanics**. They must not be conflated with HFR's broader annotation workflow status. In particular, a numeric selector does not by itself prove that the live HFR UI would label that word manually pre-validated.

HFR's grey/magenta presentation distinguishes workflow stages documented by HFR; the distributed per-word selector does not provide a general corpus-wide validation-stage feature. Likewise, document-level header `<annot>` events are editorial/history provenance and are not a word-level validation-status proxy. TLHdig-TF therefore does not infer a validation feature or colour from `mrpsel_kind` or `<annot>`.

The evidence and the automatic → manual pre-validation → full-validation distinction are documented in [the annotation-status research](research-annotation-status.md). That research also explains why live presentation classes and project-level completion records cannot be mechanically reconstructed from `mrp0sel` alone.

## Current open morphology issues

The source contains additional morphology cases that are not yet fully modelled:

- morphology attached to layout-only source words needs an explicit disposition (#105);
- morphology attached to nested source words needs a source-semantic model that does not duplicate textual slots (#109).

These are current limitations, not hidden exclusions. Consult [`../KNOWN-ISSUES.md`](../KNOWN-ISSUES.md) and the relevant generated morphology reports before treating annotation coverage as complete.

## Querying

When results depend on morphology, preserve the candidate identity or state your selection rule. A frequency count over analyses is not automatically the same quantity as a count over words.
