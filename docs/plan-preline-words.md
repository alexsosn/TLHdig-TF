# Plan: preserve pre-line source words without inventing lines

This plan follows `docs/research-preline-words.md`. Production code must not change
until the RED gate below is committed and observed failing for the intended reasons.

## Representation decision

Preserve pre-line source content exactly where the source places it: beneath the
`document`, with **no fabricated `line`, `column`, `surface`, `paragraph`, or citation
identity**.

For a readable pre-line `<w>`:

- create the ordinary `word` node;
- create its ordinary source sign slots in source order;
- allow the word and its `analysis` nodes to cover those slots normally;
- keep those slots in the document extent;
- do not add them to any line extent or line cuneiform alignment;
- preserve ordinary sign features/provenance/language semantics supported without a
  line;
- preserve marker/note flow in source order.

For a marker/layout/note-only pre-line `<w>`:

- do not invent a linguistic sign merely to anchor it;
- keep the existing layout/marker/note model;
- defer anchoring only when no real source/technical slot yet exists, as current
  `pending_layouts` / `pending_notes` semantics already require.

Technical anchors remain marked `anchor=1`; newly preserved readable signs are source
signs and must never acquire that marker.

## Line-local state rule

Refactor word-slot creation only as much as necessary to make line ownership optional.
The critical invariant is:

> `line_first` is the first slot of an actual open line, never the first slot merely
> because a document now has a source sign.

When `self.line is None`:

- create readable signs/word nodes but do not call `_extend_line()`;
- do not add to `lines_with_slots`;
- do not assign `line_first`;
- marker tracking receives the real slot and offsets but a `None` line-first boundary;
- notes attach to the real pre-line slot when one exists, otherwise remain pending.

`start_line()` then resets/starts line-local state exactly as today. This prevents the
first real line from inheriting invented structural extent while still allowing bracket
state that is genuinely open in the source to continue.

## Sign ordering and section semantics

The 22 source signs must be inserted at their true position before the first real-line
sign. Consequently the immutable artifact will have 22 additional **source** sign slots;
all later source signs shift by slot number, but their source order must be identical.
Release validation must compare source order/feature semantics, not require stable node
numbers across versions.

For a pre-line sign:

- `L.u(sign, otype="document")` resolves to its document;
- `L.u(sign, otype="line")` is empty;
- `T.sectionFromNode(sign)` may expose configured missing section levels as `None`; this
  is expected and must not be interpreted as a synthetic line.

No new section key or fallback line label is introduced.

## RED gate

Before production changes, commit failing fixtures for at least:

1. a readable word before the first `<lb>` creates a word/sign and no line ownership;
2. marker/layout-only pre-line word creates no linguistic sign;
3. pre-line damage + note state followed by a normal line preserves both without
   damaging/duplicating the wrong sign;
4. a synthetic document with no `<lb>` still preserves readable pre-line content under
   the document, without creating a line;
5. source sign ordering across pre-line → first-real-line transition;
6. the first real line's extent begins at its own first sign, never at a pre-line sign;
7. pre-line source signs are not technical anchors;
8. section/navigation assertions distinguish graph ancestry from `None` placeholders.

Add a corpus-conservation test/checker target for the measured production population:

- 36 pre-line words found;
- 15 readable pre-line words;
- 22 readable pre-line signs;
- all 22 represented exactly once after implementation;
- source readable-sign population becomes 3,365,151 non-anchor graph signs, barring a
  separately reviewed concurrent corpus change.

## GREEN implementation

Make the smallest `_State.word()` / slot-state change that turns the RED fixtures green.
Do not create a special `preline` node type or a fake line. Reuse ordinary word/sign,
analysis, marker, note and provenance machinery wherever line-independent.

Explicitly audit sign-level features whose current implementation depends on line state,
including `lang`, cuneiform alignment and damage-range calculations. If a feature cannot
be source-faithfully derived without a line, leave it absent and document that decision
rather than inferring from the later line.

## Full test / release gate

Because source slots and node numbering change, this requires a **new immutable TF
artifact**. Do not reserve a version while the header-provenance lane owns TF 0.5.0.
Allocate the next version only after the current artifact-producing lane merges.

Required full gates include:

- unit/adversarial suite;
- exact pre-line source-to-graph conservation;
- sign round-trip and sign-language conservation with the newly represented population;
- marker/damage and note conservation;
- source structure / Contract A / Contract B;
- section addressing and app load;
- manuscript graph conservation;
- census;
- predecessor-delta contract;
- historical-artifact immutability;
- canonical release certification on the exact quiet protected-tree head.

## Independent adversarial review

A logically separate reviewer must challenge at minimum:

- any invented line/citation ownership;
- pre-line signs accidentally extending the first real line;
- duplicate/reordered signs at the transition;
- `line_first` being set outside a real line;
- damage markers covering the wrong pre-line/first-line sign;
- pending notes/layouts being flushed twice or to the wrong slot;
- source signs mislabeled as technical anchors;
- analyses/word extents missing their pre-line slots;
- language or cuneiform values inferred from the later line without source authority;
- corpus counts deviating from the measured 36-word / 22-sign population;
- node-number churn being mistaken for semantic regression;
- final artifact/certification identity and historical immutability.

Any blocking review finding restarts the implementation/review sub-loop before merge.
