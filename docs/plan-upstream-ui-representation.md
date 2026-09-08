# Plan: adapt upstream TLHdig representation semantics to Text-Fabric

Issue: #72
Research: `docs/research-upstream-ui-representation.md`

## Architecture decision

Do **not** reproduce the TLHdig PHP application. Preserve the existing architecture:

- Text-Fabric remains the generic local browser/query environment;
- upstream TLHdig remains the authoritative scholarly web edition;
- corpus semantics remain in the TF graph/converter;
- app hooks only compose already-released semantics for reading;
- generic TF feature/tree inspection remains available alongside any reading-oriented view.

The research selects a layered researcher-facing representation:

1. line-first transliteration as the reading spine;
2. optional/pretty interlinear word analyses directly under each word;
3. compact scholarly document context above the text;
4. existing sign-local Hittitological typography underneath those layers;
5. cuneiform only with explicit trust/fallback semantics;
6. TF query/documentation recipes instead of a cloned upstream search form.

## Independent research-review amendments

A skeptical pass challenged whether the upstream layout could overstate relationships that the TF graph does not preserve.

Findings:

- `analyses` is an explicit `word -> every candidate morphological analysis` edge, so word/candidate alignment is graph-backed.
- each analysis has `index`, preserving the source `mrpN` index space (including gaps), so candidate ordering can be deterministic without relying on node IDs.
- `nanalyses` gives the candidate count.
- `mrpsel_kind` preserves source selection/status families, but this plan does **not** treat it as sufficient evidence to visually crown one candidate authoritative. Source-selection semantics are complex and historically provisional; all candidates remain visible/expandable until a dedicated test proves a preferred-candidate contract.
- upstream magenta/grey annotation status still lacks a proven token-level TF feature mapping; generic edit events must not be substituted for it.

This prevents visual certainty stronger than the data model.

## Work decomposition

### Lane A — line-oriented interlinear reading

Create a narrow implementation ticket for a reading composition that makes line + word + analyses the useful pretty/browser representation.

Scope:

- preserve TF section navigation and line labels;
- render each word in source order;
- associate candidate analyses using the explicit `analyses` edge;
- order candidates by `analysis.index`, not node ID;
- show compact gloss + morphology; preserve empty/failed analyses honestly;
- all candidates visible or expandably available; no arbitrary winner;
- reuse existing sign-local classes/escaping rather than reconstructing transliteration;
- avoid expensive whole-document traversals per token.

Classification: **renderer hook + small CSS**, potentially a tiny config default. No schema change.

RED must cover:

- one ordinary line with several words;
- word with zero analyses;
- exactly one analysis;
- several analyses with non-contiguous indices;
- candidate ordering independent of node ID;
- parse-failed candidate remains explicit rather than disappearing;
- damage/Sumerogram styling still applies to the transliteration;
- hostile gloss/morph text is escaped;
- absent optional feature APIs fail gracefully;
- representative real `A.pretty()`/browser path;
- bounded feature lookups/traversal on a representative line.

### Lane B — scholarly document header

Create a separate implementation ticket for compact document context, independent of interlinear rendering.

Candidate content, only where graph-backed:

- document/publication identity;
- CTH;
- project/source code, converted to a human label only through a documented mapping;
- relevant editor/date events;
- fragment/join summary for composite texts;
- existing `TLHdig ↗` action.

Rules:

- use `fragment`/`joinstmt` relations rather than parsing trailing `+`;
- unresolved joins remain visibly unresolved/omitted, never guessed;
- duplicate `docid` identity remains separate from composite identity;
- choose user-facing edit-event kinds by researched semantics, not by dumping every `edit` node;
- no provenance-heavy optional module load.

Classification: **renderer/config**, no corpus mutation unless research exposes a missing semantic.

RED must cover ordinary vs composite documents, duplicate docid, unresolved join, editor/date present/absent, HTML escaping, and source-link coexistence.

### Lane C — browser/query recipes and mode guidance

Fold into existing #44 rather than create a competing browser-doc ticket.

Add tested examples for:

- language-constrained queries;
- CTH-constrained queries;
- line-oriented result/context workflows;
- transliteration vs cuneiform use and limitations;
- when `cu`, `cu_sign`, `cudirty`/alignment state make a representation trustworthy;
- direct selective `Fabric` usage when the full browser path is too heavy.

Do not implement TLHdig's `?`, `#`, `@`, `&`, `§`, paragraph-marker search syntax as a second query language.

Classification: **documentation/query examples + possibly interface defaults**.

### Lane D — annotation validation-status research

Create a research ticket, not UI implementation.

Question: what exactly drives upstream `pre-validated (magenta)` vs `not validated (grey)` at word/analysis level, and is the necessary source state present in the distributed TLHdig 0.3 XML/metadata?

The ticket must trace live HTML state back to source attributes/events, measure coverage, and determine whether a new core feature is justified. Until then the TF app must not imitate these colours/statuses.

Classification: **underlying corpus-model research**.

### Lane E — dating/findspot metadata research

Create a research ticket because these live upstream filters are not represented by generated TF 0.4.0 features.

Questions:

- are dating/findspot values present in another openly distributable HPM/TLHdig dataset or API;
- what stable manuscript identifier permits a reproducible join;
- how do duplicates/composites map;
- licensing/provenance;
- whether these belong in TLHdig-TF core, an optional metadata module, or only upstream links.

No scraping into app code.

Classification: **underlying data/integration research**.

## Explicitly not reproduced

- bespoke public TLHdig-TF web server;
- PHP search syntax;
- pixel/colour parity with upstream;
- upstream navigation/menu chrome;
- arbitrary preferred morphological analysis;
- dating/findspot values inferred from CTH or filenames;
- annotation validation inferred from editor/date events;
- cuneiform fabricated when `cu_sign`/line evidence is absent.

## Shared app-code coordination

Lanes A and B may both touch `app/app.py`. Research/RED can run independently, but production merges should be serialized or rebased so the final exact-head review sees:

- source-link adapter;
- sign-local renderer;
- interlinear composition;
- document header

as one coherent lifecycle across `__init__`/`reuse()`.

## Performance contract

The 3.4M-slot corpus makes per-render global scans unacceptable.

- document-level summaries may be cached per app/reuse;
- line rendering should traverse only the line's words/signs and their directly linked analyses;
- no repeated corpus-wide duplicate/join/event census per rendered token;
- RED/performance tests should instrument traversal counts on a representative fixture rather than rely only on wall-clock CI timing.

## Accessibility / ambiguity

- meaning must not rely on colour alone;
- candidate analyses need textual/structural distinction;
- damage and writing-system typography remains readable without CSS;
- dirty/unavailable cuneiform needs textual fallback/indicator where exposed;
- expandable analysis UI must retain keyboard/browser accessibility through TF-supported markup rather than bespoke JavaScript if possible.

## Integration gate

After any selected implementation tickets land, extend #45 browser/app regression coverage with representative real-corpus cases:

- ordinary HFR line;
- multi-analysis word;
- composite document;
- editor/date document;
- broken-column/line example;
- cuneiform-supported and dirty/unavailable examples;
- upstream action still present.

## Completion of #72

#72 itself remains research/plan only. It is complete when:

- this plan is independently challenged;
- implementation/model tickets are created with non-overlapping ownership;
- #44/#45/#46 are cross-linked for browser tests/docs;
- no production app change is hidden in the research PR.