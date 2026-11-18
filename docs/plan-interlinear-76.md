# Plan: source-faithful interlinear readings (#76)

Baseline: current pre-alpha TF 0.4.0, pinned Text-Fabric 13.1, existing app-level sign renderer. Research [run 44381678054](https://github.com/alexsosn/TLHdig-TF/actions/runs/44381678054) actually rendered KUB 21.8 Vs. II 2′/3′ under hidden vs unhidden analysis config. The 32-KB JSON artifact proves all 7/10 line candidates become visible when simply unhidden, but the actual DOM nests equal-slot `analysis` nodes around each other and places the word under the analysis rather than making word-owned candidate rows. Do **not** unhide analyses as production representation.

## Chosen minimal hook

- Keep `typeDisplay.analysis.hidden=true` so default TF pretty line direct children are word nodes, as empirically observed for both representative KUB 21.8 lines.
- Register `customMethods.afterChild["line"]` in the existing `TfApp` sign-renderer lifecycle. TF 13.1 `tf.advanced.render._render` invokes it after each *direct* rendered child node. The hook receives the child ID and renders candidate summaries only for a `word`.
- For that word, use **only** `E.analyses.f(word)`; sort by source `F.index.v(analysis)` with deterministic stable ties, preserving missing/index gaps rather than inventing an authoritative rank. Read existing `lemma, gloss, morph, parse_ok` feature APIs. Never parse raw morphology, silently pick a selected candidate, or scan all words.
- Emit a small semantic, accessible candidate group with escaped text, visible candidate index, label/gloss/morph and explicit parse-failed status. Zero candidates -> no invented row; unavailable optional APIs -> bounded safe fallback. This is supplementary markup after the word, not a reimplementation of sign/line rendering, TF navigation, or node highlights.
- Style only classes actually emitted by this hook in `app/static/display.css`, with clear typography and no color-only status.
- Preserve the existing sign-local `plainCustom/prettyCustom`, source-link fail-closed behavior, app `reuse()` lifecycle and source corpus bytes.

## Research gate and admitted scope

The two current-pinned KUB 21.8 lines show 5 and 3 direct word children in hidden mode, with full source candidate sets `[1,2]`, `[1,2,3]`, `[1,2,3,4,5,6]`. Not yet proven for every damaged/nested line: the hook must check node type rather than assume every child is a word, and a later fixture must probe representative non-Hittite/damaged/ruling cases. Do not claim every candidate in every corpus location is perfectly laid out from this evidence alone.

## TDD and acceptance gates

1. RED unit tests before implementation: hook registry exists, zero-analysis stays empty, no nonword output, source index order and gaps maintained, all alternatives retained, parse-failed marker explicit, special HTML/XML text escaped, missing optional APIs degrade, bounded lookup counts, sign hooks unchanged, `reinit` registration survives reuse.
2. GREEN implementation in existing `app/app.py` and stylesheet only, not TF graph/converter or a new UI framework.
3. Existing full ordinary CI and current app/browser real-host smoke. Extend current #45 real browser integration to assert `A.pretty` of the pinned KUB 21.8 line contains interlinear candidate markup while original `tlh-sign` remains, with no source loss.
4. Logically independent adversarial review of real DOM and code, including ambiguous selected state, gaps/index ordering, high-cost scans, escaping and visual fallback. Do not merge until exact-head CI + real browser E2E both green.

The normal full browser consumes ~12 GiB peak RSS (#164). Do not add another separate per-page heavy workflow.