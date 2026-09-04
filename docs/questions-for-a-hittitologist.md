# Questions for a Hittitologist

**Subject:** seven decisions a machine cannot make, in the conversion of TLHdig to
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
codepoint, so we reconstructed that correspondence and then checked it against six
outside sign lists — the Oracc Global Sign List, Nuolenna, Potnia, Enmerkar, Nino-cunei's
`tfFromAtf` mapping, and the Wiktionary `hit-translit` module built on Rüster & Neu's
*Zeichenlexikon*. They are not six independent opinions — Enmerkar descends from OGSL and
`tfFromAtf` from Šašková's list, so they stand for five traditions — and we say so
wherever the counts are reported. Of the 2.77 million signs they can judge, 94.1% are
confirmed by every list that knows the reading and a further 4.8% by some of them; 1.1%
are contradicted by all of them.

**We are not asking you to check three million signs.** The questions below are the
residue: seven places where the evidence is genuinely ambiguous, or where our data
disagrees with itself. Each is stated with the counts and with citable passages, and
each should take a few minutes. Where we are simply wrong, saying so is the most useful
possible answer.

Two things that were questions in an earlier draft are no longer. TLHdig's own SimTex
documentation settles what `x` means (§8), and settles the Glossenkeil outright (§7) —
what was left there turned out to be an edition bug rather than an editorial decision,
so it has moved to the report for the editors at the end.

---

## 1. The PI-series ligatures — 4,849 signs

This is the largest question and the only one where our own data is inconsistent.

For the *w*-series TLHdig uses plain PI and a ligature interchangeably, and the
proportions differ by value — `wi` uses three codepoints:

| reading | attestations | commonest | second |
|---|---:|---|---|
| `wa` | 51,586 | 𒉿 PI — 95% | 𒊀 PI×A — 5% (2,523) |
| `wi` | 705 | 𒊅 PI×I — 90% | 𒉿 PI — 7%; 𒊂 PI×BI — 4% (27) |
| `we` | 662 | 𒊄 PI×E — 97% | 𒉿 PI — 3% |
| `wu` | 1,035 | 𒊇 PI×U — **73%** | 𒊆 PI×IB — **26%** (272) |

The external sign lists give plain 𒉿 PI throughout and do not record the ligatures as
separate values, so every ligature reads to our checker as a disagreement. This matters
more than it would elsewhere because TLHdig's own documentation names the Zeichenlexikon
as its standard — "generally follow HZL transliteration standards" — and HZL numbers the
ligatures apart from PI. We therefore cannot fold them on our own authority.

**Two questions.**

**(a)** Are 𒊀 𒊅 𒊇 𒊄 (PI×A, PI×I, PI×U, PI×E) graphic variants of PI, to be treated as
the same sign for search purposes — or distinct signs a query should be able to separate?
The Zeichenlexikon gives them different numbers, which is why we cannot fold them
automatically as we did for other pairs.

**(b)** `wu` splits 73/26 between PI×U and PI×IB, and `wi` carries a third form,
𒊂 PI×BI, on 27 of its 705 attestations. Are those real orthographic or chronological
distinctions, or inconsistencies in the edition?

Passages: KBo 33.10+ 1 and 3 (`wu`, both codepoints on adjacent lines); KUB 26.75+
7′/obv. (II) 53′ (`wi`); KBo 50.270 4′ (`we`).

---

## 2. `NIN` written 𒊩𒈠 — 841 signs

We render `NIN` (785 of 800), `EREŠ` (46 of 50) and `NIN₉` (10 of 10) as **𒊩𒈠** (SAL +
MA). Three lists give **𒊩𒌆** (SAL + TUG₂), and the learned compound table reaches the
same spelling by a second route, which is mild evidence that this is systematic rather
than a handful of shifted lines.

This is the one disagreement on the list for which we have no procedural explanation —
it is not an encoding equivalence, not a variant spelling anyone records, and not an
artefact of how the lists are indexed.

Passages: **RS 17.146 51** and **52**, both `D NIN GAL` — the goddess Ningal — where we
have 𒀭𒊩𒈠𒃲.

**Question.** Is 𒊩𒈠 a defensible writing of NIN in these texts, or is the second sign
wrong?

---

## 3. `SÌR` written 𒂡 EZEN — 2,720 signs

We render `SÌR` as **𒂡** (EZEN). One list gives **𒆟** (KEŠ₂).

Passages: **HT 2 1** and **2**, `1 MUNUS SÌR ŠA LÚ KISAL.LUḪ` and `1 MUNUS SÌR ŠA É.GAL`.

**Question.** Which sign is meant here?

---

## 4. `ZÌ` written 𒂠 ŠE₃ — 1,228 signs

We render `ZÌ` as **𒂠** (ŠE₃). One list gives **𒍥**.

Passages: **CHDS 3.181 1** and **HKM 36 45′**, both `ZÌ.DA` (flour).

**Question.** Same as above.

---

## 5. The numeral 2 written 𒁹𒁹 — 7,184 signs

We render `2` as **𒁹𒁹**, two DIŠ, on 7,184 of its 7,354 attestations. Every list gives
the dedicated **𒈫** (MIN). The same pattern runs through the other numerals we learned:
`11` = 𒌋𒁹, `12` = 𒌋𒁹𒁹, `13` = 𒌋𒁹𒁹𒁹, `20` = 𒌋𒌋.

Our reading of this is that the corpus genuinely writes two vertical wedges and that we
are right for these tablets while the lists are stating the general Mesopotamian norm.
We would rather have that confirmed than assume it.

Passages: **KBo 4.10+ 44′/Vs.! 9′** (`2 ME`); **StBoTB 1 80** (`2 GIŠ.TUKUL.MEŠ`).

**Question.** Is 𒁹𒁹 the expected writing of 2 in Hittite texts of this kind?

---

## 6. Compound spellings — where the corpus and the lists part company

Where one reading is written with several signs, we learned the spelling from the corpus
by frequency: 139 spellings, each the reading's commonest layout at confidence 1.00. The
common ones are well attested and independently confirmed — `MEŠ` = 𒈨𒌍 (26,082
observations), `SIG₅` = 𒅆𒂟 (3,346), `kar` = 𒋼𒀀 (2,764), `NA₄` = 𒉌𒌓 (2,163), `SAGI` =
𒋡𒋗𒂃 (1,824, and the corpus writes `SAGI A` = 𒋡𒋗𒂃𒀀, as in StBoTB 1 81).

**Forty-one of the 139 are a Glossenkeil plus an ordinary sign** — `𒑱ma` = 𒑱𒈠, `𒀹ku` =
𒀹𒂉 — and no external list carries them, since no list treats a Glossenkeil as part of a
value. We do not think those need checking: the sign after the wedge is separately
confirmed in each case. We mention them only so the count is not misleading.

That leaves two groups that do.

### (a) Well attested, and no list agrees

These are not thin evidence. Each is the corpus's own consistent spelling over hundreds
of instances, and each is contradicted by at least one standard list:

| reading | ours | the lists say | signs | lists against |
|---|---|---|---:|---:|
| `BANŠUR` | 𒌷𒍏 | 𒌷 / 𒍎 | 3,642 | 2 |
| `GUDU₁₂` | 𒅎𒈨 | 𒄴𒈨 / 𒅎 | 810 | 2 |
| `ZABAR` | 𒌓𒅗𒁇 | 𒌓𒅗𒈦 | 719 | 2 |
| `KARAŠ` | 𒆠𒆗𒁁 | 𒆠𒄨𒁁 | 455 | 2 |
| `ÚTUL` | 𒄰 | 𒁹 | 246 | 1 |
| `BÀD` | 𒂥 | 𒂦 | 172 | 2 |
| `GALA` | 𒍑𒂉 | 𒃲 / 𒍑 | 111 | 2 |

`BANŠUR` = 𒌷𒍏 is the one we would most like an opinion on. Three and a half thousand
instances of a two-sign writing the lists do not give is either a real convention of
these texts or a systematic error, and we cannot tell which from inside the data.

`ZABAR` and `KARAŠ` are a narrower kind of disagreement: we and the lists agree on the
shape of the word and differ in one position — 𒁇 BAR against 𒈦 MAŠ, 𒆗 against 𒄨. Even
saying which of those pairs is a real distinction in these texts would help.

**Question.** Are these Hittite writings the general lists simply do not cover, or are we
wrong about them?

### (b) Thin, and contradicted

Ten spellings rest on fewer than fifty attestations *and* are contradicted by every list
that knows the reading. A glance is enough; we are not asking for verification of each.

| reading | our spelling | attestations | lists against |
|---|---|---:|---:|
| `ÙMMEDA` | 𒍏𒁕 | 24 | 1 |
| `ŠÙDUN` | 𒋙𒌪 | 20 | 1 |
| `ÉN` | 𒋙𒀭 | 14 | 2 |
| `TÉŠ` | 𒍏𒉄 | 13 | 1 |
| `BURU₅` | 𒉆𒂟 | 11 | 2 |
| `TIBULA` | 𒊭𒀀𒋻 | 11 | 2 |
| `NIN₉` | 𒊩𒈠 | 11 | 2 |
| `nin` | 𒊩𒈠 | 10 | 3 |
| `GALA` | 𒍑𒂉 | 8 | 2 |
| `tan` | 𒆗𒀭 | 8 | 4 |

`NIN₉` and `nin` are the same disagreement as §2 arriving by a second route, which is
mild evidence that it is systematic rather than accidental. `tan` = 𒆗𒀭, contradicted by
four lists on eight attestations, is the one we would bet against ourselves on.

---

## 7. The Glossenkeil — asked, then answered by the documentation

This was a question until we read the SimTex page. Leaving it in with its answer, in
case the reasoning is wrong.

TLHdig's documentation gives the Glossenkeil two input forms and two distinct signs:

| input | meaning | rendered |
|---|---|---|
| `;` | Glossenkeil (single) | **𒀹** U+12039 ASH ZIDA TENU |
| `:` | Glossenkeil (double) | **𒑱** U+12471 PUNCTUATION SIGN VERTICAL COLON |

The corpus bears this out. It holds 1,900 `𒀹` and 811 `𒑱`, both drawn in the line's
cuneiform, and the spellings we learned from frequency agree independently: `𒑱ma` =
𒑱𒈠, `𒑱wa` = 𒑱𒉿, `𒀹ša` = 𒀹𒊭 and eight more, each at confidence 1.00. A Glossenkeil
and its sign are two codepoints under one reading.

What is left is not an editorial distinction but 188 sign tokens where the raw input `:`
survived unconverted — `:ku`, `:al`, `:wa`. Those are in the bug report at the end.

**The only question we still have** is whether the single and double Glossenkeil are
distinctions a corpus query should be able to separate, or whether a search for one
should find both. We have modelled them as distinct, since the edition writes them so.

---

## 8. One working assumption we would like confirmed or denied

This underpins the whole reconstruction, so an error in it would be expensive.

A sign the transliteration restores inside a lacuna — `[an]` — is normally *also*
restored in the cuneiform, appearing as the sign rather than as a shade. We measured a
restored sign taking a shade only 0.15% of the time, and used this to reject a rule that
would have been much more permissive. Is that expected?

(The companion assumption — that **▒** U+2592 stands for one unidentifiable sign and
corresponds to the transliteration `x` — we no longer need to ask about. The
documentation defines `x` as "unreadable, usually damaged cuneiform sign", written with
no brackets, and we measure the pairing at 93,526 of 93,544.)

---

## For the TLHdig editors: three things we would report upstream

None of these is a sign question. We list them because someone should see them, and we
do not know whether that is you or the editorial team.

### 7,462 signs the edition could not render

Where TLHdig's own renderer has no glyph for a sign, the line's cuneiform carries the
literal three characters `?°?` in its place: **7,462 of them on 5,713 lines**. It stands
for exactly one sign, which we established by measurement — treating it as a sign gives
98.9% agreement with our reading→sign table where treating it as annotation gives 83.1%.

Classifying the 2,347 of them whose line we could align — the rest sit on lines that
align at level 0, so we cannot say which reading each belongs to:

| class | share | examples |
|---|---:|---|
| a reading the renderer's table does not cover | 66% | `per` (66), `ZÁḪ` (38), `DU₄` (32), `SAKAR` (23), `MUHALDIM` (12), `TÍLLA` (9), `SÎN` (9) |
| editorial text left in the sign stream | 17% | `leer`, `erasure`, `…`, `¬¬¬`, `===` — the last two are the search page's own wildcards for single and double paragraph rulings |
| ad-hoc index | 7% | `danₓ`, `ALAMₓ`, `šerₓ`, `waₓ` — no codepoint exists for an unassigned index |
| Glossenkeil in input form | 7% | `:ku`, `:wa`, `ki:ia` — the 188 below |
| ASCII `h` where the corpus means `ḫ` | 4% | `ha`, `hu`, `hi`, `ah`, `hal` |

The largest class is the plain one: 768 distinct readings, roughly half syllabic and half
logographic, that the renderer has no glyph for. Some are clearly real (`per`, `ZÁḪ`,
`MUHALDIM`); others look like transliteration debris that has reached the sign stream by
accident (`Š`, `xx`, `”TE”`, `GI/GIŠ`). We can supply the full list if it is useful.

The last three classes are small but look mechanically fixable, and together with the
`¬¬¬`/`===` markers they account for a fifth of the total.

### 188 Glossenkeils left in SimTex input form

`:ku`, `:al`, `:wa` — the raw `:` rather than the rendered **𒑱**. Everywhere else the
corpus holds the rendered character (1,900 `𒀹`, 811 `𒑱`), so these 188 are the
exception, and they are exactly why the renderer fails on them.

### 74 places where XML tags cross

`<w><AO:Akkgram>…</w>…</AO:Akkgram>`, so the file cannot be parsed as it stands. Repair
requires *choosing* which boundary moves: closing the Akkadogram before `</w>`, or
moving the word boundary. XML validity cannot distinguish "the editor meant the wrapper
to end here" from "the editor meant the word to end here", and the converter should not
be the thing that decides.

All 74 are catalogued in
[`reports/crossing-tag-review.md`](../reports/crossing-tag-review.md) with the original
bytes, the proposed bytes, and which element moves — 62 files; in 47 cases it is the
`</w>` word boundary that shifts, the rest move `AO:HitGLOS` (9), `AO:TxtPubl` (7) and
`AO:KolonNr` (3). Each case can be judged from its own context in a line or two.

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
