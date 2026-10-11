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
