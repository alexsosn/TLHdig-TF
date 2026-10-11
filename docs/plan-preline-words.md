# Plan: preserve pre-line source words without inventing lines

Issue: #52. Research basis: `docs/research-preline-words.md`.

Status: current-main plan frozen before implementation. The branch carries RED tests/research helpers only; production code must not change until the refreshed hosted RED is observed.

## Representation decision

Preserve pre-line source content exactly where the source places it: beneath the `document`, with **no fabricated `line`, `column`, `surface`, `paragraph`, or citation identity**.

For a readable pre-line `<w>`:

- create the ordinary `word` node;
- create its ordinary source sign slots in source order;
- allow the word and its `analysis` nodes to cover those slots normally;
- keep those slots in the document extent;
- do not add them to any line extent or line cuneiform alignment;
- preserve ordinary sign features/provenance/language semantics supported without a line;
- preserve marker/note flow in source order.

For a marker/layout/note-only pre-line `<w>`:

- do not invent a linguistic sign merely to anchor it;
- keep the existing layout/marker/note model;
- defer anchoring only when no real source/technical slot yet exists, as current pending layout/note semantics require.

Technical anchors remain marked `anchor=1`; newly preserved readable signs are source signs and must never acquire that marker.

## Line-local state rule

Refactor word-slot creation only as much as necessary to make line ownership optional. The critical invariant is:

> `line_first` is the first slot of an actual open line, never the first slot merely because a document now has a source sign.

When `self.line is None`:

- create readable signs/word nodes but do not extend a line;
- do not add to `lines_with_slots`;
- do not assign `line_first`;
- marker tracking receives the real slot/offset while retaining absence of a line boundary;
- notes attach to the real pre-line slot when one exists, otherwise remain pending.

`start_line()` then starts/resets line-local state exactly at the real `<lb>`. This prevents the first real line from inheriting invented structural extent while still allowing genuinely open source bracket state to continue.

## Sign ordering and section semantics

The 22 source signs must be inserted at their true position before the first real-line sign. Consequently the current pre-alpha artifact will have 22 additional **source** sign slots and later node numbers may shift; source order/feature semantics, not numeric node stability, are the compatibility contract.

For a pre-line sign:

- `L.u(sign, otype="document")` resolves to its document;
- `L.u(sign, otype="line")` is empty;
- with the current three-level section model, `T.sectionFromNode(sign)` may be `(docid, None, None)`; these placeholders do not imply synthetic column/line ownership.

No new section key or fallback line label is introduced.

## RED gate

Before production changes, preserve failing fixtures for at least:

1. a readable word before the first `<lb>` creates a word/sign and no line ownership;
2. marker/layout-only pre-line word creates no linguistic sign;
3. pre-line damage + note state followed by a normal line preserves both without damaging/duplicating the wrong sign;
4. a synthetic document with no `<lb>` still preserves readable pre-line content under the document, without creating a line;
5. source sign ordering across pre-line → first-real-line transition;
6. the first real line's extent begins at its own first sign, never at a pre-line sign;
7. pre-line source signs are not technical anchors;
8. section/navigation assertions distinguish graph ancestry from `None` placeholders;
9. an independent corpus-conservation checker is required and freezes the measured population rather than learning it from converter output.

Hosted RED on the refreshed branch must show only these absent semantics/checker requirements failing, with the rest of the current unit suite green.

## Production conservation target

The implementation/checker must account for the measured production population:

- 36 pre-line words found;
- 15 readable pre-line words;
- 22 readable pre-line signs;
- all 22 represented exactly once after implementation;
- source readable-sign population reconciles to 3,365,151 non-anchor graph signs, unless a separately reviewed concurrent corpus change deliberately changes that baseline.

The checker should independently inspect source and graph semantics rather than call converter helpers whose bug it is meant to detect.

## Minimal implementation

Make the smallest `_State.word()` / slot-state change that turns the RED fixtures green. Do not create a special `preline` node type or fake line. Reuse ordinary word/sign, analysis, marker, note and provenance machinery wherever line-independent.

Explicitly audit sign-level features whose current implementation depends on line state, including language, cuneiform alignment and damage-range calculations. If a feature cannot be source-faithfully derived without a line, leave it absent and document that decision rather than inferring it from the later line.

Add the independent `programs/check_preline_words.py` gate and include it in complete current-artifact validation only after its source/graph independence has been reviewed.

## Current-artifact build gate

This repository now has one replaceable current pre-alpha artifact. **Do not allocate a new TF version and do not resurrect predecessor/certification machinery.**

After implementation:

1. rebuild `tf/<TF_VERSION>` / `tf-provenance/<TF_VERSION>` cleanly using the current build path;
2. run the full unit/adversarial suite;
3. run exact pre-line source-to-graph conservation;
4. require sign round-trip, sign-language, marker/damage/note, structure/Contract A, section/app, manuscript, alignment/signref and census gates as applicable;
5. run `validate_current.py` and regenerate the current `BUILD-MANIFEST.json` from the validated output;
6. require ordinary exact-final-head CI including `check_build_manifest.py`.

Because adding 22 real source slots shifts later node numbers, output-byte/hash changes are expected. Semantic gates must distinguish intended ordering shifts from unrelated data regressions.

## Logically independent adversarial review

On the exact final production/artifact head challenge at minimum:

- invented line/citation ownership;
- pre-line signs accidentally extending the first real line;
- duplicate/reordered signs at the transition;
- `line_first` being set outside a real line;
- damage markers covering the wrong pre-line/first-line sign;
- pending notes/layouts being flushed twice or to the wrong slot;
- source signs mislabeled as technical anchors;
- analyses/word extents missing their pre-line slots;
- language or cuneiform values inferred from a later line without source authority;
- corpus counts deviating from the measured 36-word / 22-sign population;
- node-number churn being mistaken for semantic regression;
- manifest or committed generated bytes describing a different build than the reviewed converter.

Any blocker gets a focused regression before correction, full GREEN, artifact rebuild/validation as needed, and a fresh review.

## Non-goals

- fake lines or citation labels;
- stable raw TF node numbers across this correctness fix;
- historical generated snapshots;
- recursive release certification;
- unrelated source repair or upstream editorial decisions.