# TLHdig → Text-Fabric: Corpus & Format Research

**Status:** research complete. Findings below are measured against the corpus on disk;
where upstream documentation exists it is cited and reconciled with the measurements.
**Date:** 2026-08-28 (revised after a second pass against HPM/HFR/SimTex documentation)

> **Revision note.** A follow-up review of the public TLHdig/SimTex documentation, the
> HFR authoring and annotation manuals and the HPM cuneiform-font material resolved
> most of what this document originally listed as undocumented. Sections 3.5, 4.1, 4.2,
> 6 and 9 have been revised accordingly, and every new claim was re-verified against the
> corpus. Two of my own earlier statements were **wrong** and are corrected in place:
> the `mrp` clitic separator has four surface forms, not two (§4.1), and the
> leading-space POS discriminator is unreliable (§4.1). Both are flagged inline.
**Corpus root:** `/Users/alexandersosnovschenko/projects/TLHbasisONLINE25_1_ZENODO_Beta_03`

Companion document: [TF-CONVERSION-PLAN.md](TF-CONVERSION-PLAN.md)

---

## 1. Provenance and identification of the data on disk

The directory is an unpacked Zenodo release of the **Thesaurus Linguarum Hethaeorum
digitalis (TLHdig)**, part of the Hethitologie-Portal Mainz (HPM).

| | |
|---|---|
| Dataset | Thesaurus Linguarum Hethaeorum digitalis (TLHdig), **Beta Version 0.3** |
| DOI (this version) | `10.5281/zenodo.20328284` |
| Concept DOI (all versions) | `10.5281/zenodo.15459133` |
| Zenodo publication date | 2026-05-21 |
| Zip on Zenodo | `TLHbasisONLINE25_1_ZENODO_Beta_03.zip` (74,449,198 bytes) |
| Creators | Müller, Gerfrid; Prechel, Doris; Rieken, Elisabeth; Schwemer, Daniel |
| Licence | CC-BY-4.0 |
| Project home | <https://www.hethport.uni-wuerzburg.de/TLHdig/> |

**Version note.** The Zenodo record linked during this work,
<https://zenodo.org/records/15459134>, is **Beta 0.2** (`10.5281/zenodo.15459134`,
published 2025-03-07). That is *not* what is on disk. The local tree is Beta 0.3: the
directory name matches the 0.3 zip exactly, and the internal `AOxml-creation`
timestamps run to **2026-05-06**, well past the 0.2 cut-off. Beta 0.2 is marked
deprecated by the depositors. The conversion should cite the 0.3 DOI for the data and
the concept DOI for the corpus as such.

Per the depositors, TLHdig aggregates transliterations produced over a century of
Hittitological scholarship; it is explicitly *not* a critical edition, and
"the epigraphical and philological quality of the data ... is uneven and under
constant development". That has direct consequences for the conversion — see §9.

---

## 2. The corpus at a glance

All figures below were produced by walking the full tree.

| Measure | Value |
|---|---|
| Total size on disk | 380 MB |
| XML files | **23,937** |
| — parse cleanly with a standard XML parser | **23,713** |
| — malformed (see §9.1) | **224** |
| Top-level directories | 829 (all `CTH <number>_XML_<subcorpus>`) |
| Non-XML files | 184 × `HPMxml.css`, 5 × `.odt`, 2 × `.webarchive`, 2 × `.log`, 1 × `.ods`, 1 × `TLHdig.html`, 1 extension-less stray, 564 × `.DS_Store` |

Derived object counts (from the 23,713 parseable files), i.e. the projected size of the
Text-Fabric graph:

| Textual object | Count |
|---|---|
| documents | 23,713 |
| manuscript fragments (distinct `{€n}` sigla per document) | 28,787 |
| surfaces/columns (distinct obverse/reverse/column per fragment) | 41,627 |
| lines (`<lb>`) | 407,623 |
| paragraphs (delimited by `<parsep>` rulings) | 98,583 |
| colons / clause units (`<clb>`) | 95,101 |
| **words** (`<w>` with actual text content) | **1,221,053** |
| **signs** (words split on `-` / `.`) | **≈3,097,100** |
| distinct lemmata (mrp field 1) | 28,091 |
| distinct German glosses (mrp field 2) | 8,531 |
| distinct lemma+gloss pairs | 32,055 |
| morphological analyses (`mrp1`…`mrp99`) | 1,611,153 |

`<w>` elements total 1,624,920, but **403,169 of them carry no text at all** — they are
containers for layout and damage markers only (`<space/>`, a lone `<del_in/>`, …). Only
1,221,053 are real words; of those, 914,243 carry a `@trans` transliteration attribute
and morphological analysis, and 306,806 have text but no `@trans` (typically
unanalysed or non-Hittite stretches). Any converter that treats every `<w>` as a word
will over-count by 33%.

### 2.1 Sub-corpora

The directory suffix encodes the HPM sub-project a text belongs to. Documents per
sub-corpus:

| Suffix | Documents | Sub-project |
|---|---|---|
| `TLH` | 11,146 | TLHdig base layer |
| `HFR` | 8,286 | Hethitische Festrituale |
| `BESRIT` | 1,025 | Beschwörungsrituale |
| `HDivT` | 811 | Hethitische Divinationstexte |
| `HAnn` | 694 | Hethitische Annalen |
| `KULTINV` | 426 | Kultinventare |
| `MYTH` | 415 | Mythologische Texte |
| `PTAC` | 245 | Palaeography / tablet collections |
| `GEBET` | 195 | Gebete (prayers) |
| `ARINNA` | 175 | Arinna corpus |
| `luw` / `LUWGR` | 131 / 37 | Luwian material |
| `SVH` | 127 | Staatsverträge (treaties) |

Sub-corpus labels are read from the *directory name*, not from inside the files. They
are worth preserving as a document feature: they are the only signal of editorial
provenance and annotation depth, and annotation quality differs markedly between them.

### 2.2 CTH numbering

`CTH` = *Catalogue des Textes Hittites*. Directory numbers run 1–834 plus a catch-all
`CTH 999`. A few directories nest one level deeper (e.g.
`CTH 670_XML_HFR/CTH 670-2351-2375/`) to shard very large CTH groups.

The same CTH number can appear under several sub-corpus suffixes (e.g. CTH 212 exists as
`_HAnn`, `_SVH` and `_TLH`), so **CTH number alone is not a partition of the corpus**.

---

## 3. Source format: HPM "AOxml"

Every text file is an `AOxml` document in the HPM namespace family:

```
xmlns:hpm   = http://hethiter.net/ns/hpm/1.0
xmlns:AO    = http://hethiter.net/ns/AO/1.0
xmlns:dc    = http://purl.org/dc/elements/1.1/
xmlns:meta  = urn:oasis:names:tc:opendocument:xmlns:meta:1.0
xmlns:text  = urn:oasis:names:tc:opendocument:xmlns:text:1.0
xmlns:table = urn:oasis:names:tc:opendocument:xmlns:table:1.0
xmlns:draw  = urn:oasis:names:tc:opendocument:xmlns:drawing:1.0
xmlns:xlink = http://www.w3.org/1999/xlink
xml:space   = preserve
```

The OpenDocument namespaces are residue: the pipeline that produced these files
converts from ODT, and a handful of ODF elements (`text:tab`, `text:h`,
`text:line-break`, `text:bookmark`) and ODF paragraph-style names (`P___Standard`,
`P___Footnote`, `SP___Page_20_Number`) leak into the output. **`xml:space="preserve"` is
significant** — whitespace between `<w>` elements is part of the encoding.

### 3.1 Document skeleton

```xml
<AOxml …>
  <AOHeader>
    <docID>KUB 21.8</docID>
    <meta>
      <creation-date date="2024-12-30T23:01:04.691000000"/>
      <kor2 date="2025-01-31T22:33:48"/>
      <AOxml-creation date="2025-01-31T22:33:48"/>
      <annotation> <annot editor="auto" date=""/> … </annotation>
    </meta>
  </AOHeader>
  <body>
    <div1 type="transliteration">
      <text xml:lang="Hit">
        <AO:Manuscripts><AO:TxtPubl>KUB 21.8</AO:TxtPubl></AO:Manuscripts>
        <lb txtid="KUB 21.8" lnr="Vs. II 1′" lg="Hit" cu="𒁹𒄯𒅆𒀭𒅆𒅖"/>
        <w><space c="74"/></w>
        <w trans="…" mrp0sel=" 1 " mrp1="…">…</w>
        …
      </text>
    </div1>
  </body>
</AOxml>
```

`div1/@type` is always `transliteration`. `<text>/@xml:lang` gives the document's main
language: `Hit` 17,937 · `XXXlang` 4,520 · `Akk` 850 · `Hat` 242 ·
`Luw` 99 · `Pal` 25 · `Hur` 8 · `Sum` 3, plus 29 dirty values (`''`, `Hitt`, `30lang`).

**`XXXlang` means *unset*, not a language.** Confirmed three ways: the TLHdig input
documentation has the main language chosen in the submission pipeline from a finite set
of real markers; the Zenodo 0.3 record declares the dataset language as `hit` only, with
no `XXXlang`; and TLHdig has a *separate*, documented marker `@Ign` for a passage whose
language is genuinely unknown (`ign` appears 75 times in `lb/@lg`). `XXXlang` and `ign`
must therefore not be conflated — the first is a missing value, the second is a positive
assertion of ignorance.

`<docID>` equals the filename stem in 23,584 of 23,713 files; 129 disagree.
There are **23,568 distinct docIDs**, so 136 docIDs occur in more than one file —
and in only 22 of those cases is the body byte-identical. The remaining 114 are
different transliterations of the same tablet, filed under different CTH numbers or
sub-corpora. **`docID` is therefore not a primary key**; the file path is.

**Why the duplicates are mostly legitimate.** `docID` is *manuscript / publication*
identity, not *record* identity. A Hittite `Sammeltafel` (collective tablet) can belong
to several CTH classes at once: `KUB 26.71`, which appears here under `CTH 1_XML_HAnn`,
`CTH 18_XML_HAnn` and `CTH 999_XML_TLH/HAnn`, is recorded by the official HPM
concordance as belonging simultaneously to CTH 1, CTH 18 and CTH 39.6. So the same
physical manuscript legitimately enters several corpus contexts, each edited within its
own sub-project. Deduplicating on `docID` would destroy real distinctions.

That said, this does **not** license the blanket claim that all 114 are deliberate.
TLHdig is a living collaborative repository assembled from several editorial
subprojects, so stale accidental copies may sit among them. The conversion keeps every
record and links them; it does not adjudicate which are intentional (§9 of the plan).

### 3.2 Editorial history: `<meta>`

`<meta>` carries a stack of provenance/edit-log elements. Each has `@editor` and
`@date`, some also `@part`, `@src`, `@frgm`, `@docs`, `@comment`:

| Element | Count | Reading |
|---|---|---|
| `creation-date` | 23,725 | record creation |
| `AOxml-creation` | 23,449 | AOxml serialisation timestamp |
| `annotation` / `annot` | 23,499 / 58,372 | annotation passes; `@editor` = `auto` (23,398) or initials/full names (36 distinct) |
| `kor2` | 30,699 | second correction pass |
| `neu` | 7,482 | wrapper grouping "new" edit events |
| `kor1kf` | 7,508 | first correction, *Kurzform* |
| `kor` | 7,266 | correction |
| `uebern` | 7,037 | *übernommen* — taken over from source `@src` (334 distinct sources) |
| `format` | 5,834 | formatting pass |
| `subscr` (in meta) | — | see §3.5 |
| `kolon` | 1,095 | colon segmentation pass |
| `val` | 1,071 | validation |
| `trlst` | 1,057 | transliteration pass |
| `author` | 919 | `@author` (9 distinct: Oğuz Soysal 569, TurnaSomel 211, Daniel Schwemer 110, …) |
| `cth` | 839 | CTH re-classification: `@alt` (old number) → `@neu` (new number) |
| `join`, `merge`, `merged`/`doc`/`mDocID`, `aufheb`, `aufloes`, `korof`, `koltaf`, `kolfot`, `kolfot2` | 307 / 73 / 149 / 192 / 66 / 170 / 92 / 25 / 249 | join & merge history of fragments |

This is a complete, dated, attributed edit log — the kind of thing that is normally lost
in conversion and is worth carrying over verbatim.

### 3.3 Manuscript block: `<AO:Manuscripts>`

Present in 23,770 `<text>` elements. Children:

| Child | Count | Content |
|---|---|---|
| `AO:TxtPubl` | 23,717 | publication siglum, e.g. `KUB 21.8`; `@nr` holds a fragment siglum `€1`…`€34` |
| `AO:InvNr` | 2,857 | excavation/inventory number, e.g. `Bo 7238` |
| `AO:DirectJoin` | 1,060 | direct joins |
| `AO:InDirectJoin` | 166 | indirect joins |
| `AO:TextPubl`, `AO:CTH-Nr`, `AO:ExcNr` | 16 / 10 / 3 | rare variants |

A composite text lists each constituent manuscript with its `€n` siglum, e.g.

```
KBo 53.304 {€3} + KBo 3.38 {€1} + CHDS 3.169 {€2}
```

and lines then reference those sigla in `lb/@lnr` (§5). This is the corpus's
manuscript-witness layer and is fully recoverable.

### 3.4 The text stream: milestones, not containers

Inside `<text>` almost everything is **flat**. Lines, paragraphs and colons are
*milestone* elements with no content; the objects they delimit have to be reconstructed
by scanning:

| Element | Count | Role |
|---|---|---|
| `<lb …/>` | 407,623 | **start** of a line |
| `<parsep/>` | 71,893 | paragraph ruling — measured to follow the last `<w>` of a line (13,833/14,596) and to precede the next `<lb>` (13,483/14,596), so it **closes** a paragraph |
| `<parsep_dbl/>` | 3,055 | double ruling |
| `<tabsep/>` | 3,872 | tabular column separator |
| `<clb …/>` | 95,101 | colon (clause) boundary, `@id` sequential per document, optional `@nr`, optional `@lg` |
| `<gap …/>` | 52,594 | break; `@t="line"` on 32,616, `@c` holds a German/English caption such as `Rs. III bricht ab` |
| `<AO:ParagrNr c="§ 1′"/>` | 2,951 | printed paragraph number; 244 distinct values, incl. `Kolophon` (771) |

Colon segmentation is **partial**: only **4,305 of 23,713 documents** (18%) carry
`<clb>` markers. It must be an optional node type, not a required layer.

### 3.5 Word-internal markup

`<w>` mixes text with three kinds of child element.

**(a) Typed wrappers** — enclose a span of characters and change its writing system:

| Element | Count | Meaning |
|---|---|---|
| `<sGr>` | 324,061 | Sumerogram (logogram), conventionally set in caps |
| `<aGr>` | 127,731 | Akkadogram, conventionally set in small caps/italics |
| `<d>` | 186,209 | determinative (semantic classifier), set superscript |
| `<num>` | 57,209 | numeral |
| `<c type="sign">` | 5,463 | sign given by *name* rather than reading, e.g. `<c type="sign">UD</c>` |

**(b) Range markers** — paired empty elements that open and close an editorial bracket:

| Pair | Counts | Convention |
|---|---|---|
| `del_in` / `del_fin` | 436,674 / 388,323 | `[ ]` lacuna — text destroyed and restored |
| `laes_in` / `laes_fin` | 141,301 / 141,107 | `⸢ ⸣` damaged but legible |
| `ras_in` / `ras_fin` (+ `ras_X` 42) | 6,120 / 6,094 | *Rasur* — erasure |
| `add_in` / `add_fin` | 291 / 289 | editorial addition `⟨ ⟩` |
| `QUOT_HurInHit_in` / `_fin` | 48 / 48 | Hurrian quoted inside Hittite |

**(c) Point markers** — single empty elements at an exact character position:

| Element | Count | `@c` values / meaning |
|---|---|---|
| `<corr c="…"/>` | 63,770 | philological mark: `?` 49,378 · `(?)` 6,361 · `!` 6,049 · `!?` · `sic` … (53 distinct) |
| `<space c="N"/>` | 201,095 | **count of U+0020 SPACE characters** (see below); 18,416 immediately after `<lb>` (line indent), 15,773 mid-line |
| `<note n="…" c="…"/>` | 11,663 | footnote; `@c` holds XML-escaped rich text, `@n` the footnote number |
| `<subscr c="…"/>` | 4,982 | an **epigraphically subscripted sign** attached to the preceding sign (`a` 2,568, `u`, `e`, `i`, `ú`, `pí`, …) |
| `<materlect c="…"/>` | 314 | **mater lectionis / explanatory additional sign** (`uḫ`, `an`, `aḫ`, `ar`/`ru`, …) |
| `<surpl c="…"/>` | 107 | superfluous sign written by the scribe, excised by the editor; the sign is in `@c`, not in text |
| `<wsep c="…"/>` | 9 | explicit word separator (`𒀹`, `𒑱`) |

Nesting: markers occur inside `<sGr>`, `<aGr>`, `<d>`, `<num>` and `<c>` as well as
directly in `<w>` (e.g. 28,103 `del_in` inside `sGr`).

#### `<materlect>` — mater lectionis, plus 21% legacy noise

The HFR authoring instructions specify that readings such as `AN` and `UḪ` are formatted
as `AO:MaterLect`, generalising to *Zusatzzeichen* that explain a sign reading (also
e.g. `AR`/`RU`); current TLHdig SimTex documentation defines lowercase material enclosed
in `°…°` as *Mater lectionis*. So the reading-valued instances have a clear semantics.

The `!` and `?` values do **not**: TLHdig has separate syntax for editorial
uncertainty and correction, which surfaces in this XML as `<corr c="…"/>`. The corpus
shows exactly that division — measured over all 315 `<materlect>` elements:

| `@c` content | Count | Verdict |
|---|---|---|
| sign readings (`uḫ` 76, `an` 46, `aḫ` 14, `um` 8, `iš` 5, …) | 246 | documented mater lectionis |
| pure editorial marks (`?` 48, `!` 16, `?!` 1) | **65** | mis-styled legacy data — belongs in `<corr>` |
| empty | 4 | — |

The 65 mark-valued instances should be preserved verbatim and flagged as anomalous, not
given a new "materlect" meaning.

#### `<subscr>` — epigraphic subscription, *not* a reading index

This is a genuine correction to an earlier reading of mine. The HFR instructions
explicitly distinguish the two: an actually subscripted sign is `AO:subscr`, whereas a
sign-reading index such as `SA₅` is written with literal Unicode subscript digits
`₀–₉` and is **not** `AO:subscr`. SimTex encodes the same phenomenon as "sign with
subscription" (`a-wa|a-ia`).

The corpus corroborates the distinction sharply: of 4,981 `<subscr>` elements, only
**7** occur in a word that also contains a literal subscript digit, and in those the two
are independent (`ut-ni₅-ia` + a separate `<subscr c="x"/>`). Had `<subscr>` been the
index mechanism it would co-occur with or replace those digits systematically. The
structural reading — `@c` belongs to the preceding sign — stands; the semantics are
epigraphic, not HZL/MZL index notation.

#### `<space c="N"/>` — a character count, not a measurement

HPM's documented editorial workflow is ODT/ODF-based with automatic conversion to XML,
and AOxml's `<space c="N"/>` preserves ODF's `<text:s text:c="N">` almost verbatim. In
ODF, `text:c` is formally the **number of consecutive U+0020 SPACE characters**, a
repetition count and not a physical measurement. The observed distribution fits: large
counts at line starts (indentation of a broken line), small counts within lines.

No AOxml schema sentence defining `space/@c` was found, so this is high-confidence
reconstruction from the ODF pipeline rather than a direct AOxml definition. It should be
carried as an unitless integer and **never** converted to millimetres.

### 3.6 Transliteration character inventory

185 distinct characters occur in `<w>` text. Beyond ASCII letters the set is:
`š Š ḫ Ḫ ṣ Ṣ ṭ Ṭ`, acute/grave accented vowels (`á é í ú à è ì ù ...` — the standard
index-1/index-2 convention), subscript digits `₀–₉`, `…` (50,290 — omitted text),
`x` (194,907 — illegible sign), `˽` (4,546 — MODIFIER LETTER SHELF), `〈 〉` (4,372/4,370
— editorial insertion), `½`, `×`, `+`, `_`, and two cuneiform characters used inline
(`𒀹` 1,899, `𒑱` 794).

---

## 4. Morphological annotation: the `mrp` system

This is the corpus's most valuable and least self-explanatory layer. There are
**1,611,153 analyses** attached to words via attributes `mrp1` … up to **`mrp99`**
(a word may carry 99 competing analyses), with `mrp0sel` recording which is chosen.

### 4.1 Grammar of an `mrpN` value

A value is a chain of one or two morph records joined by a plus-separator.

> **Correction.** An earlier draft of this document said the separator "appears as
> ` += ` and as `@+= `". That is incomplete: there are **four** surface forms, two of
> them using a bare `+` with no `=`. Counted over all 1,611,354 `mrpN` values:
>
> | Form | Count | Example |
> |---|---|---|
> | *(no clitic)* | 1,225,923 | `nerik=@Nerik@…@39.1@URU/KUR` |
> | ` += ` — space-delimited, inside field 4 | 350,781 | `…@II.1 += (a)šta@OBPst@@ ` |
> | `@+= ` — at a field boundary | 28,995 | `…@II.9@+= ya=an@CNJadd=…@` |
> | other `+`/`+=` spacing | 3,729 | — |
> | ` +@` — bare `+` ending field 4 | 1,853 | `…@38.1 +@CNJadd@@ m` |
> | `@+@` — bare `+` as its own field | 73 | `…@{a → …:D/L.SG}…@+@{R → PPRO.2PL.DAT}…@@ D` |
>
> A parser that splits only on `+=` mis-handles 5,655 values (0.35%). The split must
> accept an optional `=` and must report any residue rather than silently truncating.

Measured field counts after splitting (9,000-file sample; 579,123 single-record,
166,027 two-record):

```
base                                     [ += clitic ]
lemma @ gloss @ morphtag @ stemclass                        @ det
                                     lemma @ morphtag @ … 
```

Measured field counts after splitting on `+=` (9,000-file sample):

| Segment | 5 fields | 4 fields | 3 fields | other |
|---|---|---|---|---|
| base | 571,878 | 158,104 | 170 | 389 |
| clitic | — | 132,948 | 33,066 | 13 |

Reading: the **base** record is `lemma@gloss@morphtag@stemclass`; a **clitic** record is
`lemma@morphtag@stemclass`; the **determinative field is the last `@`-field of the whole
string**, so a base with no clitic has 5 fields and a base with a clitic has 4 (the det
having migrated to the end of the clitic). This accounts for ~99.95% of values.

Worked examples:

```
murši-DINGIR-LIM-=i- @ Muršili @ PNm.NOM.SG.C @ 38.3 @ m
        lemma          gloss      morphology     class  det

takk= @ entsprechen @ 3SG.PRS @ II.1  +=  (a)šta @ OBPst @ @ ␣
                                            clitic lemma & tag

KIRI₆ @ Garten @ {a → NOM.SG(UNM)}{b → ACC.SG(UNM)}… @ 29.1.1  +=  ya @ CNJadd @ @ ␣GIŠ
```

Field semantics:

1. **lemma** — citation form; `=` marks the morpheme boundary of the stem
   (`ḫarga=nu-`, `tešḫan=iye/a-`). 28,091 distinct.
2. **gloss** — German translation (`Garten`, `entsprechen`, `Muršili`). 8,531 distinct.
3. **morphological tag** — either a single tag (`3SG.PRS`, `D/L.SG`, `ACC.SG.C`,
   `PTCP.NOM.SG.C`, `ADV`, `NEG`) *or* a lettered set of alternatives:
   `{ a → NOM.SG(UNM)} { b → ACC.SG(UNM)} …`. The letters are the disambiguation
   handles referenced by `mrp0sel`. Lower-case `a`…`m` label base alternatives,
   upper-case `R`…`V` label clitic alternatives. 5,237 distinct raw values;
   `(UNM)` = unmarked (logographic writing, case not visible), `(ABBR)` = abbreviated.
4. **stem class** — the *Stammklasse*, which is the documented name of this column in
   the HFR annotation manual: a paradigm number from the HPM grammar (`29.1.1`,
   `I.7.1`, `II.6.1`, `38.2`). 15,051 distinct values.

   The field is in fact **three-way polysemous**. Besides paradigm numbers it carries
   (a) grammatical categories for indeclinables — `ADV` 32,616, `QUANcar` 31,272,
   `POSP` 25,622, `PREV` 21,545, `CNJ` 17,140, `DEMadv`, `INTadv`, `INDadv`, `QUANmul`,
   `QUANord`, `NEG`, `INTJ`, `INDCL` — and (b) morphology for logographic writings
   (`HITT.NOM.SG.C(ABBR)`, `D/L.SG(ABBR)`, `LUW.A/I(ABBR)`). 244 distinct non-numeric
   values in all, including compounds (`ADV, POSP, PREV`) and language prefixes
   (`HURR`, `HATT`, `PAL.CONNn || PAL.INTJ`).

   > **Correction.** An earlier draft claimed the part of speech is marked "with a
   > leading space". **That discriminator is unreliable.** Measured across the corpus,
   > **65 distinct values occur both with and without a leading space**, including every
   > core POS value: `ADV`, `POSP`, `PREV`, `CNJ`, `QUANcar`, `NEG`, `INDadv`, `INTadv`,
   > `DEMadv`. No upstream specification states that U+0020 is the formal discriminator.
   > The reliable test is membership of the **closed category vocabulary**; leading
   > whitespace is at best a corroborating signal.
5. **determinative / classifier hint** — the determinative or gender marker expected with
   the lemma (`D` divine, `m` masculine PN, `URU` city, `LÚ` male, `GIŠ` wooden,
   `(UZU)` flesh …), or, for clitic chains, the clitic's category (`CNJadd`, `CNJctr`,
   `REFL`, `OBPk`, `QUOT`, `PPRO.3SG.C.ACC`). 1,772 distinct.

### 4.1.1 The index space starts at 0, and it has gaps

Two properties of the `mrpN` attribute numbering, measured over all 747,087 words that
carry analyses:

| | Count |
|---|---|
| contiguous numbering | 746,598 |
| **non-contiguous** (e.g. `[1, 3]`, `[2, 6]`, `[3, 5]`) | **292** |
| **not starting at `mrp1`** | **19,081** |
| words carrying an **`mrp0`** attribute | **201** |

`mrp0` is a real analysis slot, not a typo for `mrp0sel` — and `mrp0sel` genuinely
points at it:

```
trans="ḪAL-ṢU"     mrp0sel="??? 0a"
                   mrp0="ḪALṢU@Bezirk, Festung@{ a → NOM.SG.STR}@@ "
```

So the analysis index space is `0…99`, gaps occur where analyses were deleted, and the
first index is not reliably 1. A converter that scans `mrp1`…`mrpN` drops 201 analyses
and cannot resolve any `mrp0sel` that references index 0. **The index must be read from
the attribute name and preserved verbatim**, never reassigned by enumeration order.

Note also that the two totals quoted in this document differ by exactly this amount:
**1,611,153** counts `mrp1`…`mrp99`, **1,611,354** includes `mrp0`. The latter is the
correct total.

### 4.2 `mrp0sel` — the disambiguation pointer

1,032,248 words carry `mrp0sel`. Its value is whitespace-padded (padding is not
significant) and is one of:

| Form | Count (9k sample) | Meaning |
|---|---|---|
| `N` (e.g. `1`, `2`) | 116,251 | analysis `mrpN` is selected, no sub-alternative |
| `Na` / `Nb` … | 34,970 | analysis `mrpN`, sub-alternative letter `a`, `b`, … |
| `Na Nb` (space-separated) | — | several readings remain possible |
| `DEL` | 80,347 | token deleted / not a word (fragment, editorial artefact) |
| `AKK` | 30,836 | Akkadian, not morphologically analysed |
| `HURR` / `HAT` / `SUM` / `LUW` | 2,242 / 183 / 1,025 / 26 | Hurrian / Hattic / Sumerian / Luwian, unanalysed |
| `???` | 12,794 | unresolved |
| `` (empty) | 295,907 raw | no selection made — analyses are candidates only |

Special letter tokens observed: `all`, `sg`, `pl`, and combinations like `aR`, `aS`
(base alternative + clitic alternative).

**`all` is documented.** The HFR annotation manual states that where ambiguity cannot be
resolved, all possibilities are left open, and gives `1all` as its example. Corpus
instances match: `1all` on `IŠ-TU` selects the whole `{a → …:ABL} {b → …:INS}` set.

**`sg` / `pl` are undocumented, but the corpus corroborates the obvious reading.** The
hypothesis is that `Nsg` / `Npl` select *all alternatives of the stated number* rather
than one lettered case — which fits HFR practice of retaining SG/PL ambiguity where
number cannot be decided. Tested by checking whether the referenced analysis actually
offers an alternative carrying that number:

| Result | Count | Share |
|---|---|---|
| consistent — ≥1 alternative of the stated number | **1,281** | **99.92%** |
| inconsistent — no alternative of that number | 1 | 0.08% |

Every selector points at a logographic `(UNM)` analysis whose alternative set spans both
numbers (`{a → NOM.SG(UNM)} … {c → NOM.PL(UNM)} …`) — i.e. exactly the case where a
Sumerographic writing hides number. Where a set happens to be entirely singular
(`IŠTĒNŪTU`, `IŠKUR`), `Nsg` selects all of it, which is still consistent. This is
strong empirical support, but it remains a reverse-engineered rule pending upstream
confirmation.

**The lower-case / upper-case split is reverse-engineered, not documented.** Lower-case
`a`–`m` labelling base alternatives and upper-case `R`–`V` labelling clitic alternatives
is not stated in any public HFR/TLH document found. The two-dimensional combinations
(`aR`, `aS`) make it very hard to read any other way, and the `{ R → …}` sets do sit in
the clitic segment of the `mrp` string — but it should be recorded as inference.

Because `mrp0sel` is often empty, **the corpus is only partly disambiguated**. A faithful
conversion must keep *all* candidate analyses, not just the selected one.

### 4.3 Word-level `@trans`

914,250 words carry `@trans` — a normalised, marker-free transliteration used as the
lookup key (`murši-DINGIR-LIMiš`, `ḪULlu`, `Ú-UL`). Special values: `%` for an
illegible sign, `~` prefix for a fragment (`~aklaš`, `~za`), `%-un` for
partly-illegible words.

---

## 5. Line references: the `lnr` grammar

`lb/@lnr` (408,085 values, 4,000+ distinct) is a compact section reference. Measured
grammar:

```
[ "{" fragment "}" ] [ surface ] [ column ] number [ prime ] [ tail ]
```

* **fragment** — `€1`, `€2`, …, and composites `€1+2`, `€2+3` (474 distinct; `€1`
  44,291, `€2` 24,019). Cross-references `AO:TxtPubl/@nr`. Some texts use `A1`-style
  sigla instead.
* **surface** — `Vs.` (obverse) 35,131 · `Rs.` (reverse) 26,797 · `obv.` 5,919 ·
  `rev.` 3,898 · `u. Rd.` (lower edge) · `lk. Rd.` (left edge) · plus uncertainty marks
  `Vs.?`, `Rs.?`, `Vs.!`, `Vs. (II)`.
* **column** — Roman `I`–`VI` (also lower-case `i`–`iv`), or `r. Kol.` / `lk. Kol.` /
  `r. col.` / `l. col.` (right/left column).
* **number** — Arabic.
* **prime** — `′` on 308,245 lines, `″` 6,043, `‴` 217. The prime marks a *relative*
  line count on a broken tablet (the absolute line number is unknown).
* **tail** — sub-line `a`/`b`, joined-line references `/1′`…`/12′`, and `!`, `?`, `(?)`.

678 distinct surface+column prefixes were observed; 252 `lnr` values contain **no number
at all** (bare `Rs.`, `lk. Kol.`) — these are surface headers rather than lines.

`lb` also carries:
* `@txtid` — the manuscript siglum for that line (matters in composite texts).
* `@lg` — the language of the line: `Hit` 364,674 · `Akk` 17,498 · `Hur` 13,462 ·
  `Hat` 6,331 · `Luw` 3,622 · `Sum` 1,601 · `Pal` 587 · `ign` 75, plus 71 dirty values.
  `<w>` may override with its own `@lg` (12,594 words, mostly `Hur` and `Luw`).
* `@cu` — see §6.

---

## 6. Cuneiform Unicode: `lb/@cu`

**405,787 of 407,623 lines carry a Unicode cuneiform rendering of the whole line.** This
is a major asset — most digital Hittite corpora have transliteration only.

Two caveats, both measured:

1. **It is line-level, not sign-aligned.** There is no per-word or per-sign anchor, so
   cuneiform cannot be attached to word or sign nodes without a separate alignment step.
2. **The character set is not pure Unicode cuneiform.** Of 431 distinct characters,
   the non-cuneiform ones are `▒` (U+2592 MEDIUM SHADE, **597,012 occurrences** — the
   placeholder for a broken/illegible sign), `?` 13,342, `°` 6,657, `|` 2,385, digits,
   and **Unicode Private Use Area characters** `U+100009` (2,572) and `U+100000` (875).
   46 lines carry `@cuDirty="1"`, and 3 files have a `<parser_error>` element embedded
   in `@cu`.

### 6.1 The Private Use Area codepoints

HPM publishes a downloadable sign list carrying HZL/MZL number, Unicode codepoint,
conventional reading, font glyph and autotext. From it:

| Codepoint | Identity | Status |
|---|---|---|
| `U+100000` (875×) | **SI×SÁ**, HZL 28 | Deliberate: sits in Supplementary Private Use Area B because no suitable standard Unicode cuneiform character exists |
| `U+100009` (2,572×) | **unresolved** | Not listed in the current HPM-derived sign list, which gives `U+100000` and `U+100007` as the remaining PUA signs plus `U+10000A` for another Hittite-specific sign |

Given its 2,572 occurrences, `U+100009` is plausibly a legacy Ullikummi/HPM assignment
dropped from the current table. Its sign identity should **not** be guessed — this is
one of the strongest questions to put upstream.

### 6.2 No public sign-aligned cuneiform

A search of the TLHdig/HPM published material found **no export containing sign-level
`@cu` alignment**. HPM documents its ODT→XML workflow and its cuneiform fonts but
exposes no alignment resource. The working assumption for conversion must therefore be
that no public alignment exists, unless the TLHdig team confirms they retain one
internally.

---

## 7. Text-Fabric: model and precedents

### 7.1 The data model (from `annotation/text-fabric` docs)

* Text is a sequence of **slots**, numbered `1..maxSlot`, all of one *slot type*.
* Everything else is a **node** (`maxSlot+1..maxNode`), linked to the slots it covers.
* Three warp features are structural:
  * `otype` — node feature mapping every node to its type.
  * `oslots` — edge feature linking every non-slot node to its slots.
  * `otext` — config-only feature declaring section levels and text formats.
* All other information is **node features** (int or str) and **edge features**
  (optionally valued). Absence of a value = absence of a data line; there is no null.
* `.tf` files are plain UTF-8: `@node`/`@edge`/`@config` header, `@key=value` metadata,
  a blank line, then `node<TAB>value` (node specs may be ranges `1-10,15`).
* Escapes in values: `\\`, `\t`, `\n`. Nothing else may appear raw.

Practical consequences for us: TF has **no schema for overlapping hierarchies** beyond
the slot linkage, which is exactly what we need — damage brackets that cross word and
line boundaries can be modelled as ordinary nodes over slot ranges.

### 7.2 Precedent 1 — BHSA (`ETCBC/bhsa`)

The reference TF corpus. Slot type `word`; node types `book chapter verse sentence
sentence_atom clause clause_atom phrase phrase_atom subphrase half_verse lex`;
~110 features. Relevant conventions we should copy:

* **Multiple parallel text representations as separate features**, selected by
  `@fmt:` templates in `otext.tf` — e.g. `g_word` (transliteration) vs `g_word_utf8`
  (native script), each with a matching `trailer` feature carrying the inter-word
  material. Formats are named `text-orig-full`, `text-orig-plain`, `text-trans-full`, …
* A `lex` node type with no slots of its own but linked to all occurrences — the model
  for a lexicon layer.
* Translated section names as `book@en.tf`, `book@de.tf`, … — the mechanism we can reuse
  for German/English glosses.
* `app/config.yaml` drives the TF browser: `typeDisplay` per node type (`label`,
  `features`, `hidden`, `level`), `excludedFeatures`, `provenanceSpec` with DOI.

### 7.3 Precedent 2 — Old Babylonian cuneiform (`Nino-cunei/oldbabylonian`)

The closest analogue: a cuneiform corpus converted from ATF by Cale Johnson and Dirk
Roorda. This is the model to follow.

* **Slot type = `sign`.** Node types `sign cluster word line face document`.
* Section levels `document / face / line` via features `pnumber / face / lnno`.
* Four text formats, exactly the shape we need:
  ```
  @fmt:text-orig-full    = {atfpre}{atf}{atfpost}{after}
  @fmt:text-orig-plain   = {sym}{afterr}
  @fmt:text-orig-rich    = {symr}{afterr}
  @fmt:text-orig-unicode = {symu}{afteru}
  ```
  i.e. a *source-faithful* format, a plain ASCII one, an accented one and a cuneiform
  one, each with its own inter-sign material feature.
* **Damage and editorial brackets are `cluster` nodes** (`det`, `missing`, `supplied`,
  `excised`, `uncertain`, `langalt`) that may nest and may cross each other; each
  cluster additionally induces a boolean flag on its member signs.
* Reconstruction guarantee: `atfpre + atf + atfpost + after` concatenated over the signs
  reproduces the original source exactly.

That last point is the design principle worth importing wholesale.

### 7.4 Is there already a Hittite TF corpus?

No. The TF corpora list (`tf/docs/about/corpora.md`) has proto-cuneiform (Uruk),
Old Assyrian, Old Babylonian and Neo-Assyrian medical texts under `Nino-cunei`, but
nothing Hittite/Anatolian. This conversion would be new.

---

## 8. Key experiment: is sign-level slotting viable?

The single consequential design choice is the slot type. Three measurements bear on it —
two that settle it, and one (§8.4) that constrains how damage may be modelled on top.

### 8.1 Editorial brackets do **not** align to sign boundaries

Scanning 510,458 words and classifying each marker by whether it sits at a sign boundary
(after `-` or `.`) or inside a sign:

| Marker | at boundary | **mid-sign** |
|---|---|---|
| `del_in` | 84,720 | 51,364 |
| `del_fin` | 54,675 | **67,108** |
| `laes_in` | 39,332 | 673 |
| `laes_fin` | 4,221 | **35,749 (89%)** |
| `corr` | 4,849 | **14,496 (75%)** |
| `ras_fin` | 177 | 1,513 |

This is expected Hittitological practice — a single sign can be half-broken — but it
means a naive sign tokenisation *loses* the exact bracket position.

### 8.2 Brackets cross word boundaries

Within the same sample, bracket nesting inside a single `<w>` is frequently unbalanced:
**27,930 `del` opens without a close** and **13,629 `del` closes without an open**. Break
spans routinely run across words and across lines.

### 8.3 Round-trip verification

A prototype tokeniser was written that splits `<w>` content on `-`/`.` into sign tokens,
emitting each marker as an inline token *at its exact character offset* inside the sign
it interrupts, and recording the separator in a per-sign `after` feature. Concatenating
`atf + after` over the signs of a word was compared byte-for-byte against the original
inner XML of that word.

Result on a random 1,500-file sample (95,357 words, 233,178 signs):

```
words round-tripped OK : 95,348
words FAILED           :      9
round-trip rate        : 99.9906%
signs produced         : 233,178   (avg 2.45 per word)
```

> **Correction — what this experiment did and did not show.** An earlier draft called
> this result "byte-exact" and dismissed the 9 failures as cosmetic. Both statements
> were too strong, and the second concealed the first.
>
> The comparison was made between `ElementTree.tostring()` output and a reassembly
> built from the *same parsed tree*. It therefore validates the **tokenisation**
> — that splitting a word into signs and recording markers at their exact offsets
> loses no information relative to the parsed document — but it does **not** validate
> reconstruction of the original file bytes. Parse-then-serialise is not a
> byte-preserving operation in any XML toolkit: namespace prefixes, entity and
> character-reference spelling, empty-element syntax and attribute quoting may all
> change. The 9 `ns0:tab` failures were a symptom of exactly that, not an artefact to
> wave away.
>
> So the honest statement of the result is: **sign tokenisation is
> information-preserving with respect to the parsed document, at 99.99% on this
> sample.** Byte-faithfulness against the source file is a *separate* guarantee that
> this experiment did not test and that serialisation alone cannot provide — it needs
> the original bytes retained and sliced directly (see the plan, §5.4).

**Conclusion: sign-level slots are viable**, provided each sign keeps a source-faithful
`atf`-style string that carries mid-sign markers in place. This reproduces the
Nino-cunei tokenisation guarantee. Byte-level fidelity is achievable but requires a
second mechanism, specified in the plan.

### 8.4 Bracket pairing is not a matched-bracket language

A follow-up measurement, prompted by review, undercuts the assumption that `del_in` /
`del_fin` behave as a properly nested bracket pair. Counting over the whole corpus with
document-scoped pairing:

| | Count |
|---|---|
| `del_in` elements | 436,674 |
| `del_fin` elements | 388,323 |
| opens never closed (document scope) | **107,221** |
| closes with no open (document scope) | **58,648** |
| crossing pairs (two families interleaved, e.g. `del_in laes_in del_fin laes_fin`) | 248 |

Line-scoped, only **71.9%** of `del_fin` closes resolve within their own line;
48,669 lines end with a break still open and 34,312 lines contain a close whose open is
elsewhere.

This is epigraphically expected — a line may begin inside a lacuna (`]xxx`) or end
inside one (`xxx[`), and a break can run across lines, columns and fragments. But it has
a hard modelling consequence: **the markers are primarily point boundaries, and spans
are a derived, partial interpretation of them.** A converter that assumes matched
brackets will invent ~166,000 spans that are not in the data. Crossing is rare (248
cases) but real, so any pairing logic must be per-family rather than a single stack.

---

## 9. Data-quality findings

### 9.1 The 224 malformed files

Every one was inspected and classified. They are not random corruption:

| Class | Count | Example | Repairable? |
|---|---|---|---|
| Unescaped `<` in text/attributes from a mangled find-replace | ~70 | `<w trans="%-uš<kap c-"Te%t pricḫt ap"` — a corrupted `<gap c="Text bricht ab"` (g→k, x→%, b→p, ch→ḫ) | yes, by pattern |
| Unclosed ODF leftovers | ~25 | `<w mrp0sel="DEL">…<text:line-break</w>` | yes |
| Unclosed `<AO:KolonNr>` / `<AO:Sumgram>` / `<AO:Akkgram>` inside `<w>` | ~20 | `<w><AO:KolonNr><gap c="Vs. I bricht ab"/></w> </AO:KolonNr></w>` | yes |
| `<gap>` closing the wrong element | ~15 | `<w><del_fin/></w><gap c="Text bricht ab"/></w>` | yes |
| Unescaped `"` inside an attribute value | ~10 | `trans="ṣuppu"'`, `lnr=" {€1+2} Rs. IV 4"/1′"` | yes |
| `<parser_error>` element embedded in `@cu` | 3 | `cu="𒅆𒇽<parser_error>kúrḫa</parser_error>𒄩▒"` | yes |
| Duplicate attribute | 1 | `KUB 17.16`: `cu=` given twice (identical values) | yes |
| **Encrypted file** | 1 | `CTH 813_XML_TLH/KUB 37.25.xml` begins `HBEGIN:oc_encryption_module:OC_DEFAULT_MODULE:cipher:AES-256-CTR` — a Nextcloud/ownCloud encryption header that leaked into the release | **no** |

**Reporting payload for the encrypted file.** Zenodo describes Beta 0.3 as an XML
dataset and states that XML errors and inconsistencies were corrected for this release,
so an encrypted storage blob inside the published ZIP is a packaging bug. A report
should carry: archive path `CTH 813_XML_TLH/KUB 37.25.xml`; DOI
`10.5281/zenodo.20328284`; ZIP MD5 **`f9acbc8db3111cc7dd88d82f7819a912`** (verified
against the Zenodo API for `TLHbasisONLINE25_1_ZENODO_Beta_03.zip`, 74,449,198 bytes);
and the first ~100 bytes of the file. Request: restore the plaintext XML in the next
version.

Aggregate parser verdicts: 157 "not well-formed (invalid token)", 65 "mismatched tag",
1 duplicate attribute, 1 syntax error.

So ~223 of 224 are mechanically repairable; one is unrecoverable and should be reported
upstream.

### 9.2 Dirty attribute values

Real values that will break naive parsing, all confirmed present:

* `lb/@lg` contains injected markup in 6 cases: `Hit> <w><note n='15' c=`,
  `Hit> <w><del_in/> … <del_fin/></w`; also `''`, `5f_`, `Hattian`, `Lu`.
* `text/@xml:lang` = `XXXlang` (4,520 — an unset placeholder, **not** a language) and
  `30lang` (1), `Hitt` (1).
* `corr/@c` includes `''`, `_`, `m`, `an`, `MEŠ` alongside the real marks.
* `AO:TxtPubl/@nr` includes `' {€3}'`, `'1'`, `'2'`, `''` beside the regular `€n`.
* 4 words carry an `@editingQuestion` attribute containing editor notes-to-self
  (`What is this???`, `Again???`).
* One `<w>` has `@mrpl` (lower-case L) instead of `@mrp1`; one `<mDodID>` for `<mDocID>`;
  one `<del_iin>` for `<del_in>`; one `<_in>`.
* Two `<PARSER_ERROR>` elements and one `<LINE_PREFIX>`, `<PARAGRAPH_LANGUAGE>` element
  survive in the text stream.

### 9.3 Structural quirks to plan for

* 427 `<w>` and 159 `<lb>` sit directly under `<div1>` rather than `<text>`.
* 235 `<w>` are nested inside another `<w>`; 45 `<clb>` and 32 `<lb>` sit inside `<w>`.
* 224 documents have their `<AO:Manuscripts>` outside `<text>`.
* Empty `<w/>` elements (286) with no children and no text.

---

## 10. What the conversion has to preserve

Summarising the above, "all available features" means at minimum:

0. Both the *documented* semantics (§3.5, §4.1, §4.2, §6.1) and the *raw* values, so
   that a future upstream clarification can be applied without reconverting.
1. Byte-faithful reconstruction of every word's transliteration **including marker
   position inside signs** (validated in §8.3).
2. All 1,611,153 morphological analyses — not only the selected one — with the five
   `mrp` fields parsed *and* the raw string kept.
3. The `mrp0sel` disambiguation pointer, including multi-valued and `DEL`/`AKK`/`???`
   forms.
4. Line references decomposed into fragment / surface / column / number / prime / tail,
   plus the raw `lnr`.
5. The manuscript-witness layer (`AO:Manuscripts`, `€n` sigla, joins).
6. The full editorial edit log in `<meta>` with editors and dates.
7. Line-level cuneiform Unicode including the `▒` breakage placeholder and PUA
   codepoints.
8. Footnotes with their escaped rich-text content.
9. Language assignment at document, line and word level.
10. Provenance: file path, CTH number, sub-corpus, docID.

---

## 11. Sources

* Text-Fabric — <https://github.com/annotation/text-fabric> (data model:
  `tf/docs/about/datamodel.md`; file format: `tf/docs/about/fileformats.md`; walker
  converter API: `tf/convert/walker.py`)
* BHSA — <https://github.com/ETCBC/bhsa> (`tf/2021/otext.tf`, `tf/2021/otype.tf`,
  `app/config.yaml`)
* Old Babylonian cuneiform TF corpus — <https://github.com/Nino-cunei/oldbabylonian>
  and the conversion spec <https://github.com/Nino-cunei/tfFromAtf>
  (`docs/transcription.md`)
* TLHdig project — <https://www.hethport.uni-wuerzburg.de/TLHdig/>
* TLHdig SimTex input documentation — <https://hethport.net/TLHdig/docu.php>
  (mater lectionis `°…°`, sign-with-subscription, uncertainty/correction syntax,
  language markers incl. `@Ign`)
* HFR authoring instructions, *Handreichung Basiscorpus* —
  <https://wres-hatti.adwudlit.uni-mainz.de/HFR/material/Handreichung_Basiscorpus.pdf>
  (`AO:MaterLect`, `AO:subscr` vs literal `₀–₉` indices)
* HFR annotation manual, *Handreichung Annotation* —
  <https://wres-hatti.adwudlit.uni-mainz.de/HFR_TEST/material/Handreichung_Annotation.pdf>
  (Stammklasse column; `1all` for unresolved ambiguity)
* HFR annotation overview — <https://hethport.net/HFR/annotation.php?lang=EN>
* HPM guide (ODT→XML workflow) — <https://hethport.net/HPM/hpm.php?p=hpmguide-en>
* HPM cuneiform fonts and sign lists — <https://hethport.net/cuneifont/> and the
  HitType sign list —
  <https://ctan.math.utah.edu/ctan/tex-archive/fonts/hittype/Documentation/hittitesignlist.pdf>
  (`U+100000` = SI×SÁ, HZL 28)
* HPM Konkordanz (CTH assignments per manuscript) —
  <https://www.hethport.uni-wuerzburg.de/hetkonk/>
* OpenDocument v1.1 specification (`text:s/@text:c` = space repetition count) —
  <https://docs.oasis-open.org/office/v1.1/OS/OpenDocument-v1.1.pdf>
* TLHdig Beta 0.3 dataset — <https://doi.org/10.5281/zenodo.20328284>
* TLHdig Beta 0.2 dataset (superseded) — <https://doi.org/10.5281/zenodo.15459134>
