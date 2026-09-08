# Research: source-faithful sign language propagation

Issue: #19 — Add source-faithful language values at sign level.

This document freezes the research gate before any production/schema change.
Measurements are from the pinned TLHdig 0.3 corpus after the checked-in repair manifest,
using strict production eligibility: 23,937 XML files, one encrypted exclusion, 52
unparseable-after-repair exclusions, and 23,884 converted text documents.

## 1. Source declaration inventory

Language is declared in the source at four materially relevant levels:

1. `<text xml:lang="…">` — document/text fallback;
2. `<lb lg="…">` — current physical line;
3. `<clb lg="…">` — current colon/stretch, persistent until replaced or closed by a
   column change;
4. `<w lg="…">` — one-word override.

A single `<par lg="Hit"/>` occurs in `CTH 832_XML_HFR/KBo 66.79.xml`; surrounding
line/colon declarations are also `Hit`, so it supplies no independently observable
sign-language evidence and is not promoted into a new propagation scope in #19.

The corpus contains 454,037 language-bearing attributes in total. Important raw values
include the expected `Hit`, `Akk`, `Hur`, `Hat`, `Luw`, `Sum`, `Pal`, plus source values
such as `ign`, `5f_`, `Hattian`, `Lin`, `Lu`, `Hitt`, `30lang`, `w`, and one cuneiform
character. Malformed source values also survive in a few repaired `lb/@lg` attributes,
for example `Hit> <w><note n='15' c=`. They are source data, not ours to normalize away.

The dominant declaration counts are:

| declaration | occurrences |
| --- | ---: |
| `lb/@lg=Hit` | 368,661 |
| `text/@xml:lang=Hit` | 17,998 |
| `lb/@lg=Akk` | 17,653 |
| `lb/@lg=Hur` | 13,466 |
| `lb/@lg=Hat` | 6,400 |
| `w/@lg=Hur` | 6,262 |
| `text/@xml:lang=XXXlang` | 4,620 |
| `clb/@lg=Hit` | 3,961 |
| `lb/@lg=Luw` | 3,643 |
| `w/@lg=Luw` | 3,262 |

There are 82 explicit empty declarations: 44 empty `lb/@lg` and 38 empty `w/@lg`.

## 2. Effective-language precedence

The source evidence supports this exact precedence for each readable sign emitted from a
word:

```text
positive w/@lg
    else positive active clb/@lg
    else positive current lb/@lg
    else positive text/@xml:lang
    else absent
```

A **positive** declaration is the stripped raw value when it is non-empty and not
`XXXlang`.

No language is inferred from transliteration spelling, cuneiform, morphology,
Sumerogram/Akkadogram markup, subcorpus, CTH number, neighbouring words, or any external
classifier.

### Why colon outranks line

This is not cosmetic. The corpus has large stretches where an active `clb/@lg` differs
from the current `lb/@lg`, e.g. Hurrian colon material inside Hittite-labelled lines.
The earlier candidate models disagree on many tens of thousands of signs; line-first
inheritance would erase those embedded-language stretches.

### Why word outranks colon/line

Observed word overrides include, by source-sign count:

- `Hur` inside inherited `Hit`: 20,533 signs;
- `Akk` inside `Hit`: 2,602;
- `Luw` inside `Hit`: 1,704;
- `Sum` inside `Akk`: 929;
- `Hit` inside `Akk`: 787;
- `Sum` inside `Hit`: 580;
- and smaller mixed-language cases.

The word attribute therefore cannot be treated as descriptive metadata on the word only;
it is the narrowest observed source override.

## 3. Empty and unknown declarations

Empty values and `XXXlang` are **not positive language labels**. They do not themselves
become `sign.lang` values.

A dedicated barrier audit tested the stronger interpretation "an explicit empty/unknown
attribute blocks inheritance from outer scope". That interpretation would suppress an
otherwise positive source language on 170 readable signs:

- 89 signs: empty word attribute over line `Hit`;
- 63 signs: empty line attribute over text `Hit`;
- 18 signs: empty word attribute over active colon `Hit`.

The repository's existing coarser `lang` behavior also only writes non-empty values.
Therefore #19 treats empty and `XXXlang` as no positive override and continues outward.

`ign` is different: it is a non-empty raw source value. It remains `ign`; #19 does not
reinterpret it as absence.

## 4. Raw values versus normalized identity

The shipped line/colon/document `lang` features preserve raw upstream strings rather
than mapping them to a controlled language ontology. #19 keeps that compatibility:

- `sign.lang` stores the winning source value verbatim after the same whitespace test
  used to decide positivity;
- no `Hit → Hittite`, `Hat → Hattian`, etc. normalization is introduced;
- malformed/legacy source values remain distinguishable instead of being silently
  collapsed.

A normalized language-identity layer, if desired, is a separate modelling ticket.

## 5. Scope lifetime and repaired nested boundaries

The production converter treats `<lb>` and `<clb>` as boundary events while walking the
repaired `<text>` tree. This matters because malformed/unclosed word markup can cause a
later real physical boundary to appear XML-nested under `<w>` after recovery.

Measured repaired corpus:

- all `<lb>` events: 412,637;
- `<lb>` events with a `<w>` ancestor: 986;
- all `<clb>` events: 98,008;
- `<clb>` events with a `<w>` ancestor: 647.

Manual inspection of representative files shows that at least many such nested events
are genuine following physical line/colon boundaries, not sign-inline language
annotations. For example an unclosed word is followed by the next real `<lb>`.
Discarding every nested boundary merely because of repaired XML ancestry is therefore
not source-faithful.

A dual-model audit compared:

- **production/recovery semantics**: all recovered boundary events participate;
- **naive XML-grammar semantics**: ignore boundaries whose repaired DOM ancestor is a
  word.

After also reproducing the converter's real colon lifetime at parsed column changes, the
models differ on the winning *scope level* for only 310 signs, but **not on the raw
language value**:

- 309: production chooses `colon Hit`, naive model chooses `line Hit`;
- 1: production chooses `colon Akk`, naive model chooses `line Akk`.

Thus recovered nested boundaries do not fabricate a different sign-language value in
the measured corpus. #19 follows production/recovery boundary semantics and records the
scope level only in the conservation report, not as a shipped semantic feature.

### Colon lifetime

`_State.start_line()` closes the active colon when `lineref.parse(lb/@lnr)` changes
column; otherwise an ordinary new line does not close it. A new `<clb>` replaces the old
colon. The independent research model reproduces this behavior.

## 6. Exact source/TF population reconciliation

The original source scanner appeared to be 21,215 signs short of shipped TF. The delta
is fully explained by technical anchors:

| population | count |
| --- | ---: |
| shipped TF sign slots | 3,386,344 |
| synthetic `anchor=1` sign slots | 21,215 |
| shipped non-anchor/source sign slots | **3,365,129** |
| independently scanned convertible source signs | **3,365,129** |
| delta | **0** |

The language checker must therefore compare source signs only with non-anchor TF sign
slots and must assert that synthetic anchors never receive `lang`.

The source contains another 22 readable token signs in 36 words before the first `<lb>`.
The current converter intentionally does not emit those words/signs. This is a separate
pre-existing fidelity defect and is tracked in #52; #19 must not silently fabricate a
line or broaden its scope to absorb them.

## 7. Corrected inheritance-level census

Using production/recovery boundary semantics, correct column-aware colon lifetime, and
`word → colon → line → text` positive-value precedence, the 3,365,129 emitted source
signs divide exactly as follows:

| winning source level | signs |
| --- | ---: |
| line | **3,259,913** |
| colon | **64,686** |
| word | **40,187** |
| text | **195** |
| genuinely absent | **148** |
| **total** | **3,365,129** |

The 148 absent signs have no positive source declaration under the supported algorithm.
They must remain without `sign.lang`.

Representative winning raw values include:

- line `Hit`: 2,929,540 signs;
- line `Akk`: 143,961;
- line `Hur`: 106,512;
- colon `Hit`: 46,750;
- line `Hat`: 39,618;
- line `Luw`: 27,362;
- word `Hur`: 21,876;
- colon `Hur`: 11,730;
- word `Luw`: 9,455;
- line `Sum`: 6,566;
- line `Pal`: 5,653;
- colon `Hat`: 4,626;
- word `Akk`: 3,028;
- text `Hit`: 195;
- line `ign`: 625.

## 8. Required conservation contract

The implementation is accepted only if an **independent checker** reconstructs source
language scope without importing or sharing the converter's propagation helper and then
verifies:

1. every converted document's ordered non-anchor sign sequence has the expected
   `sign.lang` value sign-for-sign;
2. exactly 3,364,981 non-anchor signs carry `lang` and exactly 148 do not;
3. the winning-level census is exactly line 3,259,913 / colon 64,686 / word 40,187 /
   text 195 / absent 148;
4. all 21,215 technical anchor slots lack `lang`;
5. total sign order/count and unrelated features are unchanged except for the new
   immutable artifact version.

The checker report is the provenance-level audit artifact; `sign.lang` itself remains a
single source-faithful effective value.

## Evidence

Hosted research runs:

- Actions run `34159645675`: declaration/precedence and empty/unknown barrier scans;
- Actions run `34160087625`: exact source-versus-TF population reconciliation;
- Actions run `34160852897`: repaired nested-boundary and column-scope dual-model audit.

Research-only scripts/workflows are temporary evidence harnesses and are removed before
final PR review once these measurements are frozen here and in the permanent checker.
