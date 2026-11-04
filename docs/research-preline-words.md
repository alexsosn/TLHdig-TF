# Research: readable words before the first line boundary

This document freezes the production-corpus evidence for the pre-line word fidelity gap.

## Corpus-wide population

The pinned repaired production corpus contains:

- **23,884** production-eligible source documents;
- **22** documents with top-level `<w>` elements before their first `<lb>`;
- **36** such pre-line words;
- **15** pre-line words with readable signs;
- **21** marker/layout/note-only pre-line words;
- **22** readable pre-line signs in total;
- **3,365,151** readable top-level source signs when these signs are included;
- **3,365,129** currently represented non-anchor TF 0.4.0 signs;
- therefore an exact **22-sign source-minus-TF deficit**;
- **21,215** technical anchor slots, which are a separate population and do not explain the deficit;
- **20** pre-line words carrying damage markers;
- **3** carrying notes;
- **0** affected production documents without any `<lb>` later in the document.

The 36-word / 22-sign observation reconciles exactly with the complete source/graph sign population. There is no second hidden population needed to explain the deficit.

## Source structure

Every one of the 36 words is a direct child of `<text>`:

`/AOxml/body/div1/text/w[...]`

Their common structural ancestors are `text → div1 → body → AOxml`. None has a source `<lb>`, column, paragraph, or other narrower structural owner before it. The first real `<lb>` follows later in every affected document.

The content is mixed rather than one uniform authoring artefact:

- genuinely readable transliteration, including damaged readings (`…`, `x`, ordinary signs, numbers, Hattic material);
- damage-open/damage-close words;
- whitespace/layout-only words;
- note-only words;
- combinations where an opening/closing damage marker and readable material span the transition toward the first real line.

Representative readable cases include `KBo 26.65` (five signs in one word), `KBo 52.16+` (three signs), `KBo 37.120` (Hattic signs), and individual damaged or number readings in several prayer/mythological texts. This is therefore not safe to classify wholesale as headings or apparatus leakage.

The full machine inventory is reproducible through `programs/research_preline_words_52.py`; it records source path, XML path, source byte span, readable symbols, markers, note count, and the first subsequent line metadata.

## Current loss mechanism

`_State.word()` currently returns early when `self.line is None`. It forwards token markers and notes into their trackers, but creates no `word` node and no readable sign slots. That behavior accounts exactly for the 22 missing signs.

The section-model probe tests the relevant Text-Fabric navigation model with a document-only slot. The graph ancestry is source-faithful: the pre-line sign has only its `document` above it, while a normal later sign has `line`, `column`, and `document`. With the configured three-level section model, `T.sectionFromNode()` presents the document-only case as `(document, None, None)`. Those `None` placeholders are API presentation; they are **not graph line ownership**.

Therefore preserving a document-only sign does not require fabricating an `<lb>` or a line number. Tests must assert graph ancestry, not incorrectly require a one-element section tuple.

## State-transition implications

Simply removing the current `if self.line is None: ... return` guard is unsafe by itself. The ordinary word path sets `line_first` when it creates the first slot. For source-faithful pre-line material:

- readable signs may be document-owned without line/column/paragraph ownership;
- `line_first` must remain `None` outside an actual line;
- when the first real `<lb>` opens, its line-local state must start fresh;
- open damage/note state from the source may legitimately carry across the boundary and must not be discarded or duplicated;
- pre-line signs must not be confused with technical anchor slots.

The existing `start_line()` resets `line_first` on a real line boundary. The minimal implementation is therefore to let readable pre-line words use the ordinary word/sign path while making `line_first` assignment conditional on `self.line is not None`.

## Structure-gate cross-check

Implementation review found that the current independent structure gate carries `KNOWN_WORD_DEFICIT = 15` and describes those missing top-level words as a nested-word defect. That explanation cannot be correct for this count: `structure.count_document()` explicitly counts only `<w>` elements with **no `<w>` ancestor**, so nested source words are excluded before `KNOWN_WORD_DEFICIT` is calculated.

The remaining allowed top-level-word deficit is exactly **15**, the same as the measured population of readable pre-line words dropped by the current early return. This is strong independent corroboration that #52 owns that allowance. The final rebuilt artifact should therefore be required to reduce the top-level `word + layout` deficit to zero; if it does, the stale `KNOWN_WORD_DEFICIT=15` allowance and its nested-word explanation must be removed rather than retained as historical baggage.

This does not resolve the separate nested-morphology problem in #109: nested `<w>` elements are intentionally outside this structure count and remain a different modelling question.

## Current-main refresh

The original research branch predated the one-current-artifact simplification and carried temporary workflow/certification files that no longer exist on `main`. Those files are not evidence for this correctness issue and are intentionally not ported.

The current supported generated path is `tf/0.4.0`; historical generated siblings have been pruned. The research inventory script now targets the repository's canonical `TF_VERSION` rather than a removed `tf/0.3.0` baseline. The section-model probe likewise uses the measured current Text-Fabric behavior `(document, None, None)`.

## Research gate result

**PASS.**

The fidelity gap is exact and fully classified at corpus scale: 36 source words / 22 readable signs, all directly under `text`, all in documents that later acquire a real line. Text-Fabric supports the selected document-only graph model without requiring a synthetic line. The independent top-level structure deficit provides a second measured invariant: the final #52 rebuild should remove the existing 15-word allowance completely.
