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
   — half right, and §7 corrects the other half: ▒ tracks the transliteration `x`, not
   membership of a lacuna
2. compound logograms, learnable by frequency
3. numerals, derivable arithmetically
4. punctuation in slots — our own tokenisation defect

An earlier version of this document concluded the remainder needed "real sequence
alignment and someone who can map Hittitological transliteration onto OSL readings".
That was written after one failed greedy-dictionary attempt and before measuring the
gaps. The measurement contradicts it.


## 7. Auditing what was shipped: coverage is not precision

§1–6 measured what *could* be aligned. They never measured whether what was aligned was
aligned **correctly**, and the gate that shipped with them could not either — it counted
signs carrying `cu_sign` and lines reaching level 1, both of which a corrupt build
preserves perfectly. An external review put the question directly, and it deserved a
number rather than an argument.

The check has to come from outside the aligner. `signmap.tsv` qualifies: it is learned
only from lines whose counts already match, and the aligner never read it. So for levels
2, 3 and 4 it is an independent witness. For each sign whose reading has a confident
entry, does the assigned codepoint agree?

Disagreements split three ways, because damage makes one of them ambiguous. A reading
assigned ▒ where the table expects a sign might simply be a broken sign, so that class
is set aside as **soft**. The other two cannot be explained away: a legible reading
assigned some *other* legible sign, and `x` — the notation for a trace nobody could
identify — assigned a perfectly legible sign.

| level | lines | checked | hard disagreement | `x` not on ▒ |
|---:|---:|---:|---:|---:|
| 1 | 193,519 | 1,571,709 | **0.23%** | 24 of 94,050 (0.03%) |
| 2 | 138,162 | 940,415 | **14.13%** | 22,962 of 90,959 (25.2%) |
| 3 | 39,689 | 430,198 | **0.40%** | 264 of 6,640 (3.98%) |
| 4 | 66 | 753 | 0.00% | 0 of 25 |

Level 1 is sound, and levels 3 and 4 are close behind it. Level 2 — a third of the
corpus — was not.

The cause is visible in which pairs go wrong. The four most frequent are `x` receiving
𒀭 (1,960), `an` receiving ▒ (1,685), `zi` receiving ▒ (1,515), `x` receiving 𒀀 (1,034):
swapped pairs, the signature of an off-by-one shift. Absorption dropped *the first N*
placeholders on the line, wherever they fell, and when the line's own `x` owned one of
them the whole tail shifted by one.

### 7.1 The constraint that works is not the obvious one

The natural fix — only delete a placeholder where the bracket model records a lacuna —
turns out to be nearly vacuous, and only measurement says so. On level-1 lines, where
the counts force the correspondence and it cannot be argued with:

| condition | takes ▒ |
|---|---:|
| sign marked `missing` (inside a lacuna) | 879 of 583,289 — **0.15%** |
| sign marked `laes` (damaged but legible) | 95 of 92,870 — 0.10% |
| transliterated `x` | 94,026 of 95,209 placeholders — **98.76%** |

Being inside a lacuna barely predicts a placeholder at all, because a restored `[an]` is
restored in the cuneiform too. Permitting all 583,289 of those signs to take a
placeholder buys coverage by making the constraint permit almost anything.

`x` and ▒ are the same statement made in two scripts, and the correspondence holds in
both directions: 24 of 1,511,993 legible codepoints sit on an `x`. That is the
constraint. Measured on the shipped level-2 lines:

| rule | lines kept | signs decided | hard disagreement |
|---|---:|---:|---:|
| first N placeholders (shipped) | 138,162 | 824,462 | 8.80% |
| `x`, plus any damage family | 131,315 | 867,206 | 1.61% |
| **`x` alone** | 112,617 | 701,286 | **1.04%** |

The strict rule is the one adopted. The middle row decides 165,920 more signs, but the
signs it adds are about 3.9% wrong — it is buying coverage with a permission the
evidence does not support, which is the same trade that produced the defect.

Two further consequences follow from taking the constraint seriously. Where two valid
readings of a line disagree about a position, neither is asserted: that position gets no
`cu_sign` and `cu_undecided` counts it. And where the constraint is violated on a line
whose counts *match* — 1,183 placeholders sitting on something other than `x` — the
correspondence itself is still forced, so the rest of the line stands and only the one
position that cannot be believed is withheld.

### 7.2 Three smaller findings from the same audit

**Latin digits reach `cu_sign`.** 891 of 3,063,466 assignments (0.03%) are ASCII, all of
them the upstream rendering failure §5.3 identified. §5.3 added a guard, but only to the
compound learner; the level-1 zip never had one. The guard now sits at the point of
assignment, where every path passes.

**A compound vouched for its neighbours.** `_expand` verified an exact sequence only for
readings in the table and let every ordinary sign consume whatever came next, so one
convincing anchor at the end of a line certified everything before it. It is a real
mechanism; its measured cost is level 3's 0.40%, not the dominant defect it looks like.
Ordinary signs are now held to the same placeholder constraint. Catching the residue —
a clean sign assigned the wrong clean sign — needs the reading table at runtime, and
§8 explains why that is not free.

**Damage was learned as spelling.** 8 of 105 compound entries contain ▒: `a+na` → 𒀀▒𒀀
at 0.986 over 146 observations, `i+na` → 𒄿▒𒀀 at 0.970 over 99, `KAxU` → 𒅗▒𒌋 at 0.985.
The 95% threshold does not protect against this; it certifies that the hole in the
tablet recurs in the same place. 397 signs were assigned such a spelling. A placeholder
is now rejected from a compound both when learning and when loading, so a table
generated before the rule cannot reintroduce it.

## 8. Why the aligner does not read its own validators

The obvious way to raise precision further is to consult `signmap.tsv` at runtime: refuse
a 1→1 assignment whose codepoint contradicts a confident reading. It would work, and it
is deliberately not done.

`signmap.tsv` and Oracc's OSL are what the result is *measured against*. An aligner that
consumes them cannot be checked by them — the agreement figures in §3 and §7 would then
report the aligner's own inputs back to it, and the gate would pass no matter what it
did. This project has met that pattern repeatedly, and the rule it settled on is that a
gate comparing derived values against their own source passes indefinitely.

So the aligner uses only structure: how many codepoints there are, which of them are
placeholders, and which signs are transliterated `x`. The tables stay outside, and the
numbers they produce mean something.

The remaining error they cannot catch — a clean sign assigned the wrong clean sign — is
0.23% at level 1 and 1.04% at level 2, and it is reported per level in
`reports/alignment.md` rather than hidden. Raising precision past that point needs a
validator independent of *both*: OSL is the candidate, and it is not yet wired into the
gate.


## 9. Equal counts are not evidence

§7 measured every mechanism except the one nobody thought needed measuring. Level 1 was
treated throughout as the safe floor -- the counts match, so there is nothing to decide.
There is nothing to *decide*, but there is still something to be wrong about.

Two errors cancel exactly:

* a reading written with several signs is one codepoint too many;
* a reading the cuneiform does not render at all is one codepoint too few.

Together the counts balance, the zip runs, and every position between the two is off by
one. This was written down in `KNOWN-ISSUES.md` from the beginning -- "still misalign if
one sign renders as two codepoints and another as none" -- and then never measured.

    ŠA DINGIR MEŠ :za am mu ra at ti Ù ŠA KUR URU Ḫat ti      15 readings
    𒊭  𒀭    𒈨𒌍  ·   𒄠 𒈬 𒊏 𒀜 𒋾 𒅇 𒊭  𒆳  𒌷   𒉺  𒋾      15 codepoints

`MEŠ` needs two. `:za` needs none: the `:` is a Glossenkeil, the wedge marking a word as
foreign, and the tokeniser made it part of the sign token, so the slot exists in the
graph with nothing in the rendered cuneiform to match. The zip gave 𒈨 to `MEŠ` and 𒌍 to
`:za`, splitting one sign across two readings.

### 9.1 Why the audit could not see it

`signmap.tsv` cannot judge a reading it does not contain, and a multi-codepoint reading
is by construction not in it -- it lives in `signmap-multi.tsv`. So `MEŠ` -> 𒈨 was never
checked by the thing whose job was checking. The witness had a blind spot exactly where
the error was.

Probing for it directly: 333 level-1 lines carry a reading the compound table says takes
several codepoints, and **209 of them had been handed that compound's first codepoint
alone** -- `MEŠ` -> 𒈨 rather than 𒈨𒌍, 112 times; `2` -> 𒁹 rather than 𒁹𒁹, 29 times.

The contradictions also cluster, which independent errors do not. Of the 743 level-1
lines with any disagreement, 226 have six or more, and the longest-consecutive-run
distribution is almost identical to the count distribution -- these are shifted spans,
not scattered mistakes.

### 9.2 Two signals, both visible before the fact

Neither needs the validating table, so refusing on them keeps the agreement figures
meaningful. Scored on the *other* positions of the line:

| level-1 line | lines | disagreement elsewhere |
|---|---:|---:|
| clean | 192,169 | **0.04%** |
| a placeholder on a legible reading, or a legible sign on `x` | 996 | 14.72% |
| carries a known multi-codepoint reading | 304 | 33.76% |
| both | 29 | 50.25% |

So a single violated position is evidence about the **line**, not about the position.
The earlier behaviour -- withhold that one value, keep the rest -- was too generous by a
factor of 350.

Both signals now refuse the line.

The compound rule went through one more round, because the obvious version of it was too
kind. A line carrying a known compound has to survive `_expand` instead of taking the
shortcut, and 61% do not. The first implementation kept the other 39%, reasoning that the
table is a measurement rather than a law -- `MEŠ` is 𒈨𒌍 99% of the time, not always -- so
an expansion that fell through to one codepoint per reading was an ordinary zip that had
now been checked.

Measured, those survivors are wrong **30.64%** of the time, against 0.04% for lines
carrying no compound at all. Falling through does not mean the compound shrank; it means
something *else* on the line was missing a codepoint, and the surplus is still there,
still unexplained. The expansion now has to actually expand something or the line is
refused.

Cost: 1,459 lines, 0.75% of level 1. What it buys is level 1 meaning what its name says.

### 9.3 What is still not covered

The residue is the same mechanism with a compound the table has never learned -- `UGU`
is written 𒌋𒅗 and does not reach the thresholds -- so 59% of the badly-shifted lines
carry no *known* compound. That population shrinks as the table grows, which is the
two-build cycle, and it is not otherwise detectable without a sign list the aligner does
not have. It is bounded, though: whatever remains is inside the 743 lines, because a
compensating pair that shifts nothing measurable has shifted nothing.


## 10. A witness from outside

§8 argued that the aligner must not read the tables that judge it, and then admitted in
§9 that the tables judging it were poor witnesses anyway: `signmap.tsv` records
`MEŠ` -> 𒈨 at 0.57 confidence over 197 observations, and those 197 observations *are*
the shifted lines. Evidence assembled from the defendant's testimony acquits every time.

The way out is not a cleverer use of our own table. It is a table somebody else made.

### 10.1 Five of them, and they disagree

| list | licence | size | what it is |
|---|---|---:|---|
| [tosaja/Nuolenna](https://github.com/tosaja/Nuolenna) | AGPL-3.0+ | 12,612 readings | the largest; handles compound spellings |
| [eggrobin/Enmerkar](https://github.com/eggrobin/Enmerkar) | CC BY-SA 3.0 | 1,896 signs | OGSL-derived, with MesZL/Labat/HZL numbers |
| [Module:hit-translit](https://en.wiktionary.org/wiki/Module:hit-translit) | CC BY-SA | 1,254 readings | Hittite proper, keyed to the Zeichenlexikon |
| [Nino-cunei/tfFromAtf](https://github.com/Nino-cunei/tfFromAtf) | MIT | 1,123 readings | Text-Fabric's own ATF→Unicode mapping |
| [AncientNLP/potnia](https://github.com/AncientNLP/potnia) | Apache-2.0 | 352 readings | Hittite, actively maintained |

Between them, 15,582 readings. They are read from `refs/`, which is git-ignored: their
licences run from MIT to AGPL and what leaves the build is agreement counts and a
disagreement list, which are facts about our data rather than copies of theirs.

Four transliteration conventions between five lists, and the normalisation is most of
the work. A sign value's homophone index is written unmarked, with an acute, with a
grave, or with a subscript depending on its size; ATF writes them all as ASCII digits.
`sze3` and `ŠÈ` are one reading, and a comparison that misses that reports disagreement
where there is agreement.

**That they disagree with each other is the point.** `bar` is 𒁇 to us and to Enmerkar,
𒈦 to potnia and the Zeichenlexikon list. `MEŠ` is 𒈨𒌍 to everyone except potnia. A
single list would be another authority to defer to; five lists vote, and where the vote
splits we learn that the sign's identity is contested rather than that we are wrong.

### 10.2 What they say about us

2,594,125 of our assigned signs can be judged this way — not 87.5% of the *vocabulary*
but 92% of the actual signs, because the common readings are the ones every list holds.

| | signs | |
|---|---:|---:|
| every list that knows it agrees | 2,377,362 | 84.1% |
| the lists split among themselves | 139,269 | 4.9% |
| every list that knows it disagrees | 77,494 | 2.7% |
| no list knows the reading | 56,830 | 2.0% |
| a placeholder, so no list applies | 177,392 | 6.3% |

And by mechanism, which is the part that could not be had before:

| level | outvoted, of what the lists can judge |
|---:|---:|
| 1 counts matched | **2.17%** |
| 2 damage absorbed | 3.34% |
| 4 numeral derived | 3.82% |
| 3 compound expanded | **4.90%** |

The ladder holds from outside — level 1 really is the safest — but it **reorders 2 and
3**. Measured against our own table, level 3 looked four times better than level 2
(0.24% against 1.14%); measured from outside it is worse. The internal figure was
flattering the mechanism that the internal table was learned from.

### 10.3 What the disagreements are

Not all of the 2.7% is error, and the report separates the kinds:

* **A real divergence.** `ku` is 𒂉 in our data and 𒆪 in all four lists that know it,
  over 32,890 signs. We carry faithfully what the HPM font renders; the font is the
  outlier. This belongs upstream, not in a patch here.
* **The lists' own indexing.** A sign list files a reading under its head sign, so
  `BANŠUR` = 𒌷𒍏 reads as a disagreement with 𒌷 when it is not one. 3,575 signs.
* **Genuine local usage.** This corpus writes `2` as 𒁹𒁹 seven thousand times where the
  lists give the dedicated 𒈫. For these tablets we are right and the lists are general.

So the 2.99% headline is an upper bound on our error, and the gate treats it as a
ceiling on drift rather than as a defect count.

### 10.4 What this does not settle

The lists judge a *reading against a glyph*. They cannot see whether that reading was
attached to the right position on the line — a shift that swaps two readings whose
glyphs both happen to be attested passes. That is what the structural constraints in §7
and §9 are for, and the two checks are independent, which is the useful part.

Generating the cuneiform from the lists instead of aligning it remains open, and it is
tempting: a candidate glyph exists for 99.2% of real readings, against the 83.5% the
alignment assigns. But a generated glyph is our inference and `cu` is what the edition
printed, and on `ku` alone they would differ 32,890 times. If it is done, it belongs
beside `cu_sign` under its own name, never in place of it — and the disagreement between
the two is worth more than either.
