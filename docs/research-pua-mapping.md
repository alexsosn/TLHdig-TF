# Research: mapped vs unresolved PUA cuneiform values (#20)

**Status:** research gate complete against TLHdig source 0.3 / TF 0.4.0.

This research separates three questions that must not be conflated:

1. does a line contain a Private Use Area code point?;
2. can the current converter/alignment associate that code point with a reading?;
3. does a pinned external source directly document the identity of that exact PUA code point?

Only (3) is strong enough to call a PUA value *mapped*. Corpus-learned `signmap.tsv` and the converter's own alignment are useful evidence, but are circular as mapping proof.

## Measured production population

`programs/research_pua_inventory.py` independently walks the repaired source `lb/@cu` stream and TF 0.4.0, then compares every PUA occurrence with the shipped line feature and existing sign alignment. Hosted run `34283104827` passed source/TF integrity; the provenance-aware follow-up run `34284009810` passed and generated `reports/research-pua-mapping.json`.

There are six PUA code points and 3,643 occurrences. Source and TF counts agree exactly, and every shipped `cu_pua` equals the number of PUA code points in its line.

| code point | occurrences | aligned assignments | level-0 occurrences | dominant aligned reading | research status |
|---|---:|---:|---:|---|---|
| `U+100000` | 924 | 879 | 45 | SI×SÁ 879/879 | mapped-deliberate-pua |
| `U+100001` | 1 | 1 | 0 | KA×ÚR 1/1 | ambiguous-legacy-pua |
| `U+100003` | 13 | 12 | 1 | KA×GIŠ 12/12 | ambiguous-legacy-pua |
| `U+100005` | 1 | 1 | 0 | KA×ÀŠ 1/1 | ambiguous-legacy-pua |
| `U+100006` | 3 | 2 | 1 | AMAR×KU₆ 2/2 | ambiguous-legacy-pua |
| `U+100009` | 2,701 | 2,530 | 171 | EZEN₄ 2,517/2,530 | ambiguous-legacy-pua |

Thus 924 occurrences are directly mapped by pinned external evidence and 2,719 are unresolved at the exact-codepoint provenance level. There are 218 PUA occurrences on level-0 lines, so a sign-only feature would necessarily be incomplete.

No aligned `cu_sign` value in the measured corpus mixes one of these PUA code points with a non-PUA code point; mixed-value behavior nevertheless needs a synthetic regression fixture because future data can do so.

## External evidence and provenance

Pinned external source: HitType package/sign list, version 2.3 (2026-06-09), with the 2021 Unicode update retained in the current documentation.

- `U+100000` is directly documented as **SI×SÁ, HZL 28** and intentionally remains in Supplementary Private Use Area B. This is a reproducible exact-codepoint mapping.
- The current HitType list gives standard Unicode code points for the signs matching the other five corpus PUA values by corpus evidence: KA×ÚR (HZL 137), KA×GIŠ (HZL 139), KA×ÀŠ (HZL 150), AMAR×KU₆ (HZL 276), and EZEN₄ / EZEN×ŠE (HZL 107).
- However, the current pinned list does **not** directly state that historical `U+100001`, `U+100003`, `U+100005`, `U+100006`, or `U+100009` were those signs. Their identities are therefore highly plausible but not externally proven old-PUA crosswalks.

The machine-readable research status in `reports/research-pua-mapping.json` consequently uses:

- `mapped-deliberate-pua` — direct exact-codepoint external mapping;
- `ambiguous-legacy-pua` — strong corpus identity evidence plus a current standard-Unicode sign, but no direct old-PUA crosswalk;
- `unknown-pua` — no pinned mapping evidence.

`ambiguous-legacy-pua` and `unknown-pua` are both **unresolved** for the production `cu_pua_unmapped` contract. This is intentionally conservative.

## Current implementation semantics

`cu` is verbatim line-level Unicode cuneiform. `cu_pua` is currently a line-level integer count computed directly from characters in Supplementary PUA ranges. It does not classify those characters and does not rewrite them.

`cu_sign` is an independently aligned per-sign view available only where the line alignment succeeds. It is unsuitable as the sole basis for PUA classification because level-0 lines have no complete sign assignment, and using learned alignment as authority would make the validator circular.

## Research conclusions

1. The old documentation assumption that the corpus contains only `U+100000` and `U+100009` is false for the current repaired production population; four rare PUA values also occur.
2. `cu_pua_unmapped` should be a **line-level count**, parallel to `cu_pua`, so every source occurrence is classified even when sign alignment is unavailable.
3. A value is mapped only when a pinned mapping table gives direct exact-codepoint evidence. Under the current evidence, only `U+100000` is mapped; the remaining 2,719 occurrences are unresolved.
4. Original `cu` and `cu_sign` strings must remain byte/Unicode-identical. This ticket is metadata classification, not Unicode normalization or replacement.
5. The production mapping/status table must be committed and versioned. A future unseen PUA code point must never silently become mapped; it must classify as unresolved and the corpus gate must fail until the inventory/status table is explicitly updated.
6. Version allocation is intentionally deferred until production integration after rebasing current `main`, because another artifact-changing lane (#66) is already at RED. Research, plan, and RED tests can proceed without claiming the next immutable TF version.
