# Aligning cuneiform with transliteration — plan

Evidence in [research-cuneiform-alignment.md](research-cuneiform-alignment.md).
Every phase is TDD: the test that fails first, then the code, then the corpus-scale
measurement. No phase records an expected coverage before measuring it — that mistake
was made three times in the session that produced this plan.

## Ground rules

**Absence must stay meaningful.** `cu_sign` missing means *unknown*, never "no sign".
Every phase widens what is known; none may guess to fill a gap.

**Each phase is separately verifiable.** A phase that cannot be measured against the
corpus does not ship.

**`cu_aligned` gains resolution, not exceptions.** It becomes a small vocabulary saying
*how* a line was aligned, so a query can select exactly the confidence it wants:

| value | meaning |
|---|---|
| `0` | not aligned |
| `1` | counts matched; zipped one-to-one |
| `2` | aligned after resolving damage placeholders |
| `3` | aligned after resolving compound logograms |
| `4` | aligned after resolving numerals |

A consumer wanting only the safest material filters `cu_aligned=1`.

---

## Phase 0 — punctuation must not be a sign

**Independent of cuneiform, and blocking.** `(`, `)`, `〈`, `〉`, `˽`, `(_)` are being
emitted as sign slots (§5.4). They inflate every sign count in the corpus and they
corrupt any alignment before it starts.

*Test first:* a word containing `ka(-)at` yields signs `ka` and `at`, and no slot whose
`sym` is punctuation.

*Then:* decide per mark whether it belongs on the neighbouring sign as a feature or is
dropped from `sym` but kept in the source span. Nothing may be silently deleted —
`check_provenance_split.py` already enforces that `srcxml` is the sole record of nothing.

*Measure:* the change in slot count, and re-run the equal-count census. Some lines will
align that did not before, purely from removing false slots.

**Acceptance:** no slot has a punctuation-only `sym`; marker conservation unchanged;
`check_signs.py` round-trip still 100%.

---

## Phase 1 — damage placeholders

39.2% of gaps are a codepoint with no sign, and 82% of those are `U+2592` — one per lost
sign, where transliteration writes one bracketed lacuna.

*Test first:* a line whose cuneiform is `𒀀▒𒁀` and whose transliteration is `a-[x]-ba`
aligns, with the ▒ attributed to the damaged position and not to `a` or `ba`.

*Then:* when walking a line, allow a run of ▒ to be consumed wherever the sign sequence
is inside a `del` cluster or carries `missing`. The damage extents are already nodes with
offsets — this is a join, not a guess.

*Measure:* lines newly aligned, and how many ▒ remain unconsumed.

**Acceptance:** every newly aligned line has each ▒ inside a known damage extent. A ▒
outside one leaves the line unaligned.

---

## Phase 2 — compound logograms

20.5% + 3.1% of gaps are one reading written with two or three signs.

*Test first:* `MEŠ` against 𒈨𒌍 aligns as a single sign carrying both codepoints;
a reading seen twice does not enter the table.

*Then:* learn the table from the gaps the same way `signmap.tsv` was learned from
equal-count lines — a reading enters only above an observation floor and a confidence
floor, both recorded in the file. Ship it as `programs/signmap-multi.tsv` beside the
existing one, generated and pinned.

*Open question, to be decided by measurement:* whether `cu_sign` holds the whole
sequence for such a sign, or a separate `cu_signs` feature carries multi-codepoint
values. The first keeps one feature; the second keeps `cu_sign` strictly one codepoint,
which is what a grapheme search wants.

**Acceptance:** every entry in the table has its observation count and confidence in the
file; OSL agreement is reported for the entries OSL knows, as §3 did.

---

## Phase 3 — numerals

`2` → 𒁹𒁹, `12` → 𒌋𒁹𒁹. Additive: 𒌋 for tens, 𒁹 for units.

*Test first:* `2`, `12`, `30` produce the right codepoint sequences; a numeral that does
not decompose leaves its line unaligned rather than being forced.

*Then:* derive arithmetically. No table.

*Measure:* how many numeral tokens the rule explains, and which resist — the resistant
ones are the interesting result.

**Acceptance:** the rule is stated in the code as arithmetic with its exceptions named,
not as a lookup with special cases.

---

## Phase 4 — report and gate

*Then:* `programs/check_alignment.py` — a report of coverage by `cu_aligned` value, and
a gate that fails if coverage drops. It joins CI only if it runs from the `.tf` files in
seconds, as `check_structure.py` does; otherwise it is a release gate.

*Measure:* final coverage, stated as a number obtained after the work rather than
predicted before it.

---

## Phase 5 — precision, which phase 4 did not measure

*Raised by an independent review, and it was right to raise it.* Phase 4 shipped a gate
that counted assignments. It could not have failed a build that kept every assignment
and corrupted what they pointed at, and that is the build it passed: 16.65% of the
level-2 assignments disagreed with the corpus's own learned table.

*Do:* measure agreement per mechanism against a witness the aligner never reads, split
so that damage cannot explain the result away; fix what the measurement finds; and make
the gate check that each assignment is *permitted*, not merely that there are enough of
them.

*Acceptance:* three invariants hold on the artefact — every `cu_sign` is a sign, no
spelling contains a damage placeholder, and `x` and the placeholder correspond in both
directions — and each mechanism's disagreement rate is under a pinned ceiling.

*Measure:* level 2 went from 16.65% to 1.15%, level 3 from 0.42% to 0.25%, level 1
unchanged at 0.23%. Coverage fell 90.4% -> 82.7% of signs, deliberately: 58.7% of the
withdrawn assignments were ones the witness disagreed with.

*What this phase taught, which is more general than the alignment:* a coverage floor is
not a quality gate, and "the number went up" is not evidence that the number means what
it is named. See research §7-8.

---

## Explicitly out of scope

- **Aligning lines with no `cu`** (4,687). There is nothing to align to.
- **Reconstructing cuneiform the source does not give.** If `cu` omits a sign, the sign
  stays without `cu_sign`.
- **Sequence alignment against a full sign list.** §4 measured a greedy dictionary at
  3.8%; a proper DP alignment may do better, but the four mechanisms above are cheaper
  and account for more. Revisit only if they leave a large residue.
