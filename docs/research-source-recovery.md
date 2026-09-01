# Research: conservative recovery of malformed TLHdig AOxml

## Scope

This document records a forensic review of the malformed-source cases currently handled by TLHdig-TF's crossing-tag repair machinery, plus the separate balanced-but-lossy `KBo 70.109+` case.

The review changes the recommended boundary of responsibility for TLHdig-TF. The converter should not make philological corrections to TLHdig, and it should not silently turn a guessed repair into a new source text. It should instead recover as much structurally unambiguous material as possible, record any local loss explicitly, and exclude a document when the source no longer contains enough structure for a defensible conversion.

The source release remains the immutable TLHdig Beta 0.3 Zenodo snapshot. The live TLHdig website can be used as an upstream witness when investigating malformed structure, but it must not become an unversioned replacement data source.

---

## 1. Current state

### 1.1 Crossing-tag repair is currently a source rewrite

`programs/tlhdig/repair.py` treats `detect_crossing_tags()` as a last-resort detector. For a crossing such as:

```xml
<w><AO:K>...</w>...</AO:K>
```

it closes every inner element before the parent close. For an unmatched close it drops the close tag. The resulting bytes are then parsed as repaired XML.

This is mechanically useful for making XML well-formed, but it can move semantic and word boundaries. The current report therefore correctly refuses to call these repairs automatically trustworthy.

### 1.2 Measured repair inventory

`reports/crossing-tag-review.md` contains **74 crossing-tag repair events in 62 source files**.

The events are highly repetitive rather than 74 unrelated editorial problems:

| repair family | unique files | repair events / shape | current risk |
|---|---:|---|---|
| `w` left open across later structure | 47 | 47 events; current repair closes one or more `w` elements only when `</text>` is reached | outer word can swallow later words/lines |
| semantic/layout wrapper crossing a word boundary | 14 salvageable files | wrappers such as `Akkgram`, `KolonNr`, `sGr`, `HitGLOS`, `AkkGLOS`, `TabSep`, `--italic`, `Manuscripts`, or `TxtPubl` | exact wrapper extent is ambiguous, but surrounding text often is not |
| structurally collapsed document | 1 file: `KBo 38.169` | six `AO:TxtPubl`/`AO:Manuscripts` repair events | normal text structure is absent |

The 15 wrapper-class files are:

- `CTH 144_XML_SVH/KUB 26.29+.xml` — `AO:Akkgram`;
- `CTH 336_XML_MYTH/KUB 33.57.xml` — `AO:KolonNr`;
- `CTH 336_XML_MYTH/KUB 33.60.xml` — `AO:KolonNr`;
- `CTH 381_XML_GEBET/KUB 6.46.xml` — `sGr`;
- `CTH 409_XML_BESRIT/KBo 53.35+.xml` — `AO:HitGLOS`;
- `CTH 412_XML_TLH/KBo 38.169.xml` — collapsed `AO:TxtPubl`/`AO:Manuscripts` structure;
- `CTH 420_XML_TLH/KBo 53.31.xml` — `AO:AkkGLOS`;
- `CTH 458_XML_BESRIT/KBo 56.227.xml` — `AO:HitGLOS`;
- `CTH 460_XML_TLH/KBo 56.45.xml` — `AO:HitGLOS`;
- `CTH 577_XML_HDivT/AT 454.xml` — `sGr`;
- `CTH 72_XML_TLH/KUB 19.15+.xml` — `AO:Manuscripts`;
- `CTH 819_XML_TLH/KUB 4.89.xml` — `AO:TabSep`;
- `CTH 831_XML_TLH/IBoT 4.235.xml` — `AO:--italic`;
- `CTH 831_XML_TLH/IBoT 4.249.xml` — `AO:--italic`;
- `CTH 832_XML_TLH/KBo 71.216.xml` — `AO:TxtPubl`.

The other 47 files are the repeated unclosed/nested-`w` family.

### 1.3 Current lossy baseline is caused by the repair strategy

`programs/known_lossy.txt` currently lists `KBo 70.109+` plus 45 crossing-tag files because repaired outer `w` spans enclose whole lines and nested words. The converter then treats the malformed enclosing word as covering those bytes; when it yields no slots, valid descendants can be lost.

`reports/structure.md`, however, reports only **15 missing top-level `<w>` elements** against 1,642,274 top-level source words in the repaired stream. That combination is evidence that the issue is localized and that document-wide exclusion is usually unnecessary.

The right target is therefore zero silent downstream loss outside the smallest malformed span, not a globally well-formed synthetic XML tree.

---

## 2. Responsibility boundary

TLHdig-TF is a derived computational representation of TLHdig. It should not decide what an editor "must have meant" when two philologically meaningful wrapper boundaries cross.

The converter may make **structural parser decisions** when those decisions follow from the surrounding machine-readable structure itself. Examples:

- a new sibling `<w>` starts while another `<w>` is still open;
- a new `<lb>` starts while a word is still open;
- `</text>` is reached while a word is open;
- a semantic wrapper cannot be kept without choosing an unsupported boundary, but its textual descendants can still be tokenized independently.

The converter should not:

- invent a corrected upstream XML file;
- choose a semantic wrapper extent merely because one choice makes XML well-formed;
- copy live-site text into the frozen Beta 0.3 corpus without an explicit new source/release model;
- hide locally dropped material behind a global success percentage.

Recommended wording for the policy is:

> Preserve the immutable source bytes. Recover only structurally defensible content. Record local recovery and local omission explicitly. Introduce no philological emendations.

---

## 3. The unclosed/nested `w` family is structurally recoverable

### 3.1 The current repair closes too late

For the 47 `w` cases, the current patch frequently inserts one or more `</w>` tags immediately before `</text>`. In the most extreme examples it inserts many closes because the parser stack has accumulated nested `w` elements.

That makes the document well-formed, but it preserves the wrong containment relation: an earlier malformed outer word can still contain later `<w>` and `<lb>` elements.

### 3.2 Better synchronization points already exist in AOxml

A tolerant parser does not need to wait until the end of `<text>`.

If a word is open and the parser encounters a structural element that cannot be a normal child of that word, the open word can be finalized or locally abandoned before the new structural element. High-value synchronization points include:

```text
<w>      start of the next word
<lb>     start of the next line
</text>  end of the transliteration
```

A simple recovery rule is therefore:

```text
if inside word and next start tag is a sibling-level word/line boundary:
    end current malformed word at the boundary
    record structural recovery
    process the new structure normally
```

If the bytes accumulated for the malformed word itself cannot be tokenized safely, only that word/span should be omitted; following independent words and lines should survive.

### 3.3 `KBo 12.55`: end-of-text recovery needs no philological decision

The Beta 0.3 source ends the final textual line with an open word followed by `</text>`:

```xml
<w ...><del_fin/>x<d>ḪI.A</d>-uš<gap c="Text bricht ab"/>
</text>
```

The live TLHdig entry for `KBo 12.55` identifies the same tablet in the current HPM infrastructure, and the case is structurally clear even without consulting the live renderer: a word cannot legitimately contain the closing `text` element.

For conversion, `</text>` is a defensible hard synchronization boundary. Closing parser state there does not require deciding a Hittite reading or editorial restoration.

Relevant live HPM entry:

- https://hethport.net/hetkonk/hetkonk_abfrage.php?c=209

### 3.4 `KBo 70.109+`: balanced XML can still contain a semantic structural error

`KBo 70.109+` is not caught by normal XML well-formedness checks because its tags balance. Around `{A1} obv. ii 20`, the source contains a new `<w>` before the preceding `<w>` has been closed:

```xml
<w><del_in/><d>D</d>ḫu...<gap c="(ligature da+aš+ši)"/>
<w><d>PÚ</d>ḫar-ki</w>
```

This is exactly the case for a sibling-start synchronization rule: the nested `<w>` is a direct machine-readable signal that the previous word boundary has been lost.

The remainder of the file contains normal independent `<lb>` and `<w>` structure after the defect, so losing roughly thirty subsequent lines is an artifact of the current converter path, not an unavoidable property of the source.

The live TLHdig/HPM representation should be retained as corroborating upstream evidence when this case is implemented, but the recovery decision is already justified structurally by the source markup.

---

## 4. Crossing semantic wrappers should usually be dropped locally, not reconstructed

The wrapper-class cases are different from unclosed words. A crossing can make the exact extent of a label such as `AO:HitGLOS` or `AO:Akkgram` ambiguous while leaving the underlying words and signs obvious.

Example shape:

```xml
<w><AO:HitGLOS>...
</w>
<w>...</AO:HitGLOS></w>
```

The current repair chooses one boundary by closing `AO:HitGLOS` before `</w>`. That may be correct, but XML syntax alone cannot prove it.

TLHdig-TF does not need to make that choice. The safer fallback is:

```text
preserve source bytes                         yes
preserve independently tokenizable words     yes
preserve independently valid damage markup   yes
preserve morphology attached unambiguously   yes
assert ambiguous wrapper extent               no
record dropped-crossing-wrapper diagnostic    yes
```

In implementation terms, the tolerant parser can unwrap the malformed semantic/layout wrapper for the affected local region while continuing to parse its textual descendants.

### 4.1 Representative live evidence

The live TLHdig entry for `AT 454`, one of the `sGr` crossing cases, renders a long structured text with words and morphological analyses. This demonstrates that a local broken wrapper does not imply that the document as a whole lacks usable structure:

- https://hethport.net/TLHdig/tlh_xtx.php?d=AT+454

Likewise, HPM's live indexes expose normal line-addressed evidence from `KUB 6.46`, another `sGr` crossing case:

- https://hethport.net/HiTop/hetgeoitem.php?i=%E1%B8%AAalap

These live pages are supporting evidence for salvageability. They should not be copied into the frozen corpus.

---

## 5. `KBo 38.169` is qualitatively different

`CTH 412_XML_TLH/KBo 38.169.xml` does not merely contain a wrapper crossing around otherwise normal text. Its transliteration has collapsed into repeated `AO:Manuscripts` / `AO:TxtPubl` structures such as:

```xml
<AO:Manuscripts><AO:TxtPubl>KBo 38.169</AO:Manuscripts>
<AO:Manuscripts><AO:TxtPubl>x+2 mu-k...
<AO:Manuscripts><AO:TxtPubl>3' ...
<AO:Manuscripts><AO:TxtPubl>4' ...
```

There is no normal `<lb>` / `<w>` hierarchy to recover from those bytes without reconstructing the intended AOxml model from prose-like content.

HPM's concordance confirms that `KBo 38.169` is a real witness (`CTH 412.1.4`) and provides bibliographic/contextual metadata, but that does not supply a versioned machine-readable replacement for the malformed Beta 0.3 XML:

- https://hethport.net/hetkonk/hetkonk_abfrage.php?c=412

Recommended policy for Beta 0.3 is therefore:

```text
exclude document from the TF graph
retain the immutable source file
record reason = upstream structural corruption
```

If a future TLHdig release contains a corrected AOxml version, that future source release can include it normally.

---

## 6. Role of live TLHdig

The live website is useful for forensic review because it is maintained by the upstream project and can reveal whether a malformed Beta 0.3 snapshot case is currently rendered as ordinary words/lines.

It should have three roles only:

1. **verification witness** — confirm that a proposed structural recovery agrees with current upstream presentation;
2. **negative control** — show that some malformed sources are not automatically recoverable even by upstream tooling;
3. **future-source discovery** — indicate that a corrected version may exist and should be looked for in a subsequent published source release.

It should not be an implicit build input. Reasons:

- live content can change without a release identifier;
- the build must remain reproducible from a frozen source release;
- silently mixing snapshot bytes and live text weakens provenance;
- licensing/attribution conditions of the live service and the published dataset should not be assumed identical without checking the relevant release metadata.

A recovery record may optionally store live verification metadata such as:

```text
online_verified = true
online_url = ...
online_verified_at = 2026-09-01
```

but the graph content must still derive from the frozen source bytes unless a separately versioned source-import mechanism is introduced.

---

## 7. Recommended recovery classes

Replace the broad concept of "philological crossing-tag repair" with four operational classes:

| class | condition | action |
|---|---|---|
| valid | source parses and structural invariants hold | normal conversion |
| mechanically recoverable | parser can resynchronize at an unambiguous structural boundary | recover locally and record diagnostic |
| locally unsalvageable | text/word descendants are usable but a wrapper/span boundary is not defensible | omit only the ambiguous wrapper/span and continue |
| structurally unusable | no reliable line/word structure can be recovered without reconstructing upstream content | exclude document |

This model keeps responsibility with the converter: it guarantees what it emitted, but it does not edit the scholarly source.

---

## 8. Provenance requirements

Recovery should be queryable and auditable rather than hidden in a byte-patch manifest.

At minimum record, per recovery event:

```text
source path
source SHA-256
source byte offset/range
recovery kind
trigger/synchronization boundary
element name when applicable
whether any source bytes were omitted from semantic modelling
whether the event was checked against live TLHdig
verification URL/date when used
```

Candidate recovery kinds:

```text
implicit_word_close_before_word
implicit_word_close_before_line
implicit_word_close_before_text_end
dropped_crossing_wrapper
dropped_local_malformed_span
excluded_document
```

The raw/provenance module should retain enough information to locate the original bytes even when a semantic wrapper is not represented in the graph.

---

## 9. Validation implications

The success condition should no longer be "repaired XML parses". A stronger release contract is possible.

For every recovered document:

1. all independently well-formed `<lb>` elements outside the malformed local span must survive 1:1;
2. all independently well-formed top-level `<w>` elements outside the malformed local span must survive 1:1;
3. source order must be preserved;
4. no recovery may cause a later unrelated line/word to become a descendant of the malformed element;
5. every omitted semantic wrapper or local span must appear in a generated recovery report;
6. a novel recovery signature must fail the release gate until reviewed as a converter case;
7. whole-document exclusions must balance exactly in the source ledger.

The goal is **zero silent collateral loss**.

This is more informative than allowing a fixed number of missing words or known-lossy files.

---

## 10. Expected effect on the current blocker list

If the tolerant parser satisfies the gates above, the current statement that 74 repairs in 62 files require Hittitological review should be retired.

The expected state is approximately:

- the 47 unclosed/nested-`w` files handled by structural resynchronization;
- 14 wrapper-class files retained with local ambiguous-wrapper loss where necessary;
- `KBo 70.109+` retained with explicit word-boundary recovery;
- `KBo 38.169` excluded as structurally unusable for Beta 0.3;
- no guessed philological wrapper boundaries introduced by TLHdig-TF.

These counts are an implementation hypothesis until the replacement parser is run corpus-wide and the conservation gates pass. The implementation must regenerate the final measured counts rather than hard-code this research estimate.

---

## 11. Relationship to earlier design documents

This research supersedes the assumption in earlier documents that crossing-tag cases should generally be resolved by philological review before publication.

The revised principle is narrower:

- ask for philological/upstream intervention only when the desired output itself requires a scholarly interpretation;
- do not require such intervention merely to preserve unrelated valid words and lines around malformed XML;
- prefer explicit local omission over guessed semantic reconstruction.

The implementation plan is in [`plan-source-recovery.md`](plan-source-recovery.md).
