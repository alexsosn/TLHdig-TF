# Research: upstream TLHdig representation semantics for the Text-Fabric app

Issue: #72
Baseline: certified `main` / TF 0.4.0.

## Purpose

Treat the original TLHdig web application as a scholarly representation reference, not as HTML to clone. The question is which visual/interaction choices communicate corpus semantics that should shape the Text-Fabric reading experience, and which are legacy PHP/search implementation details that should remain upstream-only.

This research does **not** change `app.py`, `config.yaml`, corpus data, or release artifacts.

## Live upstream evidence

Representative pages inspected on 2026-09-09:

- `KBo 52.10` → displayed as **KBo 52.10+ (CTH 344)** with the full joined publication list `KBo 52.10 + KUB 33.120 + KUB 33.119 + KUB 48.97 + KUB 36.31 + CHDS 6.157`; source label `[by HPM Mythen]`; line-oriented interlinear morphology.
- `KUB 23.77` → displayed as **KUB 23.77a+ (CTH 138)** with four explicit fragments and publication identities; lines carry fragment + edge/surface labels.
- `IBoT 4.175` → `[by HFR Basiscorpus]`; ordinary lines followed by aligned gloss/morphology rows; several words expose multiple analyses; `Text bricht ab` is reading-visible structure.
- `KUB 55.25` → explicit `Zeile abgebrochen` lines as well as ordinary transliteration and analysis.
- `KBo 46.60` → explicit `lk. Kol.` / `r. Kol.` column labels and `bricht ab` state.
- `CHDS 6.81` → `[adapted by TLHdig]` plus `ed. Oğuz Soysal (2025-01-24)` before the text.
- `KBo 71.186` → `[adapted by TLHdig]` plus `ed. Daniel Schwemer (2025-03-07)`.
- `KBo 23.113` → erasure/damage in the reading text and highly ambiguous word analyses rendered as stacked alternatives.
- `HT 65`, `KBo 52.115`, `IBoT 4.210`, `KUB 60.106` → additional HFR examples confirming that line → word → interlinear analysis is the normal reading grammar, not a special-case presentation.

Live URLs used in this pass:

- https://hethport.net/TLHdig/tlh_xtx.php?d=KBo+52.10
- https://hethport.net/TLHdig/tlh_xtx.php?d=KUB+23.77
- https://hethport.net/TLHdig/tlh_xtx.php?d=IBoT+4.175
- https://hethport.net/TLHdig/tlh_xtx.php?d=KUB+55.25
- https://hethport.net/TLHdig/tlh_xtx.php?d=KBo+46.60
- https://hethport.net/TLHdig/tlh_xtx.php?d=CHDS+6.81
- https://hethport.net/TLHdig/tlh_xtx.php?d=KBo+71.186
- https://hethport.net/TLHdig/tlh_xtx.php?d=KBo+23.113
- https://hethport.net/TLHdig/corpus.php

The web UI consistently exposes a legend for **INTERLINEAR GLOSSING** and **ANNOTATION STATUS**, distinguishing `pre-validated (magenta text)` and `not validated (grey text)`. This pass establishes that validation status is an upstream reading semantic, but it does **not** yet establish a safe TF feature mapping for that colour/status. Do not infer one from colour or from generic edit metadata.

## Upstream reading grammar

### 1. The line is the primary scholarly reading unit

The web edition does not present a generic object tree first. A page is read as an ordered sequence of scholarly lines with labels such as:

- `Vs. III 1`
- `rev. III 1´`
- `lk. Kol. 1′`
- `r. Kol. 4′`
- fragment-qualified labels such as `(Frg. 1) Vs. I 1`.

Broken lines/columns and text termination are visible in sequence rather than hidden in metadata panels.

### 2. Morphology is interlinear, not peripheral metadata

Each transliterated line is followed by word-aligned cells containing gloss and morphology. Multiple candidate readings are stacked inside the same word column. This preserves ambiguity while keeping the relationship between surface token and analysis visually immediate.

This is the largest representational difference from the current TF app. TF currently has analysis nodes, but they are generic hidden/collapsible children rather than the normal line-reading layer.

### 3. Document provenance/context is part of reading

Upstream headings routinely expose:

- canonical/publication identity;
- CTH;
- editorial/source group, e.g. `[by HFR Basiscorpus]`, `[by HPM Mythen]`, `[adapted by TLHdig]`;
- editor/date where present.

For composites the page explicitly lists joined publications/fragments instead of pretending the lookup identifier is the complete scholarly identity.

### 4. Ambiguity remains visible

The web edition frequently renders several analyses for one word. It does not make a visually silent arbitrary choice. Any TF representation that selects only one analysis by default needs an authoritative source-selection feature; otherwise the ambiguity must remain visible/expandable.

### 5. Damage/editorial state belongs in the reading text

Brackets, restorations, erasure and Hittitological writing distinctions are visually part of the transliteration. The already-shipped sign-local renderer (#42) addresses this class of semantics and should remain the low-level typography layer.

## Upstream browse/search grammar

The live `corpus.php` page exposes:

- language filter: `Akk Hit Hur Luw Pal`;
- script mode: Transliteration / Transkription / Cuneiform;
- case-sensitive / case-insensitive matching;
- dating filter;
- findspot filter;
- CTH number;
- 0/1/2 lines of context before/after;
- line-oriented result view;
- text-pattern operators including character, word/text, line-break and paragraph-marker operators.

Representation lesson: context windows and line-oriented results are valuable. Implementation lesson: do **not** clone this bespoke query syntax in `app.py`; Text-Fabric already supplies a query engine. Where underlying features exist, provide TF examples/defaults rather than a second search language.

Two upstream filters currently cross a data-model boundary: generated TF feature reference has no `dating` or `findspot` feature in 0.4.0. App code cannot reproduce those filters honestly without a separate metadata source/model ticket.

## Current TF support matrix

| Upstream semantic | TF 0.4.0 support | Current TF display | Gap | Candidate |
|---|---|---|---|---|
| Canonical document heading | `document.docid`, `cth` | document label + CTH feature | partial | config/renderer header |
| Composite/join identity | `fragment` nodes, `joinstmt` nodes, `join_raw`, `join_resolved`, joined relations; duplicate identities retained | fragment/join nodes hidden | **major** | compact document header, never collapse ambiguous joins |
| Source/editorial project | `project` (`subcorpus` compatibility alias) | `subcorpus` listed as a document feature | partial | map codes to documented scholarly labels only if mapping is evidenced |
| Editor/date | `edit` nodes; `kind`, `editor`, `date`; `author` on author events | edit nodes hidden | **major** | document-header summary of relevant events |
| Surface/column/line hierarchy | `surface`, `column`, `line`; `surface`, `collabel`, `lnno` | line/column labels exist; surface hidden | partial | reading-oriented hierarchy/defaults |
| Line-oriented transliteration | sign slots + TF text formats; line nodes | available, but generic TF tree is primary in pretty mode | **major UX** | dedicated line-oriented pretty/read composition |
| Word-aligned morphology | word/analysis graph; `trans`, `nanalyses`, candidate analysis nodes | analyses hidden/collapsible | **largest UX gap** | interlinear word analysis layer |
| Multiple analyses | `nanalyses`, analysis nodes/edges | retained but visually peripheral | major | stack/expand all candidates; no arbitrary single-choice default |
| Source-selected analysis kind | `mrpsel_kind`: `analysis`, `none`, `unknown`, `DEL`, `AKK`, `HURR`, `HAT`, `SUM`, `LUW` | shown as a word feature | needs semantics study | may drive compact status badge, not analysis selection until proven |
| Annotation validation status | upstream has explicit pre-validated/not-validated UI | no proven token-level TF status feature found in core reference; generic `edit(kind/editor/date)` is insufficient evidence | **model/research gap** | separate modelling investigation; do not emulate colours yet |
| Sign-local typography/damage | `sgr`, `agr`, `det`, `num`, damage/editorial features | semantic renderer already shipped | largely covered | keep #42 layer |
| Language | sign-level `lang` now source-faithful; word/document context also available through graph | sign/document feature exposure | partial | subtle badge/filter/query examples; avoid visual noise |
| Cuneiform | line `cu`; sign `cu_sign` where aligned; dirty/alignment state including `cudirty` | cuneiform format exists | partial | optional mode with explicit unavailable/dirty fallback |
| Broken line/text state | source gap/layout structures survive in graph to varying degrees | layout hidden; not presented like upstream prose (`Zeile abgebrochen`, `Text bricht ab`) | needs corpus census | semantic structural marker if graph support is complete |
| Upstream authoritative page | safe `webLink()` integration | Python + browser TLHdig action | covered | retain |
| Dating filter | no generated `dating` feature | unavailable | **data gap** | separate metadata/model owner if desired |
| Findspot filter | no generated `findspot` feature | unavailable | **data gap** | separate metadata/model owner if desired |
| CTH search/filter | `cth` | document feature/queryable | covered in data | documentation/query preset rather than custom search UI |

## Important feature-level observations

### Analysis graph is sufficient for an interlinear prototype

TF 0.4.0 exposes at least:

- word `nanalyses`: number of candidate morphological analyses;
- word `mrpsel_kind`: source selection/status family (`analysis`, `none`, `unknown`, language/logographic kinds, `DEL`);
- analysis labels in current app already use `{index}. {lemma} "{gloss}" {morph}`;
- analysis `pos`, `stemclass`, `parse_ok` exist in the current app configuration.

Therefore the major interlinear gap is primarily **representation**, not absence of the candidate analyses themselves. A follow-up should still verify analysis ordering and whether any source-selected candidate is authoritatively identifiable before styling one as preferred.

### Editor/date support is real but hidden

Generated feature semantics confirm:

- `editor`: editor initials/name recorded on an event;
- `date`: event timestamp;
- `kind`: editorial event kind (`kor`, `kor2`, `uebern`, `annot`, ...);
- `author`: author on an author event.

So upstream-like document context can be derived from graph events. The plan must define which event kinds correspond to user-facing `ed. NAME (DATE)` instead of dumping all provenance events.

### Composite identity must use graph evidence, not string reconstruction

`join_raw` is the literal source join operator/text marker; fragment and join-statement nodes preserve source statements, including unresolved cases. The renderer should summarize these structures only when graph relations support them and retain explicit ambiguity. It must not reconstruct a scholarly composite merely from trailing `+` in `docid`.

### Cuneiform needs a trust boundary

`cu` is whole-line Unicode cuneiform and is explicitly not sign-aligned. `cu_sign` exists only where alignment succeeds; absence means unknown rather than “no sign”. `cudirty` records the source line dirty flag. A mode switch must never imply per-sign alignment where only line-level cuneiform exists.

## Representation principles selected by research

1. **Do not clone the PHP page.** Reuse its scholarly reading grammar inside TF.
2. **Line-first reading.** Preserve surface/column/line labels and explicit structural interruptions as the reading spine.
3. **Interlinear analysis as the high-value improvement.** In pretty/research reading, keep each word close to its gloss/morphology and expose all candidates compactly.
4. **Document context above the text.** Show CTH, project/source, relevant editor/date and composite/join context, plus the existing upstream action.
5. **Keep ambiguity honest.** Candidate analyses, duplicate manuscript identity and unresolved joins remain explicit.
6. **Layer rather than replace.** Existing sign-local Hittitological typography remains beneath the line/word representation.
7. **Optional cuneiform with trust signalling.** Use aligned signs where available and line-level fallback where appropriate; dirty/unknown state must remain evident.
8. **Use TF querying for search.** Add documentation/examples/defaults for language/CTH/context-style workflows instead of reproducing TLHdig search syntax.
9. **No fabricated metadata.** Dating/findspot and token validation status require underlying evidence/model support before TF UI parity.

## Likely decomposition

The research supports narrow follow-ups rather than reopening #42:

1. **Interlinear line/word reading representation** — app/config/renderer work; highest user value.
2. **Document scholarly header** — CTH/project/editor/date/composite context; separate from sign rendering.
3. **Browser/query recipes and sensible defaults** — language, CTH, line-context and script-mode workflows using generic TF facilities.
4. **Validation-status modelling research** — determine the exact source semantics behind upstream magenta/grey state and whether it survives the dataset.
5. **Dating/findspot metadata research** — determine whether these upstream catalogue fields can be obtained from an authoritative open HPM source and joined reproducibly; do not scrape them into app code.

## Research conclusion

The current TF app is semantically strong at the graph and sign-typography levels but still behaves too much like a generic object browser for close reading. The most important lesson from original TLHdig is not its styling; it is its **line-oriented interlinear reading model**. The next UI work should make that model native to TF pretty/browser reading while retaining generic TF graph inspection and query capabilities.

No production change should be made until the follow-up plan freezes exact hook boundaries, performance/accessibility expectations, and RED contracts.