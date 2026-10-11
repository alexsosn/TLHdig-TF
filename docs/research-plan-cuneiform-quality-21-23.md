# Research: unresolved line alignment and all-reference disagreements (#21, #23)

Baseline: pinned current tf/0.4.0, as reported by programs/check_alignment.py and programs/check_signrefs.py. These numbers describe the artifact at the start of research, not the outcome of a fix.

| Population | Baseline |
|---|---:|
| level-0 lines | 45,849 |
| assigned signs | 2,993,867 |
| all external lists that know the reading disagree | 31,055 |
| split reference opinions | 133,032 |
| PUA in unaligned lines | 218 occurrences (see #20 / PR #74 research) |

The external reference set is pinned in programs/signrefs.lock.json. Lists are not all independent: enmerkar is OGSL-derived and tfFromAtf is related to Šašková's work. Some high-count all-reference differences are legitimate writing conventions: numeral \`2\` is frequently two unit signs (𒁹𒁹), while external lists also attest a dedicated sign (𒈫). \`EZEN₄\` uses legacy PUA without an externally pinned historic crosswalk. Neither should be rewritten by vote.

Current \`cuneiform.align\` uses line shape and measured compounds, withholding ambiguous positions. Levels 0/1/2/3/4 are algorithm labels, not evidence of the same quality. Its \`_drop\` mixed damage/compound path chooses leading placeholders; review this before extending any rule. The absence of \`cu_sign\` must remain meaningful.

## Research questions

**#21** Enumerate every level-0 line with node ID, manuscript/line reference, raw \`cu\`, sign readings, sign-count delta, unrendered triplets, placeholders, PUA, possible compound/numeral and editorial context. Preserve overlapping flags as well as one deterministic primary bucket. These are *candidate explanations*, not evidence that a proposed alignment is correct.

**#23** Enumerate every all-reference disagreement with sign and line identity, level, original glyph and reading, each source's alternatives/abstentions, equivalence-aware verdict, and **independent-lineage** count. Cross with compounds, numerals, PUA, and level, and retain reference conflicts and unknown cases. Do not rewrite glyphs in this research phase.

## Pre-implementation plan / gates

1. Commit tests for exhaustive primary classification, overlapping flags, no majority-vote correction, equivalent-sign handling, and conservation of all source verdicts (RED).
2. Implement a read-only full-artifact inventory; do not import converter PUA classification from PR #74. Declare unknown where data cannot decide. Preserve JSONL cases locally / as workflow artifact, plus counts.
3. Run against actual current TF and **all verified locked reference sources**. Publish measured bucket counts, sample manual cases and baseline comparisons. Missing references must fail the research job, not reduce coverage.
4. Only then choose narrow fixes with evidence; write exact preconditions, ambiguity stops and adversarial regressions before production code. Compare before/after by evidence bucket, sign round-trip, source census, app, alignment and reference gates. Any changed cu_sign requires rebuilding the one current pre-alpha artifact.
5. A logically independent adversarial review must challenge classification exhaustiveness, line/sign join, source independence, and ambiguous cases before merging any fix.

Research intentionally does not assert a mapping defect just because a reference list objects.
