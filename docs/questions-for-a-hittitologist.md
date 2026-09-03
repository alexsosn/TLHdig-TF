# Questions for a Hittitologist

**Subject:** eight decisions a machine cannot make, in the conversion of TLHdig to
Text-Fabric

---

Dear colleague,

We are converting **TLHdig** (Thesaurus Linguarum Hethaeorum digitalis, Beta 0.3,
Zenodo 10.5281/zenodo.20328284) into a Text-Fabric dataset, so that the corpus can be
queried by sign, word, lemma and morphology rather than read as XML. The conversion is
at [github.com/alexsosn/TLHdig-TF](https://github.com/alexsosn/TLHdig-TF).

One part of it needs your judgement rather than more programming.

TLHdig gives each line both a transliteration, sign by sign, and a string of Unicode
cuneiform for the whole line. Nothing in the source says which sign goes with which
codepoint, so we reconstructed that correspondence and then checked it against five
independent sign lists — the Oracc Global Sign List, Nuolenna, Enmerkar, the Wiktionary
`hit-translit` module built on Rüster & Neu's *Zeichenlexikon*, and Potnia. Of the 2.59
million signs they can judge, 94.0% are confirmed by every list that knows the reading
and a further 4.6% by some of them; 1.4% are contradicted by all of them.

**We are not asking you to check three million signs.** The questions below are the
residue: eight places where the evidence is genuinely ambiguous, or where our data
disagrees with itself. Each is stated with the counts and with citable passages, and
each should take a few minutes. Where we are simply wrong, saying so is the most useful
possible answer.

---

## 1. The PI-series ligatures — 4,523 signs

This is the largest question and the only one where our own data is inconsistent.

For the *w*-series TLHdig uses two different codepoints, and the proportions differ by
value:

| reading | attestations | commonest | second |
|---|---:|---|---|
| `wa` | 49,134 | 𒉿 PI — 95% | 𒊀 PI×A — 5% (2,516) |
| `wi` | 691 | 𒊅 PI×I — 91% | 𒉿 PI — 5% |
| `we` | 655 | 𒊄 PI×E — 97% | 𒉿 PI — 3% |
| `wu` | 1,023 | 𒊇 PI×U — **73%** | 𒊆 PI×IB — **26%** (269) |

The external sign lists give plain 𒉿 PI throughout and do not record the ligatures as
separate values, so every ligature reads to our checker as a disagreement.

**Two questions.**

**(a)** Are 𒊀 𒊅 𒊇 𒊄 (PI×A, PI×I, PI×U, PI×E) graphic variants of PI, to be treated as
the same sign for search purposes — or distinct signs a query should be able to separate?
The Zeichenlexikon gives them different numbers, which is why we cannot fold them
automatically as we did for other pairs.

**(b)** `wu` splits 73/26 between PI×U and PI×IB. Is that a real orthographic or
chronological distinction, or an inconsistency in the edition?

Passages: KBo 33.10+ 1 and 3 (`wu`, both codepoints on adjacent lines); KUB 26.75+
7′/obv. (II) 53′ (`wi`); KBo 50.270 4′ (`we`).

---

## 2. `NIN` written 𒊩𒈠 — 755 signs

We render `NIN`, `EREŠ` and `NIN₉` as **𒊩𒈠** (SAL + MA). Three of the five lists give
**𒊩𒌆** (SAL + TUG₂).

This is the one disagreement on the list for which we have no procedural explanation —
it is not an encoding equivalence, not a variant spelling anyone records, and not an
artefact of how the lists are indexed.

Passages: **RS 17.146 51** and **52**, both `D NIN GAL` — the goddess Ningal — where we
have 𒀭𒊩𒈠𒃲.

**Question.** Is 𒊩𒈠 a defensible writing of NIN in these texts, or is the second sign
wrong?

---

## 3. `SÌR` written 𒂡 EZEN — 2,684 signs

We render `SÌR` as **𒂡** (EZEN). One list gives **𒆟** (KEŠ₂).

Passages: **HT 2 1** and **2**, `1 MUNUS SÌR ŠA LÚ KISAL.LUḪ` and `1 MUNUS SÌR ŠA É.GAL`.

**Question.** Which sign is meant here?

---

## 4. `ZÌ` written 𒂠 ŠE₃ — 1,187 signs

We render `ZÌ` as **𒂠** (ŠE₃). One list gives **𒍥**.

Passages: **CHDS 3.181 1** and **HKM 36 45′**, both `ZÌ.DA` (flour).

**Question.** Same as above.

---

## 5. The numeral 2 written 𒁹𒁹 — 6,630 signs

We render `2` as **𒁹𒁹**, two DIŠ. Every list gives the dedicated **𒈫** (MIN).

Our reading of this is that the corpus genuinely writes two vertical wedges and that we
are right for these tablets while the lists are stating the general Mesopotamian norm.
We would rather have that confirmed than assume it.

Passages: **KBo 4.10+ 44′/Vs.! 9′** (`2 ME`); **StBoTB 1 80** (`2 GIŠ.TUKUL.MEŠ`).

**Question.** Is 𒁹𒁹 the expected writing of 2 in Hittite texts of this kind?

---

## 6. Compound spellings resting on thin evidence

Where one reading is written with several signs, we learned the spelling from the corpus
by frequency. The common ones are well attested and independently confirmed — `MEŠ` =
𒈨𒌍 (24,483 observations), `kar` = 𒋼𒀀 (2,928), `IŠTAR` = 𒌋𒁯 (1,243), `SAGI` = 𒋡𒋗𒂃
(1,830, and the corpus writes `SAGI A` = 𒋡𒋗𒂃𒀀, as in StBoTB 1 81).

Eighteen rest on fewer than fifty attestations and no external list confirms them:

| reading | our spelling | attestations |
|---|---|---:|
| `ḪUŠ` | 𒄭𒄊 | 45 |
| `gun` | 𒄘𒌦 | 41 |
| `PA₅` | 𒉽𒂊 | 37 |
| `DIR` | 𒋛𒀀 | 33 |
| `KUN₅` | 𒌉𒂠 | 31 |
| `ÙMMEDA` | 𒍏𒁕 | 27 |
| `MUD` | 𒄷𒄭 | 25 |
| `DÌM` | 𒊐𒃵 | 24 |
| `BÁḪAR` | 𒂁𒋡𒁓 | 24 |
| `ŠÙDUN` | 𒋙𒌪 | 20 |
| `DUL` | 𒌋𒌆 | 20 |

**Question.** Do any of these look wrong? A glance is enough; we are not asking for
verification of each.

---

## 7. The Glossenkeil is recorded two ways

TLHdig marks the Glossenkeil sometimes as a colon prefixed to the reading — `:za`,
`:ku`, `:kán` — and sometimes as the cuneiform character **𒑱** (U+124F1) inside the
reading itself: `𒑱ta`, `𒑱ḫa`, `𒑱ku`, `𒑱za`, `𒑱tar`.

The two behave differently in the cuneiform. A `:`-prefixed reading has **no** cuneiform
at all — U+124F1 appears zero times in 3.4 million signs of the rendered cuneiform, so
the Glossenkeil is simply not drawn — while a `𒑱`-prefixed reading carries it in the
transliteration.

**Question.** Is this a deliberate distinction — two different editorial situations — or
an inconsistency in the edition that we should report to the TLHdig editors rather than
model?

---

## 8. Two working assumptions we would like confirmed or denied

These underpin the whole reconstruction, so an error in either would be expensive.

**(a)** In the rendered cuneiform, **▒** (U+2592 MEDIUM SHADE) stands for one
unidentifiable sign, and corresponds to the transliteration `x`. We measured this at
93,526 of 93,544 attestations and built the alignment on it: a legible reading may not
take a shade, and `x` may not take a legible sign. Is that the right reading of the
convention?

**(b)** A sign the transliteration restores inside a lacuna — `[an]` — is normally
*also* restored in the cuneiform, appearing as the sign rather than as a shade. We
measured a restored sign taking a shade only 0.15% of the time, and used this to reject
a rule that would have been much more permissive. Is that expected?

---

## And separately: 74 repairs to malformed XML

Not a sign question, and independent of the above.

TLHdig contains 74 places where XML tags cross — `<w><AO:Akkgram>…</w>…</AO:Akkgram>` —
so the file cannot be parsed as it stands. Repair requires *choosing* which boundary
moves: closing the Akkadogram before `</w>`, or moving the word boundary. XML validity
cannot distinguish "the editor meant the wrapper to end here" from "the editor meant the
word to end here", and the converter should not be the thing that decides.

All 74 are catalogued in
[`reports/crossing-tag-review.md`](../reports/crossing-tag-review.md) with the original
bytes, the proposed bytes, and which element moves — 62 files; in 47 cases it is the
`</w>` word boundary that shifts, the rest move `AO:HitGLOS` (9), `AO:TxtPubl` (7) and
`AO:KolonNr` (3).

If this is of interest, the file is arranged so that each case can be judged from its
own context in a line or two.

---

## What we would do with the answers

Every answer changes something concrete and small: a fold in the equivalence table, a
correction to a spelling, or a note in the published documentation saying that a
particular disagreement with the standard sign lists is deliberate and why. Nothing here
requires you to trust the conversion — each question is stated so that the passages can
be checked against the tablets directly.

Where we are wrong, we would rather know than ship it. Where we are right, saying so
lets us mark the disagreement as intended, which is worth as much.

With thanks,

*[name]*
