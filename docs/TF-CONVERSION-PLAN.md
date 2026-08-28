# TLHdig → Text-Fabric: Conversion Plan

**Companion:** [TF-CONVERSION-RESEARCH.md](TF-CONVERSION-RESEARCH.md) — all corpus counts
and format claims are measured there.

**Source:** TLHdig Beta 0.3 (`10.5281/zenodo.20328284`, ZIP MD5
`f9acbc8db3111cc7dd88d82f7819a912`), 23,937 XML files, 380 MB.
**Target:** a Text-Fabric dataset plus a TF app, loadable with `use("alexsosn/TLHdigTF")`.

> **Revision 3.** Two independent reviews — one against the TF 13.1.0 source and the
> `Nino-cunei` converters, one against all four published cuneiform TF datasets — found
> defects that a naive implementation would have hit. Ten were confirmed by direct
> measurement and are fixed below. Three of my own earlier claims were wrong and are
> retracted in place: the `mrpalt` edge design could not hold multiple analyses (§3.4),
> the `{cu}` text format would have rendered nothing (§3.5), and the round-trip
> experiment did not demonstrate byte-fidelity (§2.1). A fourth — that damage brackets
> form a nesting language — turned out to be wrong in a way that makes the design
> *simpler*, not harder (§5.5).

---

## 1. Precedent: what to take from where

Four cuneiform corpora exist in TF. They are not four implementations: Old Assyrian and
Old Babylonian share one converter (`Nino-cunei/tfFromAtf/programs/convert.py`), NinMed
is a later JSON→TF converter aligned to them, and Uruk is an older, structurally richer
design. All four are archived, so they are **design precedents, not code to vendor**.

| Corpus | Slots | Total nodes | Node types | Sections |
|---|---|---|---|---|
| Old Assyrian | 766,501 | 1,289,143 | sign, cluster, document, face, line, word | document / face / line |
| Old Babylonian | 203,219 | 334,667 | same | same |
| NinMed | 52,829 | 93,211 | same | same |
| Uruk | 140,094 | 263,067 | sign, quad, tablet, face, case, comment, column, cluster, line | tablet / column / line |

*(counts read from each repo's `otype.tf`)*

What each contributes:

* **Old Babylonian / Old Assyrian** — `sign` as slot type with `word` nodes over it; the
  reconstruction contract; cluster nodes **plus** induced per-sign boolean flags;
  a declarative `fixes.yaml` repair manifest.
* **NinMed** — occurrence-level lexical annotation (lemma sits on the word occurrence,
  not a shared lexeme node); per-type cluster state; and the discipline of **omitting
  Unicode** where the source does not support it.
* **Uruk** — the structural lesson that matters most here: `@levels` declares the full
  ontology (nine types) while `@sectionTypes` declares only three navigation levels, and
  genuine **edge features** (`sub`, `comments`, valued `op`) carry relationships that do
  not fit slot containment.
* **None of them** — TLHdig's multi-analysis `mrpN` morphology, mid-sign marker offsets,
  brackets running across lines, manuscript-witness joins, precomputed line-level
  cuneiform, or a century-deep editorial `<meta>` history. Those need a TLH-specific model.

So the design principle is **not** "follow oldbabylonian". It is: *Old Babylonian's sign
layer, Uruk's structural and relational graph, NinMed's occurrence-first annotation
discipline, adapted to AOxml source fidelity.*

### 1.1 Scale

TLHdig's **3,097,100 signs are 4.0× Old Assyrian**, the largest existing cuneiform TF
dataset, and the projected node total is **≈7.2M — 5.6× Old Assyrian's 1.29M**:

| | Projected |
|---|---|
| sign (slots) | 3,097,100 |
| analysis | 1,611,354 |
| word | 1,221,053 |
| line | 407,623 |
| cluster | ~400,000 |
| edit | ~180,000 |
| paragraph / colon / surface+column / fragment / document | 98,583 / 95,101 / ~41,600 / 28,787 / 23,713 |
| lex / note | 31,976 / 11,663 |

An earlier draft called 3.1M slots "large but unremarkable" and rated browser
sluggishness a low risk. Both were complacent: this would be the largest cuneiform TF
dataset by a wide margin. **Milestone 0 is a scale benchmark on a 5% shard** before the
ontology is frozen (§8).

---

## 2. The two contracts

The first draft claimed a single "lossless" guarantee and then quietly broke it by
dropping 403,169 contentless `<w>` elements. That was incoherent. There are two distinct
guarantees and they need separate mechanisms.

### 2.1 Contract A — byte-faithful source layer

**Guarantee:** the exact bytes of every source file are recoverable.

**Mechanism:** the original XML stays in the repository (`corpus/TLHdig-0.3/`), and every
node derived from a source span carries `src_file` plus a `src_span` byte range into it.

Byte offsets come from `xml.parsers.expat` (`CurrentByteIndex`), **not** from lxml —
lxml exposes `sourceline` only, not byte offsets. Structural interpretation still uses
lxml/ElementTree; the two run over the same bytes and are joined by offset.

> **Retraction.** An earlier draft claimed the tokeniser round-trips "99.99%
> byte-exact" and dismissed 9 failures as cosmetic. The experiment compared
> `ElementTree.tostring()` against a reassembly from *the same parsed tree*. It
> validated tokenisation, not byte-fidelity — parse-then-serialise is never
> byte-preserving (namespace prefixes, entity spelling, empty-element syntax, attribute
> quoting all drift), and the `ns0:` failures were that drift showing through. See
> research §8.3.

For the ~223 repaired files there are **two** identities and both are kept:
`src_span` indexes the *original* bytes; `repaired_span` indexes the repaired stream.
The round-trip target for a repaired file is its repaired form; the original remains
byte-recoverable from the corpus directory plus the patch manifest.

### 2.2 Contract B — content-lossless TF graph

**Guarantee:** every linguistic and editorial fact in AOxml is a queryable node, edge or
feature — nothing survives only as an opaque string.

This is the contract the TF dataset itself must satisfy, and §12 maps every source
construct to its destination.

Contentless `<w>` elements are covered under Contract A (byte spans) and, where they
carry layout information, by explicit **`layout` nodes** — not silently discarded. The
Nino corpora set the precedent for materialising empty structures: Old Babylonian
creates artificial slots for comment-only lines, NinMed emits `type="empty"` slots.
Whether TLH's 403,169 become slots or non-slot `layout` nodes is decided by the
Milestone 0 benchmark; the default is non-slot nodes, to keep "sign" meaning *sign*.

---

## 3. Target model

### 3.1 Slot type: `sign` — confirmed

All four precedent corpora independently use `sign`. The TLH case is stronger than
theirs: editorial boundaries fall *inside* signs (research §8.1) and cross word and line
boundaries (§8.2), which word-level slots cannot represent.

A sign is a maximal run of transliteration characters between `-` or `.` separators
within one wrapper context. Markers interrupting a sign stay inside it, at their exact
offset.

### 3.2 Node types

```
sign          slot type
word          layout        (contentless <w>, see §2.2)
analysis      cluster       note
colon         paragraph     line          column        surface
fragment      document      docgroup      edit          lex
```

### 3.3 `@levels` vs `@sectionTypes` — Uruk's lesson

An earlier draft worried that "TF allows only three section levels" and proposed a
custom section mechanism for `fragment`. That solved the wrong problem. Uruk declares:

```
@levels=tablet,face,column,line,case,cluster,quad,comment,sign
@sectionTypes=tablet,column,line
```

The full ontology lives in `@levels`; the three sections are only for **addressing**.
TLH follows suit:

```
@levels          = document,surface,column,paragraph,line,colon,word,sign
@sectionTypes    = document,column,line
@sectionFeatures = docid,collabel,lnno
```

`collabel` is a **globally unique level-2 label** built from fragment + surface + column
(`€1 Vs. II`), not the bare `surface="Vs."` the first draft declared. That draft's
advertised test `nodeFromSection(("KUB 21.8", "Vs. II", "5′"))` did not match its own
config: several columns can each hold a line `1′`, and in a composite tablet several
fragments can each have a `Vs.`. `collabel` fixes this.

`structureTypes` / `structureFeatures` expose the deeper hierarchy for browsing.

### 3.4 Morphology: `analysis` nodes, not `mrpalt` edges

> **Retraction.** The first draft linked every candidate analysis to a shared `lex` node
> with a valued `mrpalt` edge. **That cannot work.** `CV.edge()` performs
> `edgeFeatures[k][nodeFrom][nodeTo] = v` — a plain dict assignment (verified in TF
> 13.1.0 `tf/convert/walker.py:1030`). Two analyses of one word that resolve to the same
> lexeme collapse onto one `(from, to)` pair and the later value silently overwrites the
> earlier. The design would have lost analyses while claiming to preserve them.

Each `mrpN` becomes an **`analysis` node** covering the same slots as its word:

```
word ──analyses──> analysis (index=0|1|2|…, lemma, gloss, morph, stemclass, pos, det,
                             clitic_lemma, clitic_morph, clitic_stemclass, clitic_det,
                             raw, sep, parse_ok)
     ──selected──> analysis        the one mrp0sel points at, when it points at one
```

**`index` is read from the attribute name and never reassigned.** The index space starts
at **0** — `mrp0` is a real analysis slot on 201 words, and `mrp0sel="??? 0a"` resolves
against it — numbering has gaps on 292 words, and 19,081 words do not start at `mrp1`
(research §4.1.1). Enumerating analyses positionally would silently break every selector
on those words.

`analysis ──lexeme──> lex` is an optional derived layer. This matches NinMed, which
keeps lemmas on the word occurrence and has no shared lexeme ontology at all.

**`lex` is keyed on `(lemma, gloss)` = 31,976 nodes.** The first draft said "32,055
nodes" but keyed on `(lemma, gloss, stemclass, det)`, which measures **38,941** — a 22%
undercount of its own design. Stem class and determinative vary between analyses of one
lexeme, so they belong on `analysis`, not on `lex`. That also keeps `lex` meaning what it
means in BHSA: a lexeme, not a bundle of occurrence-specific fields.

### 3.5 Text formats

> **Retraction.** The first draft declared `@fmt:text-orig-unicode={cu}` with `cu` on
> `line` nodes and claimed it "renders at line granularity". It would have rendered
> nothing. TF's `Text.splitFormat` (verified, `tf/core/text.py:1218`) sets
> `descendType = slotType` unless the template contains `nodetype#`, so `{cu}` fetches
> `cu` from every **sign**, where it does not exist.

```
@fmt:text-source     = {srcxml}{after}      source-faithful, markers in place
@fmt:text-plain      = {sym}{after}         clean transliteration
@fmt:text-trans-full = {srcxml}{after}      alias for citation
@fmt:line#text-cuneiform = {cu}\n           line-level Unicode, correct target syntax
@fmt:lex-default     = {lemma} '{gloss}'
```

Rich rendering — raised determinatives, Sumerogram caps, Akkadogram italics, bracket
styling, the cuneiform/transliteration parallel view — belongs in **app renderers**, not
in a `symr` feature. Old Babylonian does exactly this with `fmt_layoutRich()` /
`fmt_layoutUnicode()` exposed as `layout-*` views. The graph stores facts
(`det=1`, `sgr=1`, `missing=1`, `corr=?`); the app decides they mean superscript,
capitals, grey brackets, a tooltip.

**No sign-level `symu` is invented.** TLHdig has no sign-aligned cuneiform (research
§6.2) and NinMed sets the precedent that a cuneiform TF dataset may simply omit Unicode
rather than fabricate it. If alignment later succeeds it arrives as
`sign.cu_aligned` + `cu_alignment_status` + `cu_alignment_confidence`.

---

## 4. Feature catalogue

### 4.1 `sign`

> **Naming correction.** The first draft called the source-faithful sign string `atf`.
> In the Nino corpora `atf` means something specific and different — the ATF of a sign
> **without** cluster brackets, which live in `atfpre`/`atfpost`, such that
> `atfpre + atf + atfpost + after` reproduces the source. TLH's string is XML-derived
> with inline markers at arbitrary intra-sign offsets. Reusing the name would mislead
> anyone arriving from those corpora. It is now **`srcxml`**.

| Feature | Notes |
|---|---|
| `srcxml` | exact source-derived sign fragment, markers at their true offsets |
| `sym` | clean reading, markers stripped |
| `after` | separator to the next sign (`-`, `.`, ` `, ``) |
| `src_span` | byte range into `src_file` (Contract A) |
| `type` | `reading` \| `signname` \| `numeral` \| `unknown` \| `ellipsis` \| `empty` |
| `sgr` `agr` `det` `num` (int) | writing-system flags — **orthogonal to `type`** |
| `missing` `laesio` `rasura` `added` `quoted` (int) | induced from cluster membership |
| `corr` | `?`, `!`, `sic`, … verbatim |
| `subscr` | epigraphically subscripted sign (research §3.5) |
| `materlect` | mater lectionis / explanatory sign |
| `materlect_anomalous` (int) | the 65 instances holding a bare `!`/`?` |
| `surplus` | excised superfluous sign |
| `space_count` (int) | count of U+0020 (ODF `text:s/@text:c`); unitless |
| `lang` | inherited from line, overridden by word |

The `type` split follows Nino: `type` is the **kind of token**, while determinative,
Sumerogram and Akkadogram are orthogonal flags. The first draft folded
`sumerogram`/`akkadogram`/`determinative` into `type` while *also* carrying
`sgr`/`agr`/`det`, making "this is a Sumerogram" wrongly exclusive of "this is an
identifiable reading".

### 4.2 `analysis`

`index` (int) · `raw` · `sep` · `parse_ok` (int) · `lemma` · `gloss` · `morph` ·
`stemclass` · `stemclass_raw` · `field4_kind` (`stemclass`\|`pos`\|`morph`) · `pos` ·
`det` · `clitic_lemma` · `clitic_morph` · **`clitic_stemclass`** · `clitic_det` ·
`alt_map` (the `{a → X}` set as escaped JSON).

`clitic_stemclass` was missing from the first draft despite the research grammar
describing it.

### 4.3 `word`

`trans` · `srcxml` · `src_span` · `mrpsel` · `mrpsel_kind`
(`analysis`\|`DEL`\|`AKK`\|`HURR`\|`HAT`\|`SUM`\|`LUW`\|`unknown`\|`none`) ·
**`sel_base`** (base alternative letter) · **`sel_clitic`** (clitic alternative letter) ·
`sel_group` (`all`\|`sg`\|`pl`) · `nanalyses` (int) · `lang` · `editingquestion`.

The first draft had one `mrpsel_alt` string; `aR` needs two independent selectors.

### 4.4 `cluster`

`type` (`del`\|`laes`\|`ras`\|`add`\|`quot`) · `start_sign` · `start_offset` (int) ·
`end_sign` · `end_offset` (int) · `crossesword` · `crossesline` · `orphan`
(`open`\|`close`\|`none`) · `pair_confidence`.

Character offsets live on the cluster because TLH brackets cut signs mid-way; the
first draft's scalar `damage=initial|medial|final` cannot distinguish two same-type
ranges touching one sign, and throws away the exact position.

### 4.5 `line`, `column`, `surface`, `fragment`

`line`: `lnr` (raw) · `lnno` · `ln` (int) · `prime` · `linetail` · `txtid` · `lang` ·
`cu` · `cudirty` · `cu_pua` (int) · `cu_pua_unmapped` (int) · `cu_broken` (int) ·
`src_span`.
`column`: `column` · `collabel` (unique). `surface`: `surface`.
`fragment`: `frag` · `txtpubl` · `invnr`.

### 4.6 `edit` — the editorial history as nodes

The first draft flattened `<meta>` to newline-joined `editor|date|part` strings, dropping
`src`, `frgm`, `docs`, `comment` and the `neu` wrapper nesting — while claiming the "full
editorial edit log" survived. It did not. Following Uruk's comment-node pattern, each
`<meta>` event becomes an `edit` node:

`kind` (`kor`\|`kor2`\|`kor1kf`\|`annot`\|`uebern`\|`format`\|`join`\|`merge`\|…) ·
`editor` · `date` · `part` · `src` · `frgm` · `docs` · `comment` · `order` (int) ·
`rawxml`, linked by an `edits` edge to its target.

### 4.7 `document`, `docgroup`

`document`: `docid` · `docid_raw` · `cth` · `cth_alt` · `cth_neu` · `subcorpus` ·
`src_file` · `lang` (**omitted when `XXXlang`**) · `lang_raw` · `wellformed` (int) ·
`repaired` (int) · `repairnote` · `nfragments` (int).

`docgroup`: one node per distinct `docid`, grouping the records that claim the same
manuscript identity — `docid` · `nrecords` (int) · `n_identical` (int). This expresses
"these claim the same tablet" without asserting the editions are equivalent. Note that
the shared Nino converter treats a duplicate P-number as an *error* and skips the second
document; that behaviour must **not** be copied — TLH's 114 differing duplicates are
largely legitimate (research §3.1).

---

## 5. Edges

| Edge | From → To | Valued | Purpose |
|---|---|---|---|
| `oslots` | non-slot → sign | no | warp |
| `analyses` | `word` → `analysis` | no | all candidate analyses |
| `selected` | `word` → `analysis` | yes (`sel_base`/`sel_clitic`) | the chosen one, when chosen |
| `lexeme` | `analysis` → `lex` | no | derived lexical layer |
| `witness` | `line`/`surface` → `fragment` | no | **many-to-many** — see §5.1 |
| `joins` | `fragment` → `fragment` | yes (`direct`\|`indirect`) | join history |
| `edits` | `edit` → `document`/`fragment` | no | editorial events |
| `noteref` | `note` → `sign` | no | footnote anchor |
| `edition` | `document` → `docgroup` | no | same-manuscript grouping |

### 5.1 Why `witness` is an edge, not containment

The first draft required every surface to sit inside exactly one `fragment`. That
contradicts the corpus: `lnr` values include `€1+2`, `€2+3` — a line concerning several
constituent witnesses at once. Containment cannot express that. Uruk's precedent is
explicit: not every relationship goes through `oslots`. So the physical hierarchy is

```
document → surface → column → line
```

and fragment/witness membership is a separate many-to-many edge.

---

## 6. Damage brackets: what the corpus actually is

This is where measurement most changed the design.

**The first draft assumed a matched-bracket language and specified a single
document-scoped stack. Both halves were wrong.** Measured over the whole corpus:

| | |
|---|---|
| `del_in` / `del_fin` elements | 436,674 / 388,323 |
| opens never closed (document scope) | 107,221 |
| closes with no open (document scope) | 58,648 |
| crossing pairs (`del_in laes_in del_fin laes_fin`) | 248 |
| `del_fin` closes resolving within their own line | **71.9%** |

A single LIFO stack cannot pair crossing families at all, and document-scoped counting
produces absurd artefacts — a naive depth counter reaches **148** for `del` in one
document, which is not 148 nested lacunae but accumulated unmatched opens.

The decisive measurement is nesting **within a line**:

| Family | depth 0 | depth 1 | depth ≥2 |
|---|---|---|---|
| `del` | 25.28% | 74.65% | **0.06%** (253 of 431,336 lines) |
| `laes` | 73.16% | 26.81% | 0.03% |
| `ras` | 98.67% | 1.33% | 0.004% |
| `add` | 99.94% | 0.05% | 0.006% |

**Within a line, these brackets essentially never nest.** So the model is simpler than
either review proposed — no stack is needed:

* per-family **open/closed state**, scoped to the line;
* a `del_fin` closes the open `del` if one is active in this line, else it is an
  **orphan close** — recorded as a boundary marker, never back-projected into an
  invented span;
* a line ending with an open family emits an **orphan open**; the next line may continue
  it, and the resulting cluster is flagged `crossesline` with reduced `pair_confidence`;
* depth ≥2 within a line (≈400 cases total) is flagged as a probable encoding error, not
  silently modelled as nesting.

Nino-cunei's rule — per-type state, reset at line end — is right in shape; TLH differs
in that breaks legitimately continue across lines, so state persists but each crossing is
marked rather than assumed.

Dual representation is copied wholesale from Old Babylonian: the **cluster node is
authoritative** for the span, and every sign inside also gets a cheap boolean
(`missing=1`, `laesio=1`, …) so `F.missing.s(1)` works without touching clusters.

---

## 7. Pipeline

### 7.0 Environment — pinned

TF is not installed here (Python 3.7.12 default; 3.11/3.13 available; no `tf`, no
`lxml`). A derived scholarly corpus must rebuild deterministically, so versions are
pinned, not resolved on the day:

```
python == 3.13
text-fabric == 13.1.0     # requires_python >=3.9
lxml == 5.x               # structure only; byte offsets come from expat
```

### 7.1 Inventory
Walk the tree; record path, size, SHA-256, CTH, sub-corpus, parse status →
`reports/inventory.tsv`.

### 7.2 Repair — a patch manifest, not regexes

The first draft guarded repairs with "each regex must match exactly once". That is weak:
a wrong pattern can match exactly once and corrupt the wrong bytes. Beta 0.3 is immutable
and only ~223 files need changes, so repairs are a **declarative manifest** keyed by
content hash, following Old Assyrian's `fixes.yaml` but stricter:

```yaml
- path:   "CTH 209_XML_TLH/KBo 12.55.xml"
  sha256: "…"
  old:    '<kap c-"Te%t pricḫt ap"'
  new:    '<gap c="Text bricht ab"/>'
  reason: "corrupted find-replace; not a philological change"
```

Assertions per patch: file hash matches; `old` occurs exactly once; exactly one byte
range changes; the result parses. A patch that fails any assertion aborts the build.

**Scope limit.** Old Assyrian's `fixes.yaml` mixes parser repairs with philological
normalisation (`'01' → '1'`, leading-zero removal). TLH's manifest is restricted to
**syntactic corruption only**. The converter must not become an uncredited critical
edition.

`CTH 813_XML_TLH/KUB 37.25.xml` is encrypted and cannot be repaired; it is excluded and
reported (research §9.1).

### 7.3 Normalisation
Trim `mrp0sel` padding. Leave dirty values verbatim; flag in `reports/dirty-values.tsv`.
`xml:lang="XXXlang"` → omit `lang`, keep `lang_raw`; never map to `ign`, which is
TLHdig's positive marker for unknown language.

### 7.4 Tokenisation
Dual-parse: expat for byte offsets, lxml for structure, joined by offset. `<lb>` opens a
line; a change of surface/column/fragment opens the corresponding node; `<parsep>`
**closes** a paragraph; `<clb>` delimits colons. Bracket handling per §6.

### 7.5 Morphology

> **Correction.** The first draft's snippet was
> `base = segs[0].rstrip("@").split("@")`. Measured against the corpus, that
> **damages 794,637 values** — the majority of no-clitic analyses, which legitimately
> end in `@` because the determinative field is empty. `rstrip` deletes that field.

Separator handling must recognise all four forms (research §4.1). Locate the separator,
noting whether the character before it is `@` — that `@` is the base's field terminator,
not an empty field:

```python
m = re.search(r"(@?)\s*\+=?\s*", raw)          # first separator only
if m and m.group(0).strip():
    base_s, clit_s = raw[:m.start()], raw[m.end():]
    if m.group(1) == "@":
        pass                                    # the '@' is already excluded
else:
    base_s, clit_s = raw, None
base = base_s.split("@")                        # never rstrip
```

Attribute scan is `re.fullmatch(r"mrp\d+", k)` — which includes `mrp0`; only `mrp0sel`
is excluded. Field counts are asserted exhaustively over all 1,611,354 analyses; anything unexpected
is left unparsed with `parse_ok=0`, never truncated. Field 4 is disambiguated by the
**closed category vocabulary** (leading whitespace is a consistency check only — 65
values occur both ways). `Nsg`/`Npl` are validated against the referenced analysis;
`sel_base` and `sel_clitic` are stored separately.

### 7.6 Cuneiform
`cu` on `line` verbatim with `cu_pua` / `cu_pua_unmapped` / `cu_broken`. PUA table seeded
with `U+100000` = SI×SÁ (HZL 28); `U+100009` left unidentified. Format is
`line#text-cuneiform`, never a sign-level template.

### 7.7 Build
`tf.convert.walker.CV`. Non-hierarchical nodes (`lex`, `docgroup`) use
`cv.node(type, slots=…)`, which exists for exactly this.

### 7.8 Validate → §8.  7.9 Package → §9.

---

## 8. Validation

### 8.0 Milestone 0 — benchmark before freezing the ontology
Build a 5% shard (~155k signs, ~360k nodes), measure load time, memory and TF-browser
responsiveness, and decide from data whether the 403,169 contentless `<w>` become slots
or non-slot `layout` nodes.

### 8.1 Contract A — byte fidelity
For every document: slicing `src_span` out of the original bytes and concatenating in
node order must reproduce the file exactly. For repaired files the target is the
repaired stream, with the original recoverable via the patch manifest.

### 8.2 Contract B — content completeness
Every source construct in the §12 table resolves to at least one node/edge/feature.
Zero analyses lost: `count(analysis) == 1,611,354` — note this includes the 201 `mrp0`
attributes; the figure 1,611,153 quoted elsewhere counts `mrp1`…`mrp99` only.

### 8.3 Census, not stale constants

> **Correction.** The first draft pinned invariants to the research counts (407,623
> lines, 1,221,053 words, …) while *also* repairing 223 files into the build. Those
> counts come from the 23,713 already-parseable files; the repaired files contribute
> more lines and words, so the invariants were guaranteed to fail. Its arithmetic
> "23,713 (+ repaired) (− 1 excluded)" was also confused — the excluded file is one of
> the 224, not one of the 23,713.

The repair stage emits `reports/census.tsv` — the canonical post-repair counts — and
validation pins against **that**. The research figures become a *lower bound* check:
post-repair counts must be ≥ the 23,713-file figures and the delta must be attributable
to named repaired files.

### 8.4 Structural checks
`collabel` unique within a document. Every line in exactly one column; every column in
one surface; every surface in one document. Witness membership may be many-to-many.
`T.nodeFromSection(("KUB 21.8", "€1 Vs. II", "5′"))` round-trips.

### 8.5 Spot panel
~30 documents covering: simple Hittite text; composite `€1+€2+€3`; Akkadian; Hurrian;
`clb` colon segmentation; heavy footnoting; a repaired file; a duplicate-`docID` pair;
a line with `del` crossing into the next. Rendered in every format and diffed by eye.

---

## 9. Deliverables and versioning

Source version and schema version are **separate**, following Nino practice — otherwise a
converter fix would masquerade as an upstream TLHdig release:

```
sourceVersion = 0.3        # TLHdig Beta 0.3
tfVersion     = 0.1.0      # this ontology + converter
```

```
programs/        convert.py, patches.yaml, checks.ipynb
tf/0.1.0/        generated features
app/             config.yaml + layout-rich / layout-cuneiform renderers
docs/features.md generated from featureMeta
reports/         inventory, census, patches, dirty values, validation
```

---

## 10. Sequencing

The first code written is **not** the converter. Four executable prototypes retire the
remaining risk first:

| # | Prototype | Retires |
|---|---|---|
| 0 | 5% shard scale benchmark | node-count risk (§1.1, §8.0) |
| 1 | expat byte-slice round-trip on 1,000 files | Contract A (§2.1) |
| 2 | `mrpN → analysis` over ~50k hard words | separator + field-4 + selector risk (§7.5) |
| 3 | line-scoped bracket pairing over the full corpus | orphan/crossing statistics (§6) |
| 4 | miniature TF dataset: composite fragments, duplicate `collabel`s, `line#{cu}` | config correctness (§3.3, §3.5) |

Then: inventory → repair → tokenise → morphology → build → validate → app → deposit.

---

## 11. Open questions

Unchanged from revision 2 — five upstream items, none blocking: `Nsg`/`Npl` semantics;
formal confirmation of upper-case clitic selectors; the identity of `U+100009`; whether
an internal sign-aligned `@cu` exists; an explicit AOxml definition of `space/@c`.

To **report** rather than ask: the encrypted `KUB 37.25.xml`, and the 65 `<materlect>`
elements carrying `!`/`?`.

---

## 12. Preservation map

| Source construct | Destination |
|---|---|
| exact file bytes | `src_file` + `src_span` (Contract A) |
| word markup with mid-sign markers | `sign.srcxml` + `after` |
| all 1,611,153 analyses | `analysis` nodes + `analyses` edges |
| `mrp0sel` incl. `DEL`/`AKK`/`???` | `word.mrpsel*`, `selected` edge |
| line references | `line.lnr` + parsed parts; `collabel` for addressing |
| manuscript witnesses & joins | `fragment` nodes, `witness` + `joins` edges |
| editorial `<meta>` history | `edit` nodes + `edits` edges |
| damage / laesio / rasura extents | `cluster` nodes with offsets + induced sign flags |
| line cuneiform incl. `▒`, PUA | `line.cu`, `cu_pua`, `cu_pua_unmapped`, `cu_broken` |
| footnotes | `note` nodes + `noteref` edges |
| contentless `<w>` | `layout` nodes + `src_span` |
| language at 3 levels | `document.lang`/`lang_raw`, `line.lang`, `sign.lang` |
| same-tablet re-editions | `docgroup` + `edition` edges |
| provenance | `document.src_file`, `cth`, `cth_alt`, `cth_neu`, `subcorpus` |

Where upstream documentation settles a meaning, the derived feature carries it **and**
the raw value. Where it does not (§11), only the raw value is authoritative, the derived
feature is marked provisional in `docs/features.md`, and a `*_raw` companion guarantees
an upstream answer can be applied by re-deriving rather than reconverting.
