# Plan: replace crossing-tag source rewrites with conservative fault-tolerant recovery

## Goal

Replace the current boundary-moving crossing-tag repair path with a recovery model that preserves immutable TLHdig Beta 0.3 source bytes, salvages structurally defensible content, reports local omissions explicitly, and excludes only documents that cannot be represented without reconstructing upstream scholarly content.

The implementation should follow TDD and make corpus-wide conservation the release criterion.

Target pipeline:

```text
immutable AOxml bytes
→ mechanical lexical repairs only where already proven safe
→ tolerant structural parser / recovery layer
→ local recovery events + provenance
→ normal TF graph construction
→ corpus-wide conservation gates
→ generated recovery report
```

The converter must not emit or depend on a silently corrected copy of TLHdig.

---

# Phase 0 — freeze the forensic baseline

## 0.1 Generate a machine-readable recovery inventory

Add a script that derives the current malformed-structure inventory from the frozen Beta 0.3 source rather than relying only on prose reports.

Output:

```text
reports/source-recovery-inventory.json
```

The observation layer must record, per manifest event:

```text
event_id
path
source_sha256
manifest patch ordinal
intermediate-stream byte offset
original-file byte offset + exactness
triggering close boundary
ordered inserted closing-tag list + count
exact old/new bytes
original byte context
current known_lossy membership
current contract_a_known membership
```

Do **not** put `suggested_recovery_class` or any other conclusion into this generated observation file. Recovery/evidence disposition is a separately reviewed layer.

The generated inventory must reproduce the current source/manifest facts: 74 crossing-tag events in 62 files, **136 inserted closing tags**, **22 multi-close events**, maximum close depth 14, with triggering boundaries `text=48`, `w=18`, `AO:Manuscripts=7`, `d=1`. It must also measure current overlap with validation allowlists rather than inheriting their comments as truth.

The v2 observation layer also measures the current filtered-token effect per crossing file: **45 files, 94 failing word spans, 300,246 filtered bytes**. The measured file set currently agrees exactly with crossing-file membership in `known_lossy.txt`, but the span evidence supersedes the allowlist's uniform causal comments. Of the 94 spans, 85 contain both `<lb>` and nested `<w>`, 4 contain nested `<w>` without `<lb>`, and 5 contain neither.

These are assertions about the pinned Beta 0.3 source/manifest and current converter, not permanent acceptance counts after migration.

## 0.2 Freeze reviewed dispositions separately from observations

Keep reviewed decisions in:

```text
programs/source_recovery_dispositions.json
```

This is a policy layer, not generated evidence. It must cover the exact 74 observation event IDs and bind every decision to the event's `observation_fingerprint`. That fingerprint includes the immutable source SHA, manifest patch ordinal, intermediate and original offsets, triggering boundary, ordered inserted closes, and exact old/new patch bytes. Changing any of those facts invalidates the old review even when the source file SHA itself is unchanged.

The current reviewed split is:

- 47 mechanically determined word-state resynchronizations;
- 19 ambiguous wrapper extents to omit while preserving descendants;
- 6 source-unusable events, all in `KBo 38.169`, whose document is excluded;
- 1 strongly supported stray-`AO:Manuscripts` omission in `KUB 19.15+`;
- 1 mechanically determined misnamespaced `TxtPubl` close in `KBo 71.216`.

Any novel or changed observation fingerprint must fail closed until its disposition is reviewed.

## 0.3 Add forensic fixtures before changing behavior

Create minimal adversarial fixtures for every recovery family:

```xml
<!-- open word reaches text end -->
<text><lb/><w>foo</text>

<!-- nested word indicates lost close -->
<text><lb/><w>foo <w>bar</w></text>

<!-- line starts while word remains open -->
<text><lb/><w>foo <lb/>bar</text>

<!-- semantic wrapper crosses word boundary -->
<text><lb/><w><AO:HitGLOS>foo</w><w>bar</AO:HitGLOS></w></text>

<!-- stray close -->
<text><lb/><w>foo</AO:HitGLOS></w></text>
```

Also include corpus-derived regression fixtures for:

- `KBo 12.55`;
- one `AO:HitGLOS` crossing case;
- `KUB 26.29+` (`AO:Akkgram`);
- `AT 454` (`sGr`);
- `KBo 38.169` as an exclusion case.

Tests must assert preserved word/line order, local diagnostics, absence of collateral loss, and a negative control showing that an ordinary well-formed nested `<w>` is left untouched by #12 recovery.

---

# Phase 1 — separate lexical repair from structural recovery

## 1.0 Introduce one shared prepared-source contract

Do not let the converter and independent validators prepare source bytes independently. Add one deterministic API used by all consumers of repaired/recovered source.

The contract must keep at least these concepts distinct:

```text
original_bytes          immutable Beta 0.3 evidence
mechanical_bytes        only proven byte-local XML/lexical repairs
structural view/events  recovered hierarchy/synchronization without claiming synthetic bytes are source
source coordinate map   structural/derived nodes -> immutable original offsets
recovery events         explicit local parser decisions and omissions
```

A parser may synthesize internal structural state to continue parsing, but synthetic close tags must never become `sign.srcxml` or otherwise masquerade as original evidence. Logical recovered words need original-source evidence slices bounded by deterministic synchronization points.

The shared API is required by both production conversion and source gates. Today `repair.apply()` is called independently by converter, sign, structure, morphology, marker, tag, language, manuscript and other checks; changing only `convert.py` would make validation and production reason over different source views.

## 1.1 Do not split structural vs mechanical patches by `reason` alone

The current manifest is sequential, and crossing repairs can change the interpretation of later patches. A corpus check finds **21 crossing events that are not the final patch in their file**. In the common wrapper pattern, the crossing patch inserts an early synthetic `</wrapper>`; a later patch then deletes the original delayed `</wrapper>` as `stray close tag, nothing open`. Examples include `KUB 26.29+`, the `AO:HitGLOS` cases, `KUB 4.89`, and the `AO:--italic` cases. If Phase 1 merely filters out patches whose reason is `crossing tags...` while retaining the later `stray close` patches, it destroys original structural evidence.

`KBo 71.216` demonstrates the converse dependency: the manifest first drops the original misnamespaced `</TxtPubl>`, then the crossing repair synthesizes `</AO:TxtPubl>`. The replacement model must treat that pair as one reviewed source defect rather than applying the first patch independently.

Before a production prepared-source API stops applying crossing rewrites, add a source-grounded dependency census for every patch in the 62 crossing files and classify **crossing-coupled** patches. The API must replay only genuinely byte-local repairs; it must preserve original closes/fragments needed by structural recovery. A patch's historical `reason` string is evidence about how the old repair loop behaved, not a sufficient safety classification.

## 1.2 Keep proven byte-local mechanical repairs

Retain existing repair detectors that correct lexical/XML syntax defects where the correction does not choose a scholarly structural boundary, for example the existing classes for:

- stray unterminated tag fragments with no content;
- unescaped `<` or quotes in attributes;
- duplicate attributes;
- parser-error element names;
- other already measured byte-local cases.

Their existing SHA-pinned patch/provenance behavior remains useful.

## 1.3 Remove `detect_crossing_tags()` from the production repair path

`detect_crossing_tags()` should no longer rewrite source bytes by closing inner elements before a parent close.

Options:

- retain it temporarily as a diagnostic detector only; or
- replace it with a scanner that reports crossing structure without emitting patches.

No production build should depend on a boundary-moving crossing-tag patch after this migration.

## 1.4 Preserve source-coordinate mapping

Any tolerant parser must continue to expose source offsets against the original file. Mechanical lexical patches already have `OffsetMap`; structural recovery should add semantic parser events without fabricating corresponding source bytes.

A recovery event must point to the triggering original-byte range.

---

# Phase 2 — implement tolerant word resynchronization

## 2.1 Add explicit structural states

Do not rely on a generic XML parser's synthetic tree for malformed word structure. Add a recovery-aware token/event layer with enough state to recognize when a `w` cannot legitimately continue.

**Scope recovery to reviewed malformed signatures.** A document that parses strictly after byte-local mechanical repairs bypasses #12 structural recovery entirely. The corpus already contains 4,378 well-formed nested source `<w>` elements tracked by #109, so “new `<w>` while a word is open” is not a global AOxml grammar rule. Likewise, do not assume globally that every `<lb>` inside a word is invalid without an independent corpus census. The resynchronization rules below apply only while recovering a strict-parse failure that matches a reviewed #12 observation/disposition; an unreviewed structural signature fails closed and enters the review inventory.

At minimum distinguish:

```text
inside text
inside line
inside word
inside semantic wrapper(s)
```

## 2.2 Word synchronization rules

When a `w` is open:

### Rule A — new sibling `<w>`

Before consuming a new `<w>`, finalize the previous malformed word at the new tag boundary.

Diagnostic:

```text
implicit_word_close_before_word
```

The balanced-but-lossy nested-word case `KBo 70.109+` is owned by #13. #12 may share a recovery primitive only if #13's independent research justifies the same rule; it must not absorb that case into this ticket.

### Rule B — new `<lb>`

A line boundary cannot become part of an accidentally unclosed word. Finalize or locally abandon the word before the `<lb>` and begin the next line normally.

Diagnostic:

```text
implicit_word_close_before_line
```

### Rule C — `</text>`

Finalize the current word at the transliteration boundary.

Diagnostic:

```text
implicit_word_close_before_text_end
```

This covers cases such as `KBo 12.55`.

## 2.3 Define finalize vs omit

A recovered word may be emitted only if the bytes accumulated before the synchronization boundary can be converted with the normal sign/token rules without swallowing independent descendants.

If not, omit only that local malformed word/span and record:

```text
dropped_local_malformed_span
```

The following `<w>` / `<lb>` must still be processed normally.

## 2.4 Test the 47 current `w`-close crossing files corpus-wide

After implementing these rules, run every crossing file whose current manifest event inserts one or more `</w>` closes before `</text>` and assert:

- all lines outside the local defect survive;
- all independent subsequent words survive;
- no nested `w` remains in the logical recovery event stream unless a separately modelled nested-word case is explicitly owned elsewhere;
- the current **94 failing spans / 300,246 filtered bytes** on crossing files decrease according to exact recovery accounting rather than by enlarging an allowlist;
- local terminal cases do not get the same treatment as catastrophic swallowed descendants merely because both currently end with `w -> </text>`.

The RED set must include at least one example from each measured word-stack form:

1. catastrophic line + nested-word swallowing;
2. nested-word swallowing without a line boundary;
3. local terminal formatting/gap loss with neither `<lb>` nor nested `<w>`.

---

# Phase 3 — unwrap crossing semantic/layout wrappers

## 3.1 Classify wrappers by whether their extent is semantically meaningful

Initial crossing wrapper set from Beta 0.3:

```text
AO:Akkgram
AO:KolonNr
sGr
AO:HitGLOS
AO:AkkGLOS
AO:Manuscripts
AO:TxtPubl
AO:TabSep
AO:--italic
```

Do not assume the same policy for every future element. Classification must be explicit and tested.

## 3.2 Default recovery: preserve descendants, drop ambiguous extent

When one of these wrappers crosses a word/line boundary and no single boundary follows mechanically from the source structure:

1. stop asserting that wrapper at the crossing point;
2. preserve independently parseable textual descendants;
3. resume normal word/line parsing;
4. do not reopen the wrapper unless source markup explicitly opens it later;
5. emit a recovery diagnostic.

Diagnostic:

```text
dropped_crossing_wrapper
```

Metadata:

```text
element
source byte range
triggering close/open boundary
whether any descendant text was omitted
```

## 3.3 Never propagate wrapper ambiguity to neighboring words

Tests should prove that a malformed `AO:HitGLOS`, `sGr`, or `Akkgram` does not:

- delete following words;
- merge words;
- change line ownership;
- alter unrelated morphology;
- move damage/editorial spans outside their independently observed markers.

## 3.4 Corpus regression cases

Add explicit tests for at least:

- `KUB 26.29+` (`AO:Akkgram`);
- `KUB 33.57` / `KUB 33.60` (`AO:KolonNr`);
- `KUB 6.46` and `AT 454` (`sGr`);
- `KBo 53.35+`, `KBo 56.227`, `KBo 56.45` (`AO:HitGLOS`);
- `KBo 53.31` (`AO:AkkGLOS`);
- `KUB 4.89` (`AO:TabSep`);
- `IBoT 4.235`, `IBoT 4.249` (`AO:--italic`).

---

# Phase 4 — explicit document exclusion for structurally unusable sources

## 4.1 Move `KBo 38.169` to the exclusion ledger

`CTH 412_XML_TLH/KBo 38.169.xml` lacks a defensible normal `<lb>` / `<w>` transcription hierarchy. Do not reconstruct line/word structure from repeated `AO:TxtPubl` strings.

Add it to the version-specific exclusion ledger with a precise reason such as:

```text
upstream structural corruption: transliteration collapsed into Manuscripts/TxtPubl; no defensible line/word recovery
```

The source file remains in the immutable source corpus.

## 4.2 Exclusion must be the last resort

A document can be excluded only when recovery cannot preserve meaningful line/word structure without reconstructing content.

A malformed wrapper alone is not an exclusion reason.

## 4.3 Rebalance corpus counts automatically

Update ledger/census gates so the source identity equation remains exact after the exclusion change.

Do not manually patch expected totals in multiple scripts. Derive them from the version-specific exclusion ledger and generated source inventory.

---

# Phase 5 — recovery provenance model

## 5.1 Add a recovery event representation

Implement a small internal dataclass or equivalent:

```python
RecoveryEvent(
    path,
    source_sha256,
    kind,
    element,
    start_offset,
    end_offset,
    trigger,
    omitted_bytes,
    omitted_semantic_annotation,
)
```

Exact fields may differ, but source identity and offsets are mandatory.

## 5.2 Emit a generated report

Add:

```text
reports/source-recovery.md
```

It should contain:

- counts by recovery kind;
- affected files;
- exact omitted local spans/wrappers;
- whole-document exclusions;
- whether any text/sign bytes were lost;
- a regression comparison with the previous release where applicable.

## 5.3 Optional live-TLHdig verification metadata

Create a checked-in forensic verification table separate from build inputs, for example:

```text
programs/source_recovery_verification.tsv
```

Possible columns:

```text
path
source_sha256
live_url
verified_at
observation
```

Rules:

- build correctness must not depend on network access;
- live verification never replaces source bytes;
- a changed source SHA invalidates the old verification row;
- URLs/dates are evidence only.

A future script may assist the audit, but CI should not fail because the live HPM site is unavailable.

---

# Phase 6 — replace tolerant baselines with conservation gates

## 6.1 Zero collateral line loss

For every recovered document, compare source-level line starts with graph lines.

Required:

```text
all independently identifiable <lb> outside an explicitly omitted local span == graph line nodes
```

No allowlisted missing lines.

## 6.2 Zero collateral word loss

The old fixed "15 missing top-level words" baseline has already been retired by #131. Preserve the current exact structure gate while adding explicit recovery accounting.

Every source top-level word must remain one of:

```text
represented in graph
or
covered by exactly one recovery omission event
```

No unexplained deficit is allowed.

## 6.3 Order conservation

For each recovered file, verify that represented source words/lines appear in graph order identical to source order.

## 6.4 Recovery accounting gate

Every recovery event must have:

- known kind;
- source SHA;
- source offsets;
- deterministic trigger;
- explicit omitted-content accounting.

A novel defect kind should fail the release candidate rather than silently generalizing a recovery rule.

## 6.5 Remove obsolete known-loss allowances

Once the new gates pass:

- delete crossing-repair-derived entries from `programs/known_lossy.txt`;
- keep only genuinely unavoidable loss, if any remains;
- keep `reports/structure.md` at its current exact-conservation contract; do not reintroduce a tolerated deficit.

---

# Phase 7 — migrate documentation and release semantics

## 7.1 Update `KNOWN-ISSUES.md`

Replace the current "74 repairs require philological review" blocker with measured recovery status.

Expected wording after successful implementation should distinguish:

- structural recovery events;
- locally dropped ambiguous wrappers;
- excluded documents;
- remaining genuinely unresolved cases, if any.

Do not publish the research estimates as final numbers until reports regenerate them.

## 7.2 Update `TF-CONVERSION-RESEARCH.md` and `TF-CONVERSION-PLAN.md`

Document:

- immutable-source policy;
- recovery classes;
- synchronization rules;
- provenance semantics;
- exclusion policy.

Remove statements implying that all crossing tags need Hittitological adjudication.

## 7.3 Update upstream automation design

`docs/research-upstream-automation.md` currently treats crossing-tag repairs as review-required publication blockers. Change the future-release policy:

- known deterministic recovery signatures may proceed automatically when source SHA/signature matches and all gates pass;
- novel malformed-structure signatures stop promotion for converter review;
- no automatic publication should introduce a new recovery rule or new whole-document exclusion.

This is software/data-model review, not necessarily philological review.

## 7.4 README release statement

After implementation and regeneration, prefer wording along these lines:

> Malformed upstream XML is handled conservatively by structural resynchronization. Ambiguous annotation wrappers are omitted locally rather than reconstructed, and structurally unusable source records are listed explicitly. TLHdig-TF introduces no philological emendations.

---

# Phase 8 — release-gate integration

## 8.1 Single command

Ensure the eventual release-check command runs, for the same built artifact:

```text
source identity
mechanical repair verification
source recovery inventory/accounting
structure conservation
sign round-trip
marker conservation
Contract A / source provenance checks
morphology checks
cuneiform alignment checks
app validation
census
```

The recovery report must be generated before the final release stamp.

## 8.2 Stamp semantics

A complete/research-ready stamp must imply:

- no unexplained source word/line loss;
- no unaccounted recovery event;
- no guessed crossing-wrapper boundary;
- exclusions exactly match the checked-in version-specific ledger;
- all other release gates passed on the same dataset digest.

---

# TDD sequence

Implement in this order so each behavioral change is test-driven:

1. keep the checked-in source-recovery inventory deterministic and drift-gated;
2. add minimal malformed fixtures and failing expectations for the measured word-stack subclasses;
3. add corpus-derived #12 regression fixtures, including a catastrophic swallowed-line case and a local terminal case such as `KBo 12.55`;
4. implement the shared prepared-source contract and word resynchronization until those RED cases pass;
5. add crossing-wrapper fixtures and tests;
6. implement local wrapper unwrapping without leaking synthetic structural bytes into source provenance;
7. add `KBo 38.169` exclusion test and ledger update;
8. add recovery-event provenance tests;
9. run the 62-file crossing forensic set and create exact accounting assertions;
10. remove crossing-tag source rewrites and crossing-derived known-loss allowances only when measured loss has disappeared or is locally accounted;
11. regenerate reports and documentation;
12. run full current-artifact validation in a fresh process.

`KBo 70.109+` is deliberately absent from this sequence because #13 owns that balanced-but-lossy defect.

At each step, new behavior must first be represented by a failing test. Do not update baselines merely to make a changed result green.

---

# Non-goals

This work does not:

- correct Hittite readings;
- choose between scholarly interpretations of ambiguous wrappers;
- repair TLHdig upstream files in place;
- scrape the live TLHdig site into the corpus;
- reconstruct `KBo 38.169` from publication strings;
- guarantee that future TLHdig releases will exhibit the same malformed patterns.

Future upstream versions must be re-inventoried by source SHA and defect signature.

---

# Definition of done

The migration is complete when all of the following are true:

1. production conversion no longer depends on `detect_crossing_tags()` byte rewrites;
2. the current 47 word-stack crossing files are recovered locally or individually accounted without collateral loss;
3. the measured 94 crossing-file filtered-loss spans / 300,246 bytes are eliminated or explicitly and locally accounted;
4. wrapper crossings no longer force guessed semantic boundaries;
5. `KBo 38.169` is explicitly excluded unless a versioned upstream replacement is found;
6. every missing source word/line is explained by an exact recovery/exclusion event;
7. synthetic structural recovery bytes cannot appear as immutable source provenance;
8. `known_lossy.txt` no longer acts as a broad tolerance for crossing-repair fallout;
9. generated reports replace research estimates with measured final counts;
10. `KNOWN-ISSUES.md`, conversion docs, and upstream automation docs reflect the new policy;
11. the complete current-artifact validation passes against the shipped artifact.

Background and forensic rationale are documented in [`research-source-recovery.md`](research-source-recovery.md).
