# Research and implementation plan: ambiguous mixed damage/compound alignment (#21)

## Observed production behavior

Current `tlhdig.cuneiform.align()` first attempts strict damage-only alignment, then for mixed damage+compound lines runs `_drop(points, want)`: it discards the first `want` shade placeholders and invokes greedy `_expand()`. This is arbitrary where a line has lacunae both before and after a multi-sign logogram, and it can produce false `cu_sign` assignments when two distinct compound placements are valid.

In `reports/alignment.md`, **15,531** level-3 lines already use `damage compound`. The #21 real-corpus inventory found **6,036** level-0 lines containing at least one learned compound reading, but this overlap does *not* prove that a more permissive algorithm can resolve them. Existing full-corpus precision ceilings and cuneiform signrefs are hard gates.

Counterexample independent of scholarly glyph guesses: cuneiform `▒▒𒈨𒌍▒▒` and signs `x, MEŠ, x`. One shade must be discarded on **each** side. Dropping both leading shades destroys the necessary first `x`. The surviving assignments are `▒, 𒈨𒌍, ▒`.

Ambiguous counterexample: cuneiform `▒𒈨𒌍𒈨𒌍` with signs `MEŠ, a, MEŠ`; after discarding the one shade, the first or last `MEŠ` could be the two-codepoint spelling. A greedy choice asserts the middle reading without proof. The implementation must not choose one.

## Plan and TDD gates

1. **RED:** commit tests against public `cuneiform.align` for medial/suffix shade absorption, independent of sign-name reference evidence; two valid compound placements must leave ambiguous assignments withheld, not guessed; reject an illegal shade inside a compound.
2. Implement dynamic monotone alignment for **mixed damage+compound only**, with state for consumed cuneiform points, consumed transliteration sign slots, and *both* mechanisms having occurred. Transitions: skip one U+2592, consume a compatible one-point sign, consume an exact pinned multi-sign spelling. No external sign/reference table is used beyond the existing learned multi table.
3. Enumerate all accepting paths through forward/backward reachability (not exponential path enumeration). Assign a sign only when **all** accepting paths agree on the exact point/sequence; unknown positions stay `None`. Reject fully ambiguous results if no actual `cu_sign` survives.
4. Do not change `cu`, tokenization, no-cu, equal-count, pure-damage, numeral rules, or TF ontology.
5. Rebuild the **single** current pre-alpha artifact after #20's integration lane. Compare regression counts and independently judge every newly assigned sign with pinned external references; require source roundtrip, invariant conservation, app, manifest, full tests. Do **not** lower coverage or precision gates merely to pass them.
6. Logically-independent adversarial review should actively attack combinatorial complexity, contradictory candidates, unrendered markers, multi mappings containing placeholders, and level/method labeling. Keep PR draft until data-scale gates pass.

This is a narrow experimental algorithm proposal, not yet a justified corpus-level improvement.


## Hosted candidate finding and follow-up gate (2026-10-11)

The first full-corpus candidate run
[38151662798](https://github.com/alexsosn/TLHdig-TF/actions/runs/38151662798)
rebuilt the graph but stopped in the independent delta audit: the candidate changed
`main:cu_nsigns.tf`, which the first reporter incorrectly protected as unrelated.
The documented meaning of `cu_nsigns` is the number of codepoints in
`cu_sign` (sparse, only for sequences of length > 1), so a changed compound
assignment necessarily may change it. This is an audit-contract defect, not
permission to ignore arbitrary derived-feature drift.

Follow-up RED tests were committed before reporter implementation. The revised
reporter permits exactly this *additional* output to differ but independently
recomputes `cu_nsigns` for **both** the shipped baseline and rebuilt candidate
from their respective `cu_sign` nodes, requiring exact equality of all nodes and
counts. Missing, extra and incorrect counts are errors. The unchanged
source/graph/provenance feature fingerprints remain protected. New candidate
measurement, full validation and skeptical review are still required before
integration; no scientific correctness inference follows from fixing the gate.


## Whole-corpus candidate evidence after #20 (2026-10-11)

[Hosted read-only candidate build #38158200358](https://github.com/alexsosn/TLHdig-TF/actions/runs/38158200358) succeeded from a branch containing the merged #20 PUA artifact and all six pinned independent sign references. Full build, protected-feature comparison, independent sign reference check, source roundtrip, alignment gates and full current validation passed; this evidence is for the exact candidate aligner as checked in.

* **17,023 new** `cu_sign` assignments, **176 withdrawn**, **zero replaced**, **2,993,691 unchanged**, for a net increase of 16,847 (3,010,714 new total vs 2,993,867 baseline).
* All 17,023 newly assigned sign nodes were on lines transitioning level **0 → 3**; 171 changed sign records remained on level 3 and 5 became level 0. The 176 withdrawn values include 171 unchanged line levels and 5 degraded lines.
* Across **all 17,199 changed records**, the candidate has 11,600 supported, 1,422 split, 941 all-disagree, 253 unknown and 2,983 excluded verdicts. These totals include added and withdrawn assignments; use the transition cross-tab below to identify which classifications originate from an excluded baseline. In particular, these totals are **not** a precision percentage on the 17,023 additions.
* Exact transitions: excluded → supported 11,600; excluded → split 1,422; excluded → all-disagree 941; excluded → unknown 253; excluded → excluded 2,816. From originally supported/split/unknown/all-disagree to excluded: 57/23/17/70 respectively. These are counts of changed *records*, not validation verdicts or automatically identified errors.
* **No** changes to any protected non-alignment TF output; the derived `cu_nsigns` matches `cu_sign` exactly on both versions; complete `validate_current` passed.

Potential adversarial concern: 941 newly exposed all-reference disagreements may reflect real mapping faults, limitations of external lists, or compound-versus-component representations; the comparator never treats a majority vote as a replacement oracle. Source-addressable JSONL evidence is retained as a hosted artifact. The candidate cannot be merged until the rebuilt current TF outputs and their matching BUILD-MANIFEST have been committed, exact-head CI passes, and a distinct skeptical review accepts the scientific tradeoff.


## Independent case-level audit: HOLD current integration (2026-10-11)

The hosted candidate's actual `reports/research-alignment-delta-21.jsonl.gz`
(run #38158200358, artifact #11710155757, all 17,199 changed records)
reveals a potentially **systematic** false-positive category that summary gates
did not catch:

* **76 newly mapped** `MEŠ → 𒈨` readings, all followed immediately on the
  same line by `𒌍` assigned to a *different* sign slot. The locked learned
  compound table uses `MEŠ → 𒈨𒌍`; independent references mark all 76
  prefix-only assignments as `all-disagree`.
* Exact source-identifiable examples:
  `RS 18.115, Rs. 22′` (line 6485022, next `ša → 𒌍`);
  `RS 18.115, Rs. 34′` (6485034, next `ši → 𒌍`);
  `KUB 26.62+, Vs. I 12′/6′` (6488489, next `URU → 𒌍`).
  Cases often have a *cascade* of adjacent all-disagree assignments,
  strongly suggesting a displaced compound boundary. The difference
  between an independently corroborated sign and a sign whose codepoint
  happens to be there is scientifically essential.
* 941 new all-reference-disagreed assignments in total; the single-sign
  MEŠ category accounts for 76. Of the 176 withheld existing values,
  case-level review finds some demonstrably questionable former readings
  (e.g. `LÚ → 𒌍`), but that does not license introducing new false ones.
* **New mandatory research gate:** reconstruct each affected line's exact
  `cu` and ordered sign readings; identify whether `𒈨𒌍` belongs to
  the MEŠ logogram, a legitimate alternate reading or a damaged segment.
  No automatic scholarly "fix" from a sign list alone.
* **New RED gate:** make the small real-pattern case from a source line
  deterministic and refuse a prefix-only value for a known compound
  whenever alternative segmentations or unresolved damage prevent proof.
  Preserve the earlier medial/suffix-shade gain, exhaustive short-case
  oracle, source conservation and protected-output checks.
* **Integration is held** until the systematic category has been explained
  and a fresh complete measured candidate comparison passes. The prior
  full `validate_current` success is a structural gate, not a guarantee
  of sign-reading precision.


### Follow-on independent audit: downstream shift, not just the two split slots

All 76 flagged `MEŠ` prefix cases were grouped by their original line nodes
and independently measured from artifact #11710155757. **Every** case has the
second compound glyph as the next slot. Following each prefix split to the
next *explicit x→▒ placeholder anchor* (or line end) gives **420 candidate
assignments**: 294 all-reference-disagreed, 79 excluded, 37 supported,
7 unknown and 3 split. Only five of the 76 affected lines have a later such
explicit damage anchor. Thus suppressing just the initial `MEŠ` and following
`𒌍` still leaves a highly concentrated chain of likely displaced mappings
under a misleading confident level-3 status.

Conservative revised plan: once the split is found, withhold **that slot
and every subsequent sign until the next explicit, structurally enforced
`x→▒` alignment (exclusive)**, or to end of line when there is no anchor.
Keep upstream assignments and any later glyphs after the explicit damage
anchor. Do not infer a correction glyph and do not treat support from a
reference list as sufficient proof to bridge the shifted segment. Add RED
fixtures for the damage boundary and a no-anchor suffix before implementation.
Rerun whole-corpus counts and line-level adjudication; this should be regarded
as a deliberate conservative loss of at most the observed suspect segment,
not an unqualified precision improvement.


## Focused research: ellipsis is a lacuna, not a readable sign (#157)

The actual source `RS 18.115.xml` records `<w>…<del_fin/></w>` after
the legible words on Rs. 18′, 22′, 24′, 27′, 31′ and 34′. The line-level
`cu` ends with `▒▒▒`, while the earlier visible words have specific
codepoints. The **first** mixed-damage DP candidate assigned 132 new
legible glyphs to sign records whose reading is literally `…`
(plus 9 preexisting records withdrawn), despite this exact source
context. Examples: Rs. 22′ `…→𒊭`, Rs. 24′ and 27′ `…→𒌍`,
Rs. 31′ `…→𒈩`. The sign-token census identifies ellipsis as a distinct
type, not the concrete damaged-sign reading `x`.

Hypothesis: the mixed DP's generic `_fits` one-codepoint transition
implicitly treats every non-`x` reading, including `…`, as a readable
sign. A trailing ellipsis then absorbs a displaced visible sign and
allows a false one-codepoint compound prefix to be accepted.

Conservative plan / testable limits:
1. RED with the **complete exact source lines** Rs. 22′ and Rs. 34′:
   physically printed `MEŠ→𒈨𒌍` at both positions, following `ša→𒊭`
   or `ši→𒅆`, and `…→None`; source `cu` remains unchanged.
2. Only within mixed damage+compound DP, permit an ellipsis **non-consuming
   slot transition**: it represents an unspecified lacuna and does not
   claim an individual cuneiform point. Forbid simultaneously matching it
   to a legible codepoint. Adjacent `▒` points remain skippable only
   under the existing damage mechanism, never become invented glyphs.
3. Amend the independent exhaustive oracle with a separate epsilon edge,
   and adversarial-test ambiguous multiple ellipses and a legible sign
   adjacent to them.
4. Retain the split-compound safety fallback and verify the change
   does not reduce source conservation, produce zero-span TF *text nodes*,
   or change any protected feature; `cu_sign` simply stays absent for
   ellipsis slots.
5. Full hosted corpus comparison must explicitly count **newly asserted
   legible ellipses** (target zero within this path), newly unsupported
   split prefixes, all newly withdrawn supported glyphs and level
   coverage. No automatic signlist voting or blanket TF-level exemption.

Alternative stop: if a source line proves that `…` is intentionally
one *known* physical glyph, the above model is too broad. Record that
case and preserve its value with a dedicated source-grounded rule rather
than hallucinating one from structural fit.


## Independent adversarial check of the latest candidate (2026-10-12)

Latest full-corpus [candidate run #38181283073](https://github.com/alexsosn/TLHdig-TF/actions/runs/38181283073), full case artifact `11719540338`, rebuilt from all pinned sources and passed `validate_current.py` plus independent sign-reference and protected-output audits. Its exact results must **supersede** earlier figures from run #38158200358 for the revised #157 algorithm:

| Alignment assignments | Latest candidate |
|---|---:|
| Added | 34,482 |
| Replaced | 5,559 |
| Withdrawn | 4,029 |
| Unchanged | 2,984,279 |
| Net gain | 30,453 |
| Protected non-alignment outputs changed | 0 |
| New legible glyphs assigned to ellipsis | **0** |

The prior 76 source-identified false-confidence `MEŠ → 𒈨` additions were followed through **by sign-node identity** across both independently downloaded compressed JSONL artifacts. 74 now map to full `MEŠ → 𒈨𒌍`; in two cases the slot stays unassigned (no new change record). None retains a newly asserted `MEŠ → 𒈨` value.

### Challenging the reference verdicts, not optimizing them

The latest `excluded → all-disagree` subpopulation is **717**, clustered by the original (`sym`, `cu_sign`) values: 378 numeral `2 → 𒁹𒁹`, 112 `BANŠUR → 𒌷𒍏`, 62 `ZABAR → 𒌓𒅗𒁇`, 47 numeral `12 → 𒌋𒁹𒁹`, 36 `NIN → 𒊩𒈠`, 28 `KARAŠ → 𒆠𒆗𒁁`, and 15 `EZEN₄ → U+100009`. Their disagreement with the individually indexed external sign lists does not by itself falsify compound/numeral/source-literal spelling; each is retained visibly as a review candidate. There are also a handful of isolated single-reading disagreement cases that remain unresolved.

Exactly **one** change moves a previously externally *supported* assignment to *all-disagree*: `KUB 36.51, Rs. IV 10`, sign 546713, `ÙMMEDA: 𒍏 → 𒍏𒁕`. Independent inspection of the original pinned `corpus/TLHdig-0.3/CTH 336_XML_MYTH/KUB 36.51.xml` finds the `lb` `cu="𒊭𒊩𒍏𒁕𒌷𒀭𒄯𒉌𒅅▒▒▒"` and the immediately following word `<d>MUNUS</d><sGr>ÙMMEDA</sGr>`. The two glyphs `𒍏𒁕` **are present contiguously in the primary source**, immediately after MUNUS (`𒊩`). Thus the external classification alone is demonstrably inadequate to reject this correction.

The 4,029 withdrawals include **1,815 previously supported** assignments, of which **1,788** are on lines now unaligned (level 0), mainly because an unresolved `…` cannot consume a legible glyph. This is a deliberate precision/coverage trade-off, **not** evidence that those 1,815 individual formerly supported glyphs were all incorrect. Their source-aligned subspans might be recoverable with separately proved local anchors; do not claim they were erroneous simply because they were withdrawn.

### Outstanding integration gates

This scientific evidence supports fixing `…` as a non-consuming lacuna and refusing split compound boundaries. It does **not** mean external references perfectly adjudicate Hittite compound signs or that every new assignment is correct. Before a PR merge, commit the full rebuilt one-current-artifact `tf/0.4.0` outputs and matching manifest; rerun exact-head CI; give the full revised diff a separate skeptical check; update current release ZIP once main changes. Do not merge on a stale code-identity manifest.
