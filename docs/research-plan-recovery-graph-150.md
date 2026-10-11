# #150 — Research and integration plan: reviewed source recovery to Text-Fabric

Status: **research/plan**, stacked on draft PR #149. This is not a new release or a production recovery implementation.

## Evidence actually inspected

- `programs/tlhdig/convert.py::director` reads the immutable file, applies the **entire** `patches.yaml` entry through `repair.apply()`, scans it with `source.scan()` (Expat), parses an lxml tree, and dispatches to `_document()`. The 47 word-state crossing patches still manufacture closing `</w>` tags in this production path.
- `_document()` obtains header/doc identity, edit events, `AO:Manuscripts`, line events, word attributes and child order from that lxml tree. It aligns tree words to Expat `source.Span` objects by ordinal, omitting nested words because the enclosing word already contains their bytes. `_State.start_line()` consumes lxml `lb` attributes; `_State.word()` consumes an lxml word element, `source.inner_bytes(data, sp)`, `signs.tokenise_word()`, `morph.analyses(node.attrib)` and `morph.parse_selection()`; `_State._span()` writes `src_span` through the old repair `OffsetMap`. **These dependencies cannot be satisfied by a list of unbound `RecoveryEvent` objects alone.**
- The production `structure.count_corpus()`, `check_signs.py`, `check_morph.py`, `check_markers.py`, `check_tags.py`, `check_sign_language.py` and `check_preline_words.py` independently apply all historical patches and parse a different view from `prepared_source.prepare()` / `recovery.recover_word_state()`. In particular, the sign validator's `srcxml+after` conservation comparison currently uses repaired, not immutable, word content. `check_contract_a.py` instead inspects raw bytes and uses strict Expat; it is a distinct raw-source contract, not a recovered graph check.
- `source.Span` has `outer_start/end`, `inner_start/end`, `attrs`, `depth`, and `self_closing`, all indexed into its input byte array. Constructing a recovered span with an end coordinate in a different byte space would silently corrupt tokenization and `src_span`.
- PR #149 already pins exactly 47 reviewed word-stack cases and a source-coordinate `WordRecoveryView`. All its unit, sign, morphology, marker, app, provenance and alignment checks passed on commit `fdeecee0` (CI 38047355936); the only CI failure was the pre-existing current-build manifest identity mismatch. The event view is still not used by TF conversion.
- Corpus examples: `CTH 209_XML_TLH/KBo 12.55.xml` has **two lexical attribute patches and one end-of-text word-close patch**; its one terminal recovered word is the small pilot. `CTH 394_XML_BESRIT/Bo 3353.xml` has five missing closes, nine nested word starts and no intervening line start in the measured bad span: the next word is not mechanically proven to be a sibling. `CTH 479_XML_BESRIT/KBo 41.49+.xml` has 14 open words at text end and a catastrophic line-swallowing baseline. `CTH 570_XML_HDivT/KBo 58.79+.xml` has 13 lexical repairs before the single crossing repair, including a manufactured tag ending; original word opening at byte 65195 survives. `CTH 544_XML_HDivT/KUB 34.22+.xml` has malformed quoted `<gap>` content, requiring conservative raw source opening-candidate scanning.

## Decision: a shared, typed *logical document* is the conversion input

Do **not** use `lxml.XMLParser(recover=True)` as the truth source: its chosen implicit nesting boundaries are not a reviewed disposition, and it cannot supply immutable byte ranges. Do **not** serialize a corrected XML byte stream or treat a generated `</w>` as original `srcxml`.

The eventual shared input contract must distinguish:

1. `immutable_source`: source SHA and original bytes, retained unchanged;
2. `mechanical_source`: the reviewed, SHA-verified lexical-only repair stream and ordered byte trace;
3. `logical_text_events`: source-ordered line/word/layout/note/marker/paragraph/colon events, with stable **original** source anchors, optional mechanical token ranges, and explicit synthetic boundary reasons;
4. `word_payload`: a verified attribute mapping, original evidence slice(s), a separately labelled mechanical lexical body where necessary, and deterministic sign/morph input; ambiguous boundaries are not given fictitious `source.Span` end tags;
5. `recovery_diagnostics`: kind, trigger source offset, source SHA, confidence/ambiguity, and *measured* omissions only once the graph exists.

The converter should process the typed events through the existing `_State.start_line()`, `_State.word()`, marker and morphology logic rather than reimplementing sign/morph behavior. A small adapter can expose an element-like `.get()/attrib` for reviewed attributes, but must **not** derive word boundaries from an unverified nested XML tree. The header/manuscript/edit logic needs an explicit source-backed projection independent of a strict full-document tree. Before implementation, make that projection's coverage testable (docID, lang, edit ordering, manuscript join features).

The independent validators must use this same prepared/logical source contract for reviewed files, while maintaining independent algorithms for source counting versus actual TF output. Sharing input bytes does not justify sharing the code that computes expected and observed graph counts.

## Sequenced research → RED → implementation gates

### A. Terminal word vertical slice (no inference beyond `</text>`)

1. Test a `KBo 12.55` terminal word payload with SHA, source opening position, start-tag attributes, inner range, terminal `</text>` trigger and original/mechanical byte identity. Verify `<gap>` / editorial marker bytes, `signs.tokenise_word` raw and filtered round-trip, and `morph.analyses` / selection parity against the existing fully repaired strict-tree baseline. For the closing marker, the word has an **implicit logical end**, not a literal source `</w>`.
2. Negative cases: a valid nested `<w>` must not be split or treated as a defect; Bo 3353 multi-open must not be coerced into terminal-single-word success; unknown source hash, unanchored opening, changed trigger or source-patch drift must fail closed.
3. Construct a tiny TF subset using the same `_State` word/sign/morph routines and prove one original terminal word becomes one word-or-layout graph node with the same sign sequence and analysis ordering. Check the TF word source identity against immutable opening and logical end separately (don't conflate with strict source span).
4. Then integrate this **explicitly scoped** recovered text payload into the converter; no extra files or generic parser until all gates pass.

### B. Multiword/line recovery

1. Inventory the locally observed valid nested-word shapes among the 47 reviewed files. An open stack at `</text>` is evidence of structural failure, **not** proof that each earlier `<w>` was a sibling. Delimiters with ambiguous ownership remain unresolved.
2. RED fixture for Bo 3353 nested-word-only and KBo 41.49+ swallowed lines; assert every candidate original opening, order, line identity, morphology, notes and marker endpoints are retained. Show that the inferred segmentation does not swallow independent descendants.
3. Only after tests pass, reuse the typed input for actual TF conversion and independent validators; produce source-to-graph counts by `(src_file, immutable opening offset)` rather than corpus-wide aggregate counts.

### C. Acceptance before deprecating historical rewrites

- For each recovered file: exact original line starts == graph line identities; every source top-level word becomes a word/layout or is covered by a reviewed local omission; sign `srcxml+after` round-trip against **correctly labeled original or lexical-repaired evidence**; original-order and morphology/selection equivalence; markers/annotations retained or explicitly accounted for.
- Strictly parseable unaffected files must stay on the existing implementation until parity is proven; previously valid nested-word shapes must not be altered.
- Actual graph-level event `omitted_bytes` and `omitted_semantic_annotation` remain **unknown** until the graph-based comparison measures them. A constant zero is prohibited.
- Run source identity, policy drift, Contract A, structure, sign, marker, morphology, cuneiform, app and provenance gates on the one freshly built current pre-alpha artifact. Only then update its identity manifest; do not create old artifact versions or certification infrastructure.
- Each finalized PR requires a separate, skeptical review of code plus actual corpus and TF output. No merge while boundary ambiguity or converter/validator divergence persists.

## Out of scope of the first PR

Do not patch original upstream AOxml; do not claim that the source-opening audit is a full TF conservation proof; do not apply a generic sibling-at-next-`w` rule; do not touch wrapper recovery (19 separate dispositions), `KBo 38.169` exclusion, or #13 balanced-but-lossy word structures in the first terminal-word slice.


## Research addendum — two source-grounded singleton expansion candidates (2026-10-10)

The completed [CI #38060446252](https://github.com/alexsosn/TLHdig-TF/actions/runs/38060446252) passed every substantive gate (including the complete `KBo 12.55` raw-source TF word/line/marker census); only the known stale generated-build identity check failed. Do not restamp that artifact.

A read-only comparison of the exact repository's immutable AOxml and SHA-reviewed `source_recovery_patch_policy.json` identifies **two** additional cases with no mechanical lexical edits, one historical structurally inserted end-of-text close, and a single lexical unmatched word opening without subsequent literal `<w>` or `<lb>`:

| File | Original word openings / closes | Original `<lb>` openings | Literal `<del_fin/>` markers | Terminal source evidence |
| --- | ---: | ---: | ---: | --- |
| `CTH 448_XML_BESRIT/KBo 10.36.xml` | 160 / 159 | 59 | 31 | `<w mrp0sel="DEL"><del_fin/>x<gap c="Rs. IV bricht ab"/> \n` |
| `CTH 820_XML_TLH/KUB 48.15.xml` | 37 / 36 | 17 | 21 | `<w mrp0sel="DEL"><del_fin/>x-<laes_in/><gap c="…"/> … <gap t="line" c="Vs. bricht ab"/> \n` |

These are **candidates**, not proven repaired graphs. `KBo 10.36` has an orphan source `<del_fin/>`; `KUB 48.15` also has a still-open `<laes_in/>` and a line-type `<gap>` which can land on an empty token and expose a provenance loss when filtered. Tests must **fail closed** rather than silently drop those tags or postulate a new tablet line.

Next same-ticket research/TDD gate: parameterized build via existing `convert.build` complete-document pilot, source opening audit, raw counts vs actual TF word/layout + line + `del` close clusters, full-byte reconstruction of terminal sign slots, selected morphology parity, complete graph-type parity against the legacy strict-tree baseline, then independent adversarial review of any new allowed file. Do not enable `IBoT 3.141` or `KUB 60.14` yet: their terminal `<w>` contains only a gap/note and has **no sign-bearing token**, requiring a separately justified layout and note-ownership graph contract. Do not generalize to any of the 25 single-inserted-close files whose original source contains later words/lines within the still-open word.

This incremental opt-in pilot **still** parses the *surrounding document* using the full historical repair stream, not a source-derived logical tree; it must not be mistaken for the full #150 recovery integration.


## Research → plan: first-class source-backed gap annotations in a recovered tail

Adversarial [review #5479574136](https://github.com/alexsosn/TLHdig-TF/pull/152#pullrequestreview-5479574136) exposes a concrete semantic mismatch: `KUB 48.15`'s *two original*, self-closing `<gap>` elements are now faithfully present in the terminal sign's `after` string, but are not queryable as TF annotations. Neither tag is a real `<lb>`; inventing new line slots would misstate the text.

**Source witness:** immutable original `CTH 820_XML_TLH/KUB 48.15.xml`, verified by the SHA-reviewed `PreparedSource`, has a terminal `<w mrp0sel="DEL">` containing one real sign `x-`, an orphan `<laes_in/>`, then `<gap c="ma-aḫ&amp;lt;..."/>` and `<gap t="line" c="Vs. bricht ab"/>` with intervening XML whitespace. The `laes_fin`-like strings in `c` are **escaped attribute content**, not live bracket events. Review the raw bytes and use a quote-aware token scanner: regexp matching on `<gap.*?>` alone would break on quoted `>` and permit false source offsets. Both tags have a real `/>` and exact source-byte boundaries; the **word** has no real `</w>`.

**Design choice:** keep the existing source-verified trailing-byte transfer to the last actual sign, then additionally create two `gap` nodes anchored to that same slot, with `gapOf` edges to the recovered word. Record `gap_start` and `gap_end` *absolute immutable-source byte offsets* (half-open literal markup ranges), `gap_c` and `gap_t` decoded from the original literal tag only, and `gap_anchor_offset` as an intra-sign **character position**. These are annotations, never slots; do not fake `src_span` for the structurally unclosed parent word. The original `<laes_in/>` continues to be a proper orphan-open `cluster`; never count escaped text in `gap@c` as another cluster. Share this model between graph preview and full-doc pilot through the recovered `_State.word` path, not source-specific duplicated output code.

**TDD gates (RED before implementation):**
1. On the real complete-document `KUB 48.15` preview with recovery opt-in, assert exactly two `gap` nodes; each must have the exact original source opening/end offsets and decoded `@c/@t`, must be linked through `gapOf` and anchor to the original terminal sign only. Original 37 word openings, 17 actual `<lb>`, 21 `<del_fin/>`, and orphan `<laes_in/>` still hold, while sign `srcxml+after` reconstructs the **entire immutable terminal word body**.
2. Normal conversion and all other pilot files retain their prior nodes and semantics. The only permitted inventory change in the `KUB 48.15` pilot is two annotation `gap` nodes and their features/edges, never extra sign/word/line nodes. Tests must reject arbitrary note tags, nonliteral/fabricated gap offsets, and drifted original source.
3. Dedicated feature documentation must distinguish source-byte boundaries from `src_span`, which is not literal for an unclosed `<w>`.
4. CI unit/adversarial shard, corpus-wide independent sign/marker/morph/provenance gates and a fresh logically independent review of the exact tested implementation.

**Remaining scope:** this adds queryable gap annotations only for the **one reviewed recovered tail**; it does not imply coverage of all ordinary in-word gaps, zero-sign terminal words, multiple orphan source words, or general replacement of historical repaired-tree parsing. Avoid expanding a hardcoded exception registry beyond evidence and an explicit typed recovery contract.


## First bounded before-line resynchronization: UBT 70 (2026-10-10)

**Research:** CTH 832_XML_TLH/UBT 70.xml has five literal lb starts and five literal w starts. Line 4 starts a word with a malformed lexical trans opener (the source-reviewed policy marks exactly two byte-local mechanical repairs) and the original body containing del_fin, x-mu, and gap c="RASUR". **No literal closing w occurs before** the source lb of line 5. Line 5 then has an independently literal w trans="%" containing x and a real closing w. The final gap t="line" lies outside that word. The third patch inserts a single closing w only at the end of text; it is a structural reparsing workaround, **not** a supported word extent. In the repaired tree, line-5's word appears nested in line 4. Legacy _document() skips nested w descendants and nested w spans, excluding that valid final word.

**Decision:** first add a typed, SHA-verified word-before-real-line payload from the source event kind implicit_word_close_before_line; its body ends at the original literal lb byte offset. Lexical attributes come from only the mechanically corrected opener; original and mechanical body bytes must match exactly. The gap on line 4 becomes a typed source-backed annotation on its last real sign. On the UBT 70 opt-in path alone, emit all five original word openings in source order, allowing the final word despite its historically nested lxml node, and verify each original opening. No unconditional next-word/line auto-closure; all other documents retain their existing genuine nested-word behavior.

**TDD RED:** prove event kind and trigger, literal source boundary and mechanical opener, exact body bytes; build whole TF document with five actual word and five actual line nodes; one word each on lines 4 and 5; no fabricated source span for line 4; literal source span for line 5; word sign/morph/selection and gap provenance; six literal del_fin boundaries; and no invented sixth line for the terminal line-type gap. Unreviewed sources and valid nested-word fixtures must fail closed or remain unchanged. Opt-in only; leave generated artifacts and manifest untouched.

**Caveat:** this bridge still uses the legacy repaired lxml tree for surrounding document/header. The next structural milestone is source-event projection plus per-opening graph provenance and independent validator parity.


## Research-plan-TDD: literal outside-word gap on UBT 70 line 5 (2026-10-10)

**Immutable source observation:** CTH 832_XML_TLH/UBT 70.xml (reviewed SHA: 2ba14c6297057016dd789a3124233d27814ac1149ba102a044fe6f456bb8f9b6) has five actual lb openings and five actual w openings. On the fifth line, an independently literal w opens and closes around del_fin + x. After that literal closing w, but before literal closing text, appears exactly one self-closing gap whose c is "Text bricht ab" and whose t is "line". Thus there are **two** literal gap tags in this original document: the other, gap c="RASUR", is inside the recovered fourth word. The historical synthetic closing tag at text end makes the fifth word and trailing gap *look* nested under the fourth word in the legacy repaired tree. That inferred parenthood is false for source-level ownership.

**Plan:** build a small verified source-event projection of gap nodes **outside logical words** from recovery.scan_markup(prepared.mechanical_bytes, mechanical_patch_trace...). Reconstruct the word stack and apply only the SHA-reviewed implicit close at the literal fifth lb. Require the following independent literal word to close before the gap and the gap to lie after it, while still inside the source text and under the real fifth lb. Parse the standalone original gap tag with a strict, non-network XML parser; preserve byte-exact absolute original coordinates and decoded @c/@t; record literal fifth-line opening offset. Distinguish this typed *line-scoped* event from in-word gap events. Never use repaired lxml ancestry as the provenance/ownership authority, and do not generalize to unrelated corpus sources merely because they contain a gap.

**TF:** emit one additional gap node on the already-existing last real sign of that source line (NO new slot/word/line), features gap_start/end, gap_c/t, gap_anchor_offset, gap_scope="line", plus unvalued gapLine edge to the actual line node. In-word recovered gaps retain their gapOf word edge, with gap_scope="word" and no gapLine edge. Demand exact source token start/end and original literal attributes; require no gapOf edge for the source-outside-word node. Intra-sign offset at the end of the final line sign is a point attachment, not a claim the tag was part of that sign's srcxml. The literal line @t value "line" does not authorize an extra lb. No old artifact or manifest mutation.

**RED gate:** original source exactly two gap tags; line-4 gap has word scope on its real final sign, line-5 outside-word gap has line scope and its original source end position. Both have real source byte offsets and decoded exact attributes. Five original line nodes, five word nodes, recovered fourth-word morphology, fifth-word literal src_span, original damage marker counts and sign bytes remain unchanged. Adversarial checks: changed signed source, gap inside another word, an unclosed additional word, fake/unknown line opener, and an unrelated non-before-line file must NOT be interpreted as the same line-scoped event.

**Acceptance/review:** hosted RED first, minimal source-event + converter changes, loaded TF graph plus existing corpus-wide gates, exact-head skeptical independent review. Even a passed pilot does NOT prove complete independent corpus source parsing; main #150 remains open pending source-to-graph identity parity, shared validators and genuine artifact rebuild.


## Source opening-identity conservation on all reviewed TF graphs (2026-10-10)

**Research:** The four SHA-reviewed complete-document word-recovery pilots preserve aggregate source `<w>` and `<lb>` counts, yet equal totals do not exclude a source opening silently omitted from the TF graph and replaced by a duplicate/fabricated one. `recovery.audit_opening_tags()` currently compares literal source starts against the *scanner*'s tokens before conversion, not the emitted TF `word`/`layout`/`line` nodes. The converter pairs the historical Expat `w_spans` and lxml words ordinally and omits true nested words in ordinary sources. UBT 70 contains a special verified exception because its final source-closed word was spuriously nested by a structural repair. For all four sources the existing full-document tests show preserved word+layout and line inventories.

**Plan:** In *opt-in* recovery only, cross-check ordered literal original opening offsets of `<w>` and `<lb>` inside the genuine source `<text>` against the corresponding ordered Expat span opening offsets, allowing only signed byte-local lexical opener changes. Fail closed on any missing/duplicated/out-of-order/unknown opening or nonliteral start BEFORE graph writes. Emit `source_word_open` (absolute original opening byte offset) on each real TF `word` OR the source-word `layout` fallback, and `source_line_open` on every TF `line` node. Independently record the exact source-coordinate ordered sequence actually **fed to the TF writer**; reject if it differs from the original immutable source event sequence. A word's `source_word_open` is independent of its (potentially fabricated) closing `src_span`: the reviewed recovered word retains `recovery_open` and `src_span=None`. Do not stamp provenance onto ordinary non-pilot generated artifacts.

**RED:** For each of KBo 12.55, KBo 10.36, KUB 48.15 and UBT 70, build the real complete-document opt-in graph; extract original literal opening offsets independently with quote-aware scanner and `text` boundaries, assert every original `<w>` is represented by exactly one TF `word` or source-word `layout` feature, and every `<lb>` by exactly one TF `line`. Assert no duplicate/unknown/missing coordinates and that each literal opening's bytes begin with the exact expected tag name. Compare per-word order and per-line order, plus real separate word and line ownership for UBT 70. Confirm normal non-opt-in mode does not expose new source-identity features. Adversarial unit contract rejects compensating substitutions, duplicates, reversed order and synthetic/unanchored source-coordinate claims.

**Scope:** This verifies actual emitted node identities for four reviewed sources; it is NOT a full parser independent of the historical repaired metadata/line tree or an independent published-artifact validator. Do not extend to genuinely nested source `<w>` cases without specifying the non-1:1 ownership rule. No new corpus versions, restamped current manifest, upstream XML edits, or loss-allowance reductions.


## Lexical attribute/body identity beyond opener equality (2026-10-10)

**Research.** The prior opening audit proves every emitted TF word/layout has an immutable source `<w>` coordinate, but current `_document` zips Expat source spans with an lxml tree by ordinal: a source-opening identity can remain valid even if a different lxml `<w>` node supplies `trans` and `mrp*`, or a different Expat word body supplies sign bytes. In four reviewed files the raw `<w>` starts are 14, 160, 37 and 5. Each original word has either a real literal `</w>` or precisely one SHA-reviewed implicit close (at `</text>` in three terminal singleton cases, at the next actual `<lb>` in UBT 70). The mechanical-only stream is valid for attribute extraction after signed, byte-local opener repairs; the historical full stream has synthetic structural closing bytes and is **not** an independent authority for word semantics.

**Plan.** Independently derive an immutable, ordered `LexicalWordWitness` sequence from `PreparedSource.mechanical_bytes` using source-token opening and closing offsets and the **one** reviewed logical implicit-close event. Validate word-stack pairing, including no overlapping/nested words in these four explicit one-to-one source pilots, and reject ambiguous multiple close events, missing/extra literal closing tags, and any unreviewed line boundaries. Parse only each mechanical `<w ...>` opening tag with a strict, network-disabled XML parser to recover its complete attribute map, including all `mrpN` and `mrp0sel`, without accepting attrs from repaired lxml ancestry. The witness body is the mechanical bytes between original real opening and closing delimiter, or the reviewed original-byte payload for the unique implicit word. Validate exact `<w>` opener location and mechanical/original offset alignment; do not claim synthetic `src_span`.

**TDD RED.** For all four actual source files, require one witness per source word opening; compare the source lexical `@trans`, `@mrp0sel`, `@mrpN` set and body bytes against the actual loaded TF `word` at that `source_word_open` and all `layout` word-openings (layout-only words carry no pretend sign payload). Verify actual selected/analysis TF projections correspond to independently source-parsed attrs, and reconstruct source word sign `srcxml+after` byte-for-byte where sign-bearing. The recovered implicit word must not claim a real closing tag; the final UBT 70 word must retain its own real literal close and separate source morph. Unit adversaries: substitute a different lxml attribute map at the correct opener, swap two mechanically different word bodies while retaining source opener ids, insert another `</w>`, forge a source hash or mechanical content, and give an unreviewed source to the helper. All must fail closed **before CV word emission**.

**Scope/acceptance.** Explicit opt-in only, four signed reviewed sources; preserve default nested word behavior, generated artifact and manifest, corpus loss allowances and original AOxml. This adds source **lexical word parity**, not an independently reconstructed full document/manuscript tree or released corpus. Hosted RED → implementation and real TF integration → adversarial review on exact head. Do not create extra one-off PRs or corpus revisions.


## 2026-10-10 — output-level lexical morphology audit (next #150 gate)

**Research.** The four signed opt-in files now have source-SHA-backed
`LexicalWordWitness` records for each original lexical opening, and the
converter verifies the expected opening, complete lexical attribute map and
body bytes before emitting nodes. This establishes *input* identity; the
loaded TF graph's `analysis` features and valued `selected` edges are not
yet checked candidate-by-candidate. In `convert._State.word`, each `mrpN`
is written as one `analysis` node, linked by `E.analyses`, and numerical
`mrp0sel` tokens are accumulated as valued `E.selected` edges. Comparing
only `nanalyses` and `mrpsel` would not detect swapped lemmas, missing
clitics, candidate-index permutation or incorrect selected-edge values.

**Frozen limited plan.** Add an opt-in *read-only loaded-graph* audit taking
a separately source-authenticated lexical attribute map and a word node.
It must compare the complete per-candidate emitted feature vector, ordered
indices, parse/normalization raw preservation, and the exact valued selected
edge map. Include a separate basic selector-token check independent of the
production writer's choice of edge targets. The audit may use `morph.parse`
as the canonical grammar, but this shared parser means the audit guards
**writer/serialization parity, not independent philological correctness**:
pin diverse human-readable original-source cases with explicit expected
analyses as a separate regression. Do not use a strict reparsed document as
the expected source, silently skip a morphology-bearing `layout`, infer a
missing word boundary, or publish an artifact on the strength of this gate.

**TDD / review.** RED first for the absent audit entry point using four
source-SHA-checked loaded TF documents, candidate features and valued edge
checks. Include negative tampering of an emitted candidate field and a
source selection token, plus explicit no-sign/layout scope handling. Implement
a narrow validator without changing conversion/default output. Independently
review both its source authority and the oracle's limitation; run the full
ordinary suite and keep the stacked PR draft until shared structural
validators and a real one-current-artifact build pass.


## 2026-10-11 — analysis slot ownership after selected-edge membership (#150)

**Research:** the real source `CTH 820_XML_TLH/KUB 48.15.xml` contains separate
`<w trans="nu" mrp0sel=" 1 " mrp1="nu@@ CONNn@@ ">` elements.
The current opt-in TF writer creates each `analysis` with
`cv.node("analysis", slots=set(word_slots))`. The source-word opening
identity, per-candidate feature audit, and recently fixed selected-edge
destination membership cannot detect a graph where an `E.analyses` edge
targets an analysis whose `oslots` were accidentally assigned to an
otherwise identical *different source word*. Word-relative candidate
`index=1` and selector `"1"` are not cross-document identity keys.

**Frozen TDD gate:** build the loaded one-document TF graph with signed source
recovery for KUB 48.15, select the two original `nu` words using separate
immutable `LexicalWordWitness.opening_offset` values, and verify each
own analysis's `L.d(analysis, otype="sign")` equals the source word's
`L.d(word, otype="sign")` on the actual graph. Inject a graph-consumer
mutation where `E.analyses` and `E.selected` remain valid but the loaded
analysis slot membership points to the other real word's signs. That must
fail with an explicit diagnostic; the old checker should fail the RED test.

**Implementation boundary:** read-only guard in `morph_output.assert_word_output()`
on every candidate, checking exact set/order of sign slots on both nodes.
Do not modify the writer, source files, existing genuine nested-word policy,
loss allowlists, or generated artifact/manifest. Verify in the complete
corpus-derived unit/adversarial suite and repeat a fresh independent review
against the final exact head. This establishes graph slot parity only for
the four signed opt-in pilots, not an independent morphology grammar,
an event-derived full source tree, or migration of corpus validators.


## 2026-10-11 — external source-to-loaded-TF corpus recovery gate (#150)

**Independent audit gap:** The four SHA-reviewed sources already have source-opening,
lexical-byte and morphology audits, but they are scattered across test-only paths
and converter-internal `verify_emitted_openings`. Existing corpus-wide
`check_structure.py`, `check_signs.py`, `check_morph.py` still read
historically repaired XML; their successful runs do **not** certify source-event
recovery output. Adding another converter-self-check does not close that gap.

**Decision:** A small reusable *consumer-side* `recovery_audit.verify(prepared, api)`
takes an authenticated `PreparedSource` and a freshly loaded **single-source**
TF graph (not converter callbacks). It obtains immutable original `<w>` and
`<lb>` opening identities using `recovery.original_opening_sequences` and
complete lexical attributes/body witnesses from mechanical-only source tokens.
Require exactly one TF `document`; exactly one TF `word` OR source-word
`layout` per original lexical opener and one `line` per literal line opener;
no extra unanchored nodes, duplicates, unknown opening identities, or skipped
words. Match source `@trans`, reconstructed `sign.srcxml + sign.after`
against original word body, and per-analysis features/edge values/slot ownership
via `morph_output.assert_word_output`. Recovering a word with an implicit
close must *not* claim a real `src_span`; real closed words must retain
a source-anchored `src_span`. The `layout` path never silently certifies
source morphology and is checked fail-closed via the morphology verifier.
All checks are **read-only** against the serialized, loaded graph.

**TDD RED:** Pilot files KBo 12.55, KBo 10.36, KUB 48.15, UBT 70 from the
fixed SHA policy must pass the consumer's per-document source/graph census.
Inject wrong source-word opening identity, a forged source-line opening,
and a corrupted emitted sign `srcxml` while keeping aggregate node counts
unchanged; each must be rejected. Tampered source SHA and an additional
unreviewed input must fail closed. Run this independent gate as a CLI over
the four sources in CI (building transient TF outside tracked `tf/`).
The consumer never uses the repaired lxml tree to derive its expected
lexical or line inventory and never reads the converter's emitted-openings
list or a current-build manifest as its oracle.

**Scope:** source-to-loaded-TF structural+lexical+analysis parity for **four**
explicit reviewed pilot sources, not a corpus-wide replacement for repaired
XML, not a philologically independent grammar, and not proof that header,
manuscript, damage/annotation, #105 layout morphology, #109 nested morphology,
or all 47 repairs are conserved. Keep existing global validators and artifact
manifest unmodified until wider recovery is proven. Independent skeptical
review must explicitly test source authority and adversarial graph mutation.
