# Research: line-oriented interlinear reading in Text-Fabric

Issue: #76  
Baseline: certified `main` / TF 0.4.0 at `e46ab029257f27947afd657d596cf46a513f593e`.

## Question

What is the smallest Text-Fabric-native way to make TLHdig morphology read as **line → word → candidate analyses** without replacing the generic TF renderer, losing ambiguity, or duplicating sign/transliteration logic?

This is a research-only gate. It changes no app/config/data behavior.

## Corpus graph already preserves the needed relation

The converter creates every morphological candidate as an `analysis` node covering exactly the same sign slots as its word and connects the word to every candidate via the `analyses` edge. `analysis.index` is the original `mrpN` attribute number; it starts at 0 in real data and has gaps. `nanalyses` records the candidate count.

Consequences:

- word/candidate alignment is graph-backed rather than reconstructed from strings;
- candidate order must use `analysis.index`, never node id;
- several analyses are legitimate source ambiguity and must remain available;
- zero-analysis words must stay zero-analysis;
- a display implementation does not need provenance or raw `mrpN` parsing.

The existing feature metadata also records `nselected`: more than one source analysis may be selected on real words, so an app must not visually crown a single candidate merely because a selection-like feature exists. Preferred-candidate semantics remain outside #76 until separately proven.

## Current app behavior

`app/config.yaml` currently declares:

```yaml
analysis:
  label: '{index}. {lemma} "{gloss}" {morph}'
  features: pos stemclass parse_ok
  level: 1
  hidden: true
```

The label itself is already a useful compact interlinear payload. The main representation defect is that `analysis` is hidden from normal pretty-tree construction, so morphology is not part of the ordinary reading flow.

The existing `app/app.py` custom renderer is intentionally sign-local:

- `plainCustom['sign']` preserves the selected TF text format while adding Hittitological classes;
- `prettyCustom['sign']` decorates sign labels only;
- source-link wrapping is independent of rendering and must remain reusable after `App.reuse()`.

#76 must compose with those hooks, not replace them.

## Pinned Text-Fabric 13.1 rendering contract

Source inspected from the pinned Text-Fabric code used by the repository (`annotation/text-fabric`, commit `1079c68e051947efd955b61ad499e3a9beb03b09`).

### `hidden` is structural

`settings.py` collects every `typeDisplay.<type>.hidden: true` type into `hiddenTypes`. During `unravel.py`, intersecting nodes of those types are removed before chunking/tree construction.

Therefore the first implementation hypothesis must be **config-first**: make `analysis` non-hidden and inspect the resulting real pretty tree before adding custom HTML.

### `prettyCustom` cannot create interlinear content

The renderer calls `prettyCustom[mType](m, mType, cls)` only while constructing CSS class metadata. It can change classes but cannot inject analysis rows/content. It is useful for styling a proven tree, not for constructing the interlinear relation.

### `plainCustom` is too invasive for a line/word solution

When a node type has `plainCustom`, TF skips ordinary recursive rendering for that subtree. A line-level or word-level `plainCustom` would therefore require us to rebuild text/children ourselves, duplicating TF format selection, highlights, source links, sign-local rendering and future TF behavior. Reject this unless a later experiment proves there is no smaller supported extension point.

### `afterChild` is powerful but structurally conditional

For a pretty-rendered parent, TF calls its configured `afterChild` callback after **each direct rendered child** and inserts the returned HTML. This can in principle append morphology after a word, but only if real unravel output establishes that the relevant direct children are stable word units.

Overlapping nodes are fragmentized/reparented by `unravel.py`; assuming `line` direct children are always words without measuring representative trees would couple the app to an accidental DOM/tree shape. `afterChild` is therefore a second-line option, not the default design.

## Candidate designs

### A. Config-only: unhide analyses and use TF tree/layout controls

Change only `typeDisplay.analysis` visibility/layout (and possibly word/analysis `flow`, `wrap`, `stretch`, `level`, `base`, or `children` settings already supported by TF).

Advantages:

- preserves TF highlights, node identity, query-result integration and accessibility;
- zero custom traversal logic;
- candidate nodes remain independently inspectable;
- no duplicate escaping or sign rendering.

Unknown to measure before planning: exact nesting/order in representative real `A.pretty(line)` output when analyses become visible. Because analysis and word cover identical sign slots, the generic unravel ordering may or may not produce the desired word-owned visual grouping.

**Research preference: test this first.**

### B. `afterChild` composition

If config-only output keeps the correct graph relation but cannot place analyses readably, use a narrowly registered callback only after proving which parent/child relation is stable in pinned TF.

Requirements if selected:

- callback must inspect only the child word and its direct `analyses` edge;
- candidates sorted by `analysis.index`;
- all source strings HTML-escaped;
- no global scans;
- callback output textual/structural, not colour-only;
- lifecycle registration must survive `reuse()` beside the existing source-link/sign hooks.

Risk: callback position follows TF's rendered direct-child tree, not the abstract edge graph. Fragmentation/overlap cases must be adversarially tested.

### C. Custom line/word subtree renderer

Reject by default. It duplicates too much TF machinery and would make TLHdig-TF responsible for passage headings, format selection, highlighting, sign rendering and nested node semantics. Use only if A and B are demonstrated impossible and the plan explicitly justifies the compatibility cost.

## Representative cases required before plan freeze

The next gate must inspect real TF 0.4.0 pretty/unravel output for at least:

1. ordinary HFR line with several analysed words;
2. a zero-analysis word;
3. exactly one candidate;
4. several candidates;
5. non-contiguous `analysis.index` values;
6. parse-failed candidate (`parse_ok=0`);
7. damaged/Sumerogram/Akkadogram word so existing sign-local classes are present;
8. mixed/non-Hittite language line (e.g. Akkadian material);
9. a line with cuneiform support, confirming analysis display does not alter text-format behavior;
10. a query-result pretty display/highlight, not only direct `A.pretty(line)`.

Useful source-level examples already identified in #72 include `HT 9` (damage, Sumerograms/Akkadograms and multiple analyses) and HFR/other pages with ordinary stacked analyses. Exact TF nodes should be selected reproducibly by section/features rather than hard-coded unstable node ids where possible.

## Required measurements

For each representative line record:

- unravel parent/child type structure with analyses hidden vs visible;
- candidate order shown vs `analysis.index`;
- whether word and analysis share exact slots as expected;
- number of feature/edge lookups needed by any proposed hook;
- generated HTML shape/classes sufficient for CSS layout;
- whether browser and notebook pretty rendering use the same structure;
- interaction with highlights, `withNodes`, feature display and source links.

No visual implementation should proceed from source inspection alone; at least one real corpus integration fixture must freeze the observed tree contract.

## Performance boundary

The corpus has millions of nodes, but interlinear rendering is local. A valid design may traverse:

- the current line's rendered children;
- one word's `analyses` edge;
- candidate node features for that word.

It must not scan all words/analyses/documents while rendering one line. If a hook is needed, tests should instrument lookup/traversal counts instead of relying only on wall-clock timing.

## Escaping / fidelity boundary

Any custom HTML must escape lemma, gloss, morphology and status values. Config-native TF labels already go through TF's rendering pipeline and are preferred partly for this reason.

`parse_ok=0` is not permission to hide a candidate. It is evidence that structured parsing is incomplete; the candidate still exists and must remain explicit. Raw/provenance strings should not be reparsed merely to make the UI prettier.

## Research conclusion

The graph is already sufficient for faithful interlinear morphology. The remaining question is representation, not schema.

The implementation hierarchy should therefore be:

1. **unhide/configure existing `analysis` nodes and measure real pretty output**;
2. if necessary, add a very small `afterChild` composition over the explicit `analyses` edge after proving a stable parent/child contract;
3. avoid a custom subtree renderer unless both TF-native approaches are demonstrably inadequate.

The plan gate must select among these only after representative real-corpus unravel/HTML fixtures are captured. No schema/version bump is justified by #76 itself.
