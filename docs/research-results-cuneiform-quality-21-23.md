# Measured whole-corpus triage, issues #21 and #23

Evidence: [hosted real-artifact run #38145890293](https://github.com/alexsosn/TLHdig-TF/actions/runs/38145890293), exact research head `bf2accc7d34da0286654e62c7d58cf93436473bb`. This run verified every pinned external reference and uploaded [full compressed case inventories](https://github.com/alexsosn/TLHdig-TF/actions/runs/38145890293/artifacts/11704432466). Populations refer to existing `tf/0.4.0` and *not* a rebuilt artifact after #20.

## #21: all level-0 lines

The complete audit found **45,849** unaligned lines, reconciling exactly with `reports/alignment.md`.

| Primary classification | Lines |
|---|---:|
| damage-count-mismatch | 25,475 |
| no-sign-slots | 13,022 |
| unrendered | 3,313 |
| count-mismatch | 1,994 |
| compound | 1,137 |
| numeral | 709 |
| pua | 163 |
| editorial | 10 |
| unknown | 26 |
| **Total** | **45,849** |

The primary ordering is a deterministic queueing heuristic. Overlapping observed flags are more informative: 40,873 carry a placeholder, 40,197 have a damage/illegible-sign count mismatch, 6,036 contain a recognized compound reading, 4,784 contain a numeral, 3,601 contain the source's unrendered sentinel, and **198** contain at least one PUA codepoint. A PUA-bearing *line* count of 198 must not be confused with the **218 PUA occurrences** on level-0 lines measured by #20.

The no-sign-slots population is large and must be inspected separately. A line without a sign position cannot be repaired by shifting other readings.

## #23: all externally outvoted sign assignments

The inventory independently reproduced **31,055** all-reference-disagreed assignments, along with 133,032 split votes, 2,601,461 supported assignments and 47,759 unknown readings. The illegible-sign placeholder class (180,560 in `reports/signrefs.md`) is excluded from the reference vote by design.

Overlapping flags among 31,055 cases:

| Flag | Cases |
|---|---:|
| multiple reference traditions | 27,062 |
| single reference tradition | 3,993 |
| multiple Unicode codepoints in assigned sign | 14,716 |
| numeral reading | 8,412 |
| sources list differing glyphs | 17,155 |
| PUA in assigned sign | 2,524 |

Top examples: numeral `2` → `𒁹𒁹` (7,184), `BANŠUR` → `𒌷𒍏` (3,642), `wa` → `𒊀` (2,523), and `EZEN₄` → `U+100009` (2,517). The numeral and legacy PUA examples are not proven errors. The 17,155 reference-conflict flag measures glyph-string differences, which may include equivalent cuneiform spellings; it does **not** establish independent scholarly disagreement until equivalence-normalized per-lineage evidence is evaluated.

## Next gates

1. Review provenance and source-identity joins, then distinguish all-reference-disagreed cases backed by *two independent agreeing traditions* from reference coverage of a single tradition.
2. Preserve the source's numeral spellings, cuneiform glyphs and PUA. Do not introduce canonical rewrites by majority vote.
3. Inspect complete, source-addressable samples from the large mismatch and no-sign-slots clusters, including the aligner's greedy mixed damage+compound path. Build synthetic RED regressions before altering that path.
4. Rebuild current TF after any conversion change and compare source conservation, manual samples, independent signrefs and exact-head CI. Issue closure requires tests and adversarial review.
