# Aligning cuneiform with transliteration — research

Every number here was measured on `tf/0.1.0`. Where a claim was made and later
disproved, both are kept: the corrections are the useful part.

## 1. The problem

`cu` holds Unicode cuneiform for a whole line and is not sign-aligned, so the corpus
cannot be searched by grapheme, sign frequencies cannot be counted, and no
script/transliteration pair can be offered to Context-Fabric (its sampler walks slots,
and no slot carried cuneiform).

## 2. Counting alone: 45.7%

Comparing, per line, the number of cuneiform codepoints against the number of non-anchor
sign slots, over all 412,637 lines:

| | lines | |
|---|---:|---|
| codepoints == signs | 188,594 | 45.7% |
| mismatch | 219,356 | 53.2% |
| no `cu` at all | 4,687 | 1.1% |

The surplus is almost always positive — `cu` carries **more** codepoints than we have
signs, +1 on 111,982 lines.

Those 188,594 lines are now laid out: `cu_sign` on 1,579,848 signs (46.4%), with
`cu_aligned` marking which lines were done. Absence means unknown, not "no sign".

## 3. Why the zip is right, not merely plausible

Equal counts do not prove correct pairing: two sequences of the same length still
misalign if one sign renders as two codepoints and another as none. Two independent
checks say it does not happen here.

**Learned from the corpus.** `programs/signmap.tsv` records, for each reading, the
codepoint it co-occurs with on equal-count lines:

| | |
|---|---:|
| distinct readings | 2,610 |
| confident (≥5 observations, ≥95% on one codepoint) | 1,019 |
| pairs they cover | 1,535,919 of 1,579,848 — **97.2%** |

`an` → 𒀭 at 0.996 over 79,692 observations. A wrong alignment could not concentrate one
reading on one codepoint like that.

**Validated against Oracc's sign list** (`oracc/osl`, `00lib/osl.asl`, CC0):

| | entries | |
|---|---:|---|
| agree | 630 | **96.2%** of those OSL knows |
| disagree | 25 | |
| reading not in OSL | 364 | mostly Hittite-specific values |

The 25 are not misalignments: `x` → ▒ is the illegible-sign placeholder and no sign at
all; `ku`/`KU`/`TUŠ` all land on 𒂉, which Unicode names DUR2 — one sign under several
names; `EZEN₄` maps to a Private Use Area codepoint with no Unicode name.

> **Parsing note.** A sign block carries `@form` subblocks with their own `@ucun`.
> Letting the last win put compound forms in the primary table — `na` came out as 𒈾𒊒.
> Taking the first `@ucun` per block moved agreement from 78.5% to 96.2%. The first
> number was a parser bug, not a disagreement with OSL.

## 4. What a dictionary does not fix: 3.8%

Keeping every `@ucun` per block gives 9,437 sequences longer than one codepoint. Using
those plus the confident 1:1 table to consume each unaligned line greedily resolved
**8,346 of 219,356 lines — 3.8%**.

OSL keys on Assyriological reading strings; `sym` carries Hittitological transliteration
conventions, and they do not line up. `meš` in OSL yields 𒍑 and 𒎌, not the 𒈨𒌍 the
corpus writes. `diškur` is not an OSL reading at all — it is a determinative plus a sign.

## 5. What is actually in the gaps

Anchoring each unaligned line on the confident 1:1 readings and measuring what lies
between anchors — 206,335 lines, 294,618 gaps:

| gap | share | mechanism |
|---|---:|---|
| 0 signs → 1 point | **39.2%** | the damage placeholder ▒ |
| 1 sign → 2 points | **20.5%** | two-sign logogram |
| 0 → 2 | 11.4% | consecutive ▒ |
| 1 → 1 | 9.4% | reading absent from the confident table |
| 1 → 3 | 3.1% | three-sign logogram |
| 0 → 3 | 2.0% | consecutive ▒ |
| 2 → 1 | 1.7% | punctuation in a slot |
| 1 → 0 | 1.4% | punctuation in a slot |

### 5.1 The placeholder dominates

Of the 115,346 orphan codepoints, **94,553 (82%) are `U+2592 MEDIUM SHADE`** — the
illegible-sign placeholder. Cuneiform writes one per lost sign; transliteration writes
one bracketed lacuna for the whole gap. Two conventions for the same fact, not a
misalignment. The rest of the category is editorial marks: `?` 1,672, `|` 1,667,
`°` 833.

### 5.2 Compound logograms are learnable from frequency

| reading | codepoints | observations |
|---|---|---:|
| `MEŠ` | 𒈨𒌍 | 21,818 |
| `2` | 𒁹𒁹 | 6,901 |
| `SIG₅` | 𒅆𒂟 | 2,965 |
| `BANŠUR` | 𒌷𒍏 | 2,713 |
| `kar` | 𒋼𒀀 | 2,702 |
| `NA₄` | 𒉌𒌓 | 2,083 |
| `IŠTAR` | 𒌋𒁯 | 1,189 |
| `ÍD` | 𒀀𒇉 | 842 |
| `SAGI` | 𒋡𒋗𒂃 | 1,824 |
| `ZABAR` | 𒌓𒅗𒁇 | 419 |
| `KARAŠ` | 𒆠𒆗𒁁 | 319 |

21,818 observations of one pairing is statistics, not a guess. OSL is not needed for
this; the corpus supplies it.

### 5.3 Numbers are positional, not lexical

`2` → 𒁹𒁹 (6,901) and `12` → 𒌋𒁹𒁹 (743). Cuneiform numerals are additive: tens as 𒌋,
units as 𒁹. One transliterated token, as many signs as the value needs. Derivable by
arithmetic, no table required.

### 5.4 Punctuation is in our slots, and should not be

| `˽` | 1,500 |
| `(` | 369 |
| `(_)` | 200 |
| `)` | 122 |
| `〈` | 111 |

and pairs like `'( )a'` → 𒀀 (67), `'an( )'` → 𒀭 (48). The tokeniser is emitting
brackets and spacing marks as sign slots. `signmap.tsv` already showed it: `)` → ▒ at
confidence 0.206.

**This is a defect independent of cuneiform.** These slots inflate every sign count in
the corpus, not just the alignment.

## 6. Conclusion

Four mechanisms account for the bulk of the 53.2%, and none needs an Assyriologist:

1. ▒ corresponds to damage, and damage positions are already known (`missing`, `cluster`)
2. compound logograms, learnable by frequency
3. numerals, derivable arithmetically
4. punctuation in slots — our own tokenisation defect

An earlier version of this document concluded the remainder needed "real sequence
alignment and someone who can map Hittitological transliteration onto OSL readings".
That was written after one failed greedy-dictionary attempt and before measuring the
gaps. The measurement contradicts it.
