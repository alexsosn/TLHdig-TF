# TLHdig → Text-Fabric: Conversion Plan

**Companion document:** [TF-CONVERSION-RESEARCH.md](TF-CONVERSION-RESEARCH.md) —
all counts and format claims below are measured there.

**Source:** TLHdig Beta 0.3 (`10.5281/zenodo.20328284`, ZIP MD5
`f9acbc8db3111cc7dd88d82f7819a912`), 23,937 XML files, 380 MB.

> **Revised** after a second research pass against HPM/HFR/SimTex documentation. Most
> of what was originally an open question is now specified from upstream sources; five
> questions remain (§9). Two parser requirements changed materially: the `mrp` clitic
> separator has four surface forms (§5.5) and part-of-speech detection must key on a
> closed vocabulary rather than leading whitespace (§5.5).
**Target:** a Text-Fabric dataset `tlhdig` with a companion TF app, loadable via
`use("<org>/tlhdig")` and browsable with `tf <org>/tlhdig`.

---

## 1. Goals and principles

1. **Lossless.** The TF dataset must permit byte-faithful reconstruction of every
   word's source markup. This is achievable — measured at 99.99% on a 95k-word sample
   (research §8.3), with the residual being prototype artefacts.
2. **Parsed *and* raw.** Every derived feature ships alongside the raw source string it
   was derived from. Where the source is ambiguous or undocumented (`materlect`, the
   stem-class/POS polysemy), the raw value is authoritative and the parse is advisory.
3. **All analyses, not just the selected one.** The corpus is only partly disambiguated
   (295,907 words have an empty `mrp0sel`). Keeping only the selected analysis would
   silently discard most of the annotation.
4. **Nothing invented.** No language codes are guessed, no `XXXlang` placeholder is
   turned into `Hit`, no broken file is silently dropped without being recorded.
5. **Follow the cuneiform precedent.** Node types, feature naming and the
   `atf`/`sym`/`after` reconstruction contract follow `Nino-cunei/oldbabylonian` so the
   dataset is idiomatic to existing TF users; section/text-format conventions follow
   BHSA.

---

## 2. Target model

### 2.1 Slot type: `sign`

**Decision: `sign`.** Justification in research §8 — editorial brackets fall mid-sign
in the majority of cases (`laes_fin` 89% mid-sign, `del_fin` 55%) and cross word
boundaries in ~40k cases per 500k words, so word-level slots cannot represent damage
extents. Sign slots plus a source-faithful per-sign string round-trip losslessly.

Projected slot count: **≈3,097,100**. (BHSA is 426,590 slots; Old Babylonian 203,219.
This is a large but unremarkable TF dataset.)

A sign is a maximal run of transliteration characters between `-` or `.` separators,
within one wrapper context. Markers interrupting a sign stay inside it, at their exact
offset.

### 2.2 Node types

| Type | Est. count | Definition |
|---|---|---|
| `sign` | 3,097,100 | **slot type** |
| `word` | 1,221,053 | one `<w>` with text content |
| `cluster` | ~590,000 | one editorial bracket span (`del`, `laes`, `ras`, `add`, `quot`) — may nest and may cross words/lines |
| `colon` | 95,101 | span between `<clb>` markers (only in the 4,305 documents that have them) |
| `line` | 407,623 | span opened by `<lb>` |
| `paragraph` | 98,583 | span closed by `<parsep>` / `<parsep_dbl>` |
| `surface` | 41,627 | obverse/reverse/edge + column, per fragment |
| `fragment` | 28,787 | one manuscript witness (`€n`) inside a document |
| `document` | 23,713 | one source XML file |
| `lex` | 32,055 | lemma+gloss pair, linked to all its occurrences (BHSA-style) |
| `manuscript` | 23,568 | one physical tablet/publication siglum; groups the records that transliterate it |
| `note` | 11,663 | footnote anchored at its position |

`cluster`, `colon`, `lex`, `manuscript` and `note` are non-section types. `word` is
*not* a section level but is the natural display unit.

**`manuscript` replaces the `sameas` edge from the first draft.** `docID` is manuscript
identity, not record identity (research §3.1): a Sammeltafel such as `KUB 26.71` belongs
to CTH 1, 18 and 39.6 at once and is legitimately edited three times. A `manuscript`
node keyed on `docID` and linked to the slots of all its records makes "show me every
edition of this tablet" a one-hop query. It is discontiguous and may span the whole
corpus — the same shape as BHSA's `lex`, so this is precedented, not exotic. The 136
multi-record manuscripts get `nrecords > 1`; the 22 with byte-identical bodies get
`identical=1` so accidental copies can be separated from deliberate re-editions later
without a reconversion.

### 2.3 Section levels

TF allows three. Chosen:

```
@sectionTypes    = document,surface,line
@sectionFeatures = docid,surface,lnno
```

Rationale: `document / surface / line` mirrors Old Babylonian's `document / face / line`
and is what a Hittitologist actually cites (`KUB 21.8 Vs. II 5′`). `fragment` sits
between document and surface in the containment hierarchy but is *not* a section level —
in composite texts a surface belongs to a fragment, and the `€n` siglum is carried as a
feature on both, so nothing is lost.

Because `docID` is not unique (136 collisions, research §3.1), the document section
feature is a **derived unique key**: `docid` = `<docID>` when unique, else
`<docID> (<CTH>_<subcorpus>)`. The raw values stay in `docid_raw`, `cth`, `subcorpus`,
`srcfile`.

Structured section support (`tf.core.text`) can additionally expose `fragment` via a
custom section for the browser app.

### 2.4 Text formats

Following the Old Babylonian pattern — a source-faithful format, a plain one, a rich one
and a cuneiform one, each with its own inter-sign material feature:

```
@fmt:text-orig-full     = {atf}{after}
@fmt:text-orig-plain    = {sym}{after}
@fmt:text-orig-rich     = {symr}{after}
@fmt:text-orig-unicode  = {cu}                      (line-level, see §5.6)
@fmt:text-trans-morph   = {sym}{after}              word layer adds {lemma}
@fmt:lex-orig-plain     = {lemma}
@fmt:lex-default        = {lemma} '{gloss}'
```

* `atf` — sign string **with all inline markers in place** (the reconstruction feature).
* `sym` — clean reading, markers stripped: `ur`, `DINGIR`, `x`.
* `symr` — rich rendering: Sumerograms in caps, determinatives raised, Akkadograms
  italic-marked, brackets rendered as `[ ] ⸢ ⸣ ⟨ ⟩`.
* `after` — what separates this sign from the next (`-`, `.`, ` `, ``).

`{atf}{after}` concatenated across a word must equal the word's original inner XML.
That is the round-trip contract and it is a build-time assertion (§7.1).

---

## 3. Feature catalogue

Node features, grouped by the node type they primarily belong to. `int` type is noted;
everything else is `str`.

### 3.1 `sign`

| Feature | Source | Notes |
|---|---|---|
| `atf` | word inner XML slice | **reconstruction feature** — markers at exact offsets |
| `sym` | text nodes | clean reading, no markers |
| `symr` | derived | rich/rendered form |
| `after` | separator | `-`, `.`, ` `, `` |
| `type` | wrapper context | `reading` \| `sumerogram` \| `akkadogram` \| `determinative` \| `numeral` \| `signname` \| `unknown` (`x`) \| `ellipsis` (`…`) \| `empty` |
| `sgr` `agr` `det` `num` | `<sGr> <aGr> <d> <num>` | `1` when the sign lies inside that wrapper |
| `signname` | `<c type="sign">` | sign given by name |
| `damage` | `del_in`/`del_fin` | `full` \| `initial` \| `final` \| `medial` — where the bracket cuts the sign |
| `laesio` | `laes_in`/`laes_fin` | same value set |
| `rasura` | `ras_in`/`ras_fin`/`ras_X` | erasure |
| `added` | `add_in`/`add_fin` | editorial addition |
| `quoted` | `QUOT_HurInHit_*` | Hurrian quoted in Hittite |
| `corr` | `<corr c>` | `?`, `!`, `sic`, … verbatim |
| `subscr` | `<subscr c>` | **epigraphically subscripted sign** attached to this sign — *not* a reading index (research §3.5) |
| `materlect` | `<materlect c>` | mater lectionis / explanatory additional sign |
| `materlect_anomalous` (int) | derived | `1` for the 65 instances whose `@c` is a bare `!`/`?` — mis-styled legacy data that belongs in `corr`; value still preserved in `materlect` |
| `surplus` | `<surpl c>` | excised superfluous sign (content is in `@c`) |
| `space_count` (int) | `<space c>` | **count of U+0020 SPACE characters** preceding this sign (ODF `text:s/@text:c`); unitless — never convert to a physical measure |
| `lang` | `<lb @lg>` / `<w @lg>` | inherited, word override wins |

### 3.2 `word`

| Feature | Source |
|---|---|
| `trans` | `@trans` — normalised lookup form |
| `atfw` | full inner XML of `<w>` (belt-and-braces reconstruction) |
| `mrpsel` | `@mrp0sel`, whitespace-trimmed |
| `mrpsel_kind` | derived: `analysis` \| `DEL` \| `AKK` \| `HURR` \| `HAT` \| `SUM` \| `LUW` \| `unknown` \| `none` |
| `mrpsel_idx` (int) | selected analysis index, when numeric |
| `mrpsel_alt` | selected sub-alternative letter(s), e.g. `a`, `a b`, `aR`, `all` |
| `nmrp` (int) | number of competing analyses |
| `mrp` | **all raw `mrpN` values joined by `\n`** — the lossless carrier |
| `lemma` `gloss` `morph` `stemclass` `det` | parsed fields of the **selected** analysis |
| `stemclass_raw` | field 4 verbatim, before the three-way disambiguation |
| `clitic_lemma` `clitic_morph` `clitic_det` | parsed clitic segment of the selected analysis |
| `pos` | set when field 4 is a member of the closed category vocabulary (§5.5) |
| `field4_kind` | `stemclass` \| `pos` \| `morph` — which of the three readings field 4 took |
| `mrp_sep` | which clitic separator form the value used (`+=`, `@+=`, `+@`, `@+@`) — a data-quality handle |
| `lang` | `<w @lg>` when present |
| `editingquestion` | `@editingQuestion` (4 words) |

**Alternative analyses.** The selected one is flattened into scalar features for
convenience; *all* of them are preserved twice over — raw in `word.mrp`, and structurally
as `lex` nodes reachable through the `mrpalt` edge (§4). No analysis is dropped.

### 3.3 `lex`

| Feature | Notes |
|---|---|
| `lemma` | citation form, `=` morpheme boundaries intact |
| `gloss` | German gloss |
| `stemclass` | HPM paradigm number |
| `det` | expected determinative / classifier |
| `freq_lex` (int) | occurrence count |
| `rank_lex` (int) | frequency rank |

### 3.4 `line`

| Feature | Source |
|---|---|
| `lnr` | raw `@lnr` |
| `lnno` | normalised citation form used as the section label |
| `surface` `column` `ln` (int) `prime` `linetail` | parsed components (research §5) |
| `frag` | `{€n}` siglum in scope |
| `txtid` | `@txtid` |
| `lang` | `@lg` (`ign` preserved — it positively asserts unknown language) |
| `cu` | cuneiform Unicode of the line |
| `cudirty` | `@cuDirty` |
| `cu_pua` (int) | count of Private-Use-Area codepoints in `cu` |
| `cu_pua_unmapped` (int) | count of PUA codepoints with no known identity (i.e. `U+100009`) |
| `srcln` (int) | line number in the source XML file |

### 3.5 `paragraph`, `colon`, `cluster`, `note`, `surface`, `fragment`

| Node | Features |
|---|---|
| `paragraph` | `parnr` (`<AO:ParagrNr c>`, e.g. `§ 1′`, `Kolophon`), `ruling` (`single` \| `double`) |
| `colon` | `id`, `nr`, `lang` (from `<clb>`) |
| `cluster` | `type` (`del` \| `laes` \| `ras` \| `add` \| `quot`), `crossesword` (int 0/1), `crossesline` (int 0/1), `unbalanced` (`open` \| `close` when the partner marker is absent) |
| `note` | `n` (footnote number), `c` (raw escaped rich text), `ctext` (unescaped plain text) |
| `surface` | `surface`, `column`, `frag`, `label` |
| `fragment` | `frag` (`€1`…), `txtpubl`, `invnr`, `directjoin`, `indirectjoin` |

### 3.6 `document`

Identity and provenance:

`docid` (unique key) · `docid_raw` · `cth` · `cth_alt` · `cth_neu` · `subcorpus` ·
`srcfile` (path relative to corpus root) · `lang` (**omitted entirely when the source
says `XXXlang`** — TF has no null, and absence is the correct encoding of "unset";
`lang_raw` keeps `XXXlang` verbatim) · `lang_raw` · `txtpubl` ·
`manuscripts` (raw `<AO:Manuscripts>` text) ·
`nfragments` (int) · `wellformed` (int 0/1) · `repaired` (int 0/1) ·
`repairnote` (what was fixed).

Editorial history — one feature per `<meta>` element kind, value = `editor|date|part`
records joined by `\n`, plus a flattened first/last:

`creationdate` · `aoxmlcreation` · `annot` · `kor` · `kor1kf` · `kor2` · `neu` ·
`uebern` · `uebern_src` · `format` · `author` · `kolon` · `val` · `trlst` · `join` ·
`merge` · `merged` · `aufheb` · `aufloes` · `korof` · `koltaf` · `kolfot` · `kolfot2` ·
`editors` (deduplicated set) · `lastedit` (max date).

---

## 4. Edge features

| Edge | From → To | Valued | Purpose |
|---|---|---|---|
| `oslots` | non-slot → sign | no | warp |
| `mrpalt` | `word` → `lex` | **yes** — value is the `mrpN` index | links a word to *every* candidate lemma, not only the selected one; the value lets you recover which analysis it came from |
| `mrpsel` | `word` → `lex` | yes — value is the sub-alternative letter | the selected analysis only; absent when `mrp0sel` is empty or non-numeric |
| `editionof` | `document` → `manuscript` | no | every record of the same tablet points at one `manuscript` node (replaces the first draft's `sameas` edge) |
| `joins` | `fragment` → `fragment` | yes (`direct` \| `indirect`) | from `AO:DirectJoin` / `AO:InDirectJoin` |
| `noteref` | `note` → `sign` | no | anchors a footnote to the sign it follows |

`mrpalt` is what makes the undisambiguated 80% of the corpus queryable: a search for a
lemma finds every word where that lemma is *a* possible reading, and the caller can then
filter on `mrpsel`.

---

## 5. Conversion pipeline

Nine stages. Each writes an auditable report; the whole thing is re-runnable from
scratch.

### 5.0 Environment

Text-Fabric is not currently installed on this machine (checked: Python 3.7.12 default,
3.11/3.13 available, no `tf`, no `lxml`). First step:

```bash
python3.13 -m venv .venv && .venv/bin/pip install text-fabric lxml
```

`lxml` matters: it gives byte offsets and better recovery-mode parsing than
`xml.etree.ElementTree`, both of which the repair and round-trip stages want.

### 5.1 Inventory

Walk the tree, record every file with size, path, CTH, sub-corpus, parse status.
Produce `reports/inventory.tsv`. This is the manifest everything else joins against.

### 5.2 Repair (224 files)

Apply the pattern fixes classified in research §9.1, in this order, each guarded by a
regex that must match exactly once:

1. Corrupted `<gap>` tags: `<kap c-"…"` → `<gap c="…"/>`, undoing the g→k, x→%, b→p,
   ch→ḫ substitution damage. Also `<clp it-"…"` and `<kap c-` variants.
2. Unclosed ODF `text:line-break`.
3. Unclosed `AO:KolonNr` / `AO:Sumgram` / `AO:Akkgram`.
4. Misplaced `</w>` around `<gap>`.
5. Unescaped `"` inside attribute values.
6. `<parser_error>` inside `@cu` → strip the wrapper, keep the text, set `cudirty`.
7. Duplicate `cu` attribute → keep first (values are identical in the one case).
8. Typo'd element/attribute names: `del_iin`→`del_in`, `mrpl`→`mrp1`, `mDodID`→`mDocID`.

Each repaired file is written to `repaired/` (never over the source), and the document
gets `repaired=1` plus a `repairnote`.

`CTH 813_XML_TLH/KUB 37.25.xml` is **encrypted** and cannot be repaired — it is excluded,
recorded in `reports/excluded.tsv`, and should be reported to the HPM team.

Target after this stage: 23,936 of 23,937 files parse.

### 5.3 Normalisation

* Trim `mrp0sel` padding; keep the raw in `mrpsel_raw` if it differs.
* Leave dirty values (`lg="Hit> <w>…"`, `corr c="MEŠ"`) **untouched** in the raw
  features; expose a cleaned parallel feature only where the cleaning is unambiguous,
  and flag the rest in `reports/dirty-values.tsv`.
* `xml:lang="XXXlang"` (4,520 documents) means *unset* — omit `document.lang` entirely
  for those (TF encodes absence by omitting the data line) and keep `XXXlang` in
  `lang_raw`. Do **not** map it to `ign`: `ign` is TLHdig's documented positive marker
  for a passage of genuinely unknown language (`@Ign`) and appears independently 75
  times in `lb/@lg`.
* Handle the structural quirks of research §9.3: `<w>`/`<lb>` directly under `<div1>`,
  nested `<w>`, `<clb>`/`<lb>` inside `<w>`. Treat the flattened stream, not the tree.

### 5.4 Tokenisation

Per document, produce a flat token stream from `<text>` (and `<div1>`), then:

* `<lb>` closes the previous line node and opens a new one; parse `@lnr` into
  fragment/surface/column/number/prime/tail. A `@lnr` with no number is a **surface
  header**, not a line.
* A change of fragment or of surface/column opens new `fragment` / `surface` nodes.
* `<parsep>`/`<parsep_dbl>` **closes** the current paragraph (measured, research §3.4).
* `<clb>` closes the current colon and opens the next; only in the 4,305 documents that
  have them.
* `<w>` → a `word` node; its content is tokenised into `sign` slots by the algorithm
  validated in research §8.3. `<w>` with no text and no `@trans` produce **no** word
  node; their markers still open/close clusters and their `<space c>` becomes
  `spacebefore` on the next sign.
* Bracket markers push/pop a cluster stack that is **document-scoped, not word-scoped**,
  so clusters may span words and lines. Unmatched opens/closes at document end are
  closed at the document boundary and flagged `unbalanced`.

### 5.5 Morphology

Parse each `mrpN` per the grammar in research §4.1.

**Separator.** Four surface forms exist (research §4.1), two using a bare `+`. Splitting
on `+=` alone mis-handles 5,655 values. Required:

```python
# accepts ' += ', '@+= ', ' +@', '@+@' and spacing variants
segs = re.split(r"\s*\+=?\s*", raw)
base = segs[0].rstrip("@").split("@")   # lemma, gloss, morph, stemclass [, det]
clit = segs[1].split("@") if len(segs) > 1 else None   # lemma, morph, stem [, det]
det  = raw.split("@")[-1]               # det is always the last @-field
```

Record which form was seen in `word.mrp_sep`; any value that still yields an
unexpected field count is left unparsed and flagged, never truncated.

**Field 4 is three-way polysemous** — stem class, part of speech, or logographic
morphology. The discriminator is a **closed vocabulary, tested on the trimmed value**:

```python
KNOWN_POS = {"ADV","POSP","PREV","CNJ","NEG","INTJ","INDCL",
             "QUANcar","QUANmul","QUANord","DEMadv","INTadv","INDadv", ...}
t = field4.strip()
if t in KNOWN_POS:                     field4_kind = "pos"
elif NUMERIC_PARADIGM.fullmatch(t):    field4_kind = "stemclass"
else:                                  field4_kind = "morph"     # e.g. D/L.SG(ABBR)
```

Leading whitespace is recorded as a **consistency check only** — 65 distinct values,
including every core POS, occur both with and without it (research §4.1), so it cannot
be the primary test. `stemclass_raw` always keeps the verbatim value. The 244 distinct
non-numeric values must be triaged by hand once and frozen as a lookup table, including
the compounds (`ADV, POSP, PREV`) and language-prefixed forms (`HURR`, `HATT`,
`PAL.CONNn || PAL.INTJ`).

**Alternative sets and `mrp0sel`.** Split `{ a → X} { b → Y}` into an ordered map so a
selector letter can index it, then:

* numeric `N` and `Na`/`Nb` — direct index, as before;
* `Nall` — **documented** (HFR annotation manual): select every alternative;
* `Nsg` / `Npl` — select every alternative carrying that number. Corroborated at
  **99.92%** against the corpus (research §4.2) but not formally documented, so the
  parser must *validate* each one against the referenced analysis and flag the residue
  rather than assuming;
* upper-case `R`–`V` — clitic-segment alternatives. Reverse-engineered, not documented;
  treat as such in the feature docs.

**Emit** `lex` nodes keyed on `(lemma, gloss, stemclass, det)`; wire `mrpalt` / `mrpsel`
edges. Anything unparseable keeps the raw string and sets `mrp_parse_ok=0`.

### 5.6 Cuneiform

`@cu` is line-level and unaligned (research §6). Plan:

* **Phase 1 (in scope):** attach `cu` to the `line` node verbatim, with `▒` and PUA
  codepoints preserved. `@fmt:text-orig-unicode` renders at line granularity. Add
  `cu_pua`, `cu_pua_unmapped` and `cu_broken` (count of `▒`) as data-quality features.
  Ship a PUA lookup table in `docs/`, seeded from the HPM/HitType sign list:
  `U+100000` = **SI×SÁ** (HZL 28), retained in Supplementary PUA-B because no standard
  Unicode cuneiform character exists. `U+100009` (2,572 occurrences) is **not** in the
  current sign list and its identity must not be guessed — it counts toward
  `cu_pua_unmapped` and is question 3 in §9.
  No public sign-aligned `@cu` export exists (research §6.2), so phase 2 cannot be
  planned around one.
* **Phase 2 (stretch, explicitly out of the first release):** attempt sign-level
  alignment by matching the `▒`/sign counts against the tokenised signs of the line.
  Only accept an alignment when the counts agree exactly; store as `symu` on signs and
  record the success rate. Do not force partial alignments.

This is the one place where "preserve all features" and "align everything" pull apart,
and the honest answer is to preserve first and align later.

### 5.7 Build

Use `tf.convert.walker.CV` with a `director` that walks the token stream. `CV` gives
node/edge/feature actions, validates the graph, and handles slot ordering. Declare
`slotType="sign"`, plus `otext`, `generic` (provenance metadata for every feature),
`intFeatures`, and `featureMeta` (a one-line description per feature — these become the
`@description` lines in the `.tf` files and the corpus's own documentation).

### 5.8 Validate

See §7.

### 5.9 Package

* `tf/0.3/` — the feature files, version-tagged to match the Zenodo release.
* `app/config.yaml` + `app/static/` — the TF-browser app (BHSA-style `typeDisplay`,
  `provenanceSpec` with the 0.3 DOI, `writing` set for the transliteration font).
* `docs/features.md` — generated from `featureMeta`, in the style of
  `Nino-cunei/tfFromAtf/docs/transcription.md`.
* `programs/convert.py`, `programs/checks.ipynb`.
* `reports/` — inventory, repairs, exclusions, dirty values, validation.

---

## 6. Hard cases and how they are handled

| Case | Handling |
|---|---|
| Markers inside a sign (55–89% of closing brackets) | kept in `sign.atf` at their exact offset; `damage`/`laesio` record *where* (`initial`/`medial`/`final`/`full`) |
| Brackets crossing words and lines (~40k per 500k words) | `cluster` nodes with a document-scoped stack; `crossesword`/`crossesline` flags |
| Unbalanced brackets | closed at document boundary, flagged `unbalanced=open\|close`; never silently dropped |
| 403,169 contentless `<w>` | not words; their markers and `<space>` still affect clusters and `spacebefore` |
| 136 duplicate `docID`s, only 22 identical | file path is the key; `docid` disambiguated with CTH+subcorpus; a `manuscript` node groups the records (`editionof` edges), with `nrecords` and `identical` so accidental copies stay separable from Sammeltafel re-editions |
| `XXXlang` (4,520 documents) | `lang` omitted (= unset), `lang_raw` keeps the token; **not** mapped to `ign`, which has a distinct documented meaning |
| `materlect` holding `!`/`?` (65 of 315) | value preserved, `materlect_anomalous=1`; not reinterpreted as a new materlect sense |
| bare-`+` clitic separators (1,926 values) | split regex accepts an optional `=`; form recorded in `mrp_sep` |
| Undisambiguated words (295,907 empty `mrp0sel`) | all analyses retained via `mrpalt`; `mrpsel_kind=none` |
| `DEL` tokens (195,508) | word node still created, `mrpsel_kind=DEL`; they are part of the text |
| 224 malformed files | repaired (§5.2), 1 excluded and reported |
| PUA cuneiform codepoints | preserved; counted in `cu_pua` |
| `U+100009` identity unknown | preserved; counted in `cu_pua_unmapped`; not guessed (§9) |
| Footnote `@c` holds escaped XML | raw in `note.c`, unescaped plain text in `note.ctext` |

---

## 7. Validation

Nothing ships until all of these pass.

### 7.1 Round-trip (the primary gate)

For **every** word in the corpus: `"".join(atf + after for signs of word)` must equal the
word's original inner XML. The prototype already achieves 99.9906% with only
serialisation artefacts remaining; the production tokeniser must reach **100.000%** or
list every exception in `reports/roundtrip-failures.tsv` with its cause.

### 7.2 Count invariants

Assert against the measured figures in the research document:

| Invariant | Expected |
|---|---|
| `document` nodes | 23,713 (+ repaired ones, − 1 excluded) |
| `line` nodes | 407,623 |
| `word` nodes | 1,221,053 |
| words with `@trans` | 914,243 |
| `colon` nodes | 95,101, in 4,305 documents |
| `parsep` + `parsep_dbl` | 74,948 |
| total `mrpN` analyses ingested | 1,611,153 |
| distinct lemmata | 28,091 |
| distinct lemma+gloss pairs | 32,055 |
| lines with `cu` | 405,787 |
| `manuscript` nodes | 23,568 (136 with `nrecords` > 1, of which 22 `identical`) |
| `materlect` elements | 315 total, 65 flagged anomalous |
| `mrpN` values with a clitic | 385,431 (350,781 ` += ` · 28,995 `@+= ` · 3,729 other · 1,853 ` +@` · 73 `@+@`) |
| `Nsg`/`Npl` selectors validating against their analysis | 1,281 of 1,282 |
| documents with `lang` omitted (`XXXlang`) | 4,520 |

A deviation is a bug, not a rounding difference.

### 7.3 Structural checks

* `oslots` monotone: every non-slot node covers a contiguous-or-explicitly-gapped slot
  set; `cluster` is the only type permitted to be discontiguous.
* Every `line` is inside exactly one `surface`, every `surface` in one `fragment`, every
  `fragment` in one `document`.
* Every `word` slot set is a subset of exactly one `line`'s slot set — **except** where
  a word is split across a line break; count and report those rather than assuming zero.
* Section lookup `T.nodeFromSection(("KUB 21.8", "Vs. II", "5′"))` round-trips.

### 7.4 Spot checks

Hand-verify a fixed panel of ~30 documents chosen to cover: a simple single-fragment
Hittite text, a composite with `€1+€2+€3`, an Akkadian text, a Hurrian text, a text with
`clb` colon segmentation, a text with heavy footnoting, a repaired file, and a
duplicate-`docID` pair. Render each with all four text formats and diff against the
source XML by eye. Ship the panel as `programs/checks.ipynb`.

---

## 8. Milestones

| # | Deliverable | Depends on |
|---|---|---|
| 1 | venv + TF installed; `inventory.tsv` over all 23,937 files | — |
| 2 | Repair pass; 23,936/23,937 parse; `repairs.tsv`, `excluded.tsv` | 1 |
| 3 | Sign tokeniser at 100% round-trip on the full corpus | 2 |
| 4 | `mrp` parser + `lex` node builder; parse-failure report | 2 |
| 5 | `lnr` parser; fragment/surface/line hierarchy | 2 |
| 6 | Full `CV` director; first `tf/0.3/` build | 3, 4, 5 |
| 7 | Validation suite green (§7) | 6 |
| 8 | `app/config.yaml`, TF browser working, `docs/features.md` | 6 |
| 9 | `checks.ipynb` spot-check panel; README; Zenodo deposit of the derived dataset | 7, 8 |

Milestones 3–5 are independent and can proceed in parallel.

---

## 9. Open questions for the TLHdig / HPM team

The second research pass closed most of the original list from upstream documentation
(see research §3.5, §4.1, §4.2, §6.1). Five genuinely open questions remain. None
blocks the conversion; each has a documented fallback.

1. **`mrp0sel` = `Nsg` / `Npl`** — confirm these select *all alternatives of the stated
   number*. The corpus corroborates it at 99.92% (1,281/1,282), but no public document
   states it. *Fallback:* parse as a group selector, validate against the referenced
   analysis, flag the residue.
2. **`mrp0sel` upper-case selectors** — confirm that lower-case `a`–`m` index base
   alternatives and upper-case `R`–`V` index clitic alternatives. *Fallback:* implement
   the inference, document it as reverse-engineered.
3. **`U+100009`** — 2,572 occurrences in `lb/@cu`, absent from the current HPM sign list
   (which retains `U+100000` = SI×SÁ and `U+100007`, plus `U+10000A`). Possibly a legacy
   Ullikummi/HPM assignment. What sign is it? *Fallback:* preserved, counted as
   unmapped, never guessed.
4. **Sign-aligned `@cu`** — does an internal alignment of the line-level cuneiform to
   sign positions exist? Nothing public was found. *Fallback:* line-level only; §5.6
   phase 2 stays out of the first release.
5. **`space/@c`** — an explicit AOxml definition would be welcome. The ODF-pipeline
   reconstruction (`text:s/@text:c` = count of U+0020) is high-confidence but is
   inferred, not read from an AOxml schema. *Fallback:* unitless integer.

Separately, two items to **report** rather than ask:

* **`CTH 813_XML_TLH/KUB 37.25.xml` ships encrypted** in Beta 0.3 — an
  ownCloud/Nextcloud `HBEGIN:oc_encryption_module:…AES-256-CTR` envelope inside a ZIP
  documented as an XML dataset with "XML errors and inconsistencies corrected". Send the
  archive path, DOI `10.5281/zenodo.20328284`, ZIP MD5
  `f9acbc8db3111cc7dd88d82f7819a912`, and the file's first ~100 bytes; ask for the
  plaintext to be restored next version.
* **65 `<materlect>` elements carry `!`/`?`** rather than a sign reading — editorial
  marks that belong in the `<corr>` mechanism. Likely mis-styled legacy data worth
  cleaning upstream.

## 10. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Sign tokeniser cannot reach 100% round-trip on the long tail | medium | the 0.01% residual is already characterised as serialisation-only; failures are enumerated, not swallowed |
| Cluster stack mis-nests on the ~40k unbalanced brackets | medium | unbalanced spans are explicitly flagged rather than repaired; validation counts them |
| 3.1M slots make the TF browser sluggish | low | comparable to existing corpora; `excludedFeatures` in `app/config.yaml` trims the display |
| Repair regexes over-match and corrupt good data | low | each guarded to match exactly once; repaired files written separately and diffed |
| Upstream 0.4 release invalidates counts | certain, eventually | version-pin to `tf/0.3/`; the validation invariants make a re-run against a new release cheap |
| `mrp` grammar has undocumented forms beyond the 0.05% residual | low | raw string always retained; `mrp_parse_ok` and `mrp_sep` make the residual queryable — this risk already materialised once (the bare-`+` separator, 1,926 values) and was caught by exactly this method |
| Hand-triaged field-4 vocabulary drifts in a later release | medium | `stemclass_raw` always kept; `field4_kind` is derived, so a corrected table can be re-applied without re-tokenising |

---

## 11. What "preserving all available features" means concretely

Mapping the ten requirements from research §10 onto this design:

| # | Requirement | Where it lands |
|---|---|---|
| 1 | Byte-faithful word markup | `sign.atf` + `sign.after`; gate §7.1; `word.atfw` as backup |
| 2 | All 1.6M analyses | `word.mrp` (raw, newline-joined) + `mrpalt` edges to `lex` |
| 3 | `mrp0sel` incl. `DEL`/`AKK`/`???` | `word.mrpsel`, `mrpsel_kind`, `mrpsel_idx`, `mrpsel_alt` |
| 4 | Decomposed line references | `line.lnr` raw + `surface`/`column`/`ln`/`prime`/`linetail`/`frag` |
| 5 | Manuscript witnesses & joins | `fragment` nodes, `joins` edges, `document.manuscripts` |
| 6 | Full editorial edit log | ~22 `document` features, one per `<meta>` element kind |
| 7 | Line cuneiform incl. `▒` and PUA | `line.cu`, `cu_pua`, `cu_broken`, `cudirty` |
| 8 | Footnotes with rich text | `note` nodes, `note.c` raw + `note.ctext`, `noteref` edges |
| 9 | Language at 3 levels | `document.lang`/`lang_raw`, `line.lang`, `sign.lang`/`word.lang` |
| 10 | Provenance | `document.srcfile`, `cth`, `cth_alt`, `cth_neu`, `subcorpus`, `docid_raw` |

Every item in the source format inventory (research §3.5) has a destination. Nothing in
the AOxml markup is dropped.

Where upstream documentation now settles the semantics — `materlect`, `subscr`,
`space/@c`, `XXXlang`, `mrp0sel=all`, the Stammklasse column, `U+100000` — the derived
feature carries the documented meaning **and** the raw value. Where it does not — the
five items in §9 — only the raw value is authoritative, the derived feature is marked
provisional in `docs/features.md`, and a `*_raw` companion guarantees that an upstream
answer can be applied by re-deriving rather than reconverting.
