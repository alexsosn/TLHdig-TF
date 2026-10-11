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
