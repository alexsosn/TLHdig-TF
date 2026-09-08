# Research: corpus-specific Hittitological rendering

Issue: #42

This document freezes the research gate before renderer design or production changes.

## Question

Which TLHdig-TF graph semantics need corpus-specific Text-Fabric presentation, and which Text-Fabric 13.1 hooks can expose those semantics without creating a second parser, changing graph data, or erasing normal browser hierarchy?

## Sources of truth

The renderer is an adapter over already-modelled corpus semantics. It must not reinterpret AOxml itself.

Canonical meanings come from the released TF feature headers and `programs/tlhdig/featuremeta.py`; conversion behavior is checked against `programs/tlhdig/convert.py` and `programs/tlhdig/signs.py`. The actual release distribution is measured by `programs/research_renderer_features.py`, which reads node-feature files directly and deliberately avoids loading `oslots` or the multi-gigabyte graph.

The current release is `0.3.0`.

## Measured release states

The corrected full-release census reports these active sign states:

| feature | active signs | meaning relevant to display |
|---|---:|---|
| `sgr` | 105,647 | sign is in a Sumerogram |
| `agr` | 16,369 | sign is in an Akkadogram |
| `det` | 50,888 | determinative |
| `num` | 59,040 | numeral |
| `missing` | 1,253,251 | lacuna / missing sign |
| `laes` | 215,691 | damaged but legible |
| `ras` | 11,918 | erasure |
| `add` | 905 | editorial addition |
| `corr` | 63,521 | philological correction/mark |
| `subscr` | 5,000 | epigraphically subscripted sign attached to this sign |
| `materlect` | 308 | mater lectionis / additional sign information |
| `surplus` | 71 | scribal surplus excised by the editor |

There are **1,393,419 signs** with at least one selected display state and **117 observed state combinations**. This rules out a winner-takes-all renderer: multiple semantics legitimately overlap and must layer.

The first research probe initially produced implausible multi-million counts for `sgr`, `agr`, `det`, and `num`. Investigation showed these four integer flags are stored explicitly as `0` or `1` for every sign. The probe was corrected to count only non-zero values and rerun before design. This matters to implementation too: a renderer must test flag truth, not merely feature-definition/presence, for these four features.

## Morphology is deliberately not collapsed into sign display

The release contains **314,598 words with more than one analysis** (`nanalyses > 1`) and **7,290 words with more than one selected analysis** (`nselected > 1`). The renderer must therefore not invent a single authoritative morphology, stem, language or lexical interpretation merely to decorate the transliteration. Competing analyses remain graph/query semantics and may be displayed elsewhere, but #42 does not resolve them.

## Cuneiform is a separate line-level format

The release has `cu` on **407,950 lines** and `cudirty` on **46 lines**. `otext.tf` defines `text-cuneiform` at line level (`line#{cu}`), while the transliteration formats use sign `sym` plus `after`.

Therefore a sign-level custom transliteration renderer must not replace or synthesize the cuneiform format. In particular, it must not require `cu_sign`, whose coverage is intentionally incomplete, as the ordinary sign text source.

## Feature values are not safe presentation tokens

Some display-relevant features are not booleans. `subscr`, `materlect`, `surplus`, and correction-related values can carry text or source notation. Corpus samples include punctuation and escaped/XML-like source material. Raw feature values must never be interpolated into CSS class names or inserted as unescaped HTML.

The safe presentation contract is therefore based on a small fixed vocabulary of semantic **presence/state classes** whose names are owned by the app, while human-readable sign text continues to come from the released `sym`/`after` text contract.

## Text-Fabric 13.1 hook contract

The repository pins Text-Fabric 13.1.0. Inspection of its rendering path shows:

- `plainCustom(options, chunk, nType, outer)` substitutes for the normal subtree rendering of a node type;
- applying `plainCustom` to a word, line, or other container can therefore hide descendants rather than merely decorate them;
- `prettyCustom` mutates the stable class dictionary for a node without rebuilding the graph hierarchy;
- custom methods are discovered from `app.customMethods`.

The main safety conclusion is that any `plainCustom` implementation in #42 must be **sign-local only**. It must never reconstruct words or lines from scratch. Container-level semantic decoration should use class hooks, not replacement rendering.

## Existing app integration constraint

`app/app.py` now contains the reviewed TLHdig upstream-link adapter from #41. #42 must extend the same `TfApp` rather than replace it. In particular it must preserve:

- the existing `__init__` web-link installation;
- `reinit()` restoring the custom link wrapper after Text-Fabric reuse;
- the `TLHdig ↗` browser action and ambiguity policy.

Renderer registration must coexist with these lifecycle hooks and be independently testable.

## Presentation semantics

The current CSS already anticipates Hittitological states such as Sumerograms, Akkadograms, determinatives, damage and editorial intervention, but stock Text-Fabric markup does not expose the required feature-value classes. That is the actual integration gap: the corpus already models the semantics; the app does not expose stable DOM hooks for them.

A renderer should distinguish at least these dimensions without changing the underlying text:

1. writing-system/function states: `sgr`, `agr`, `det`, `num`;
2. preservation/editorial states: `missing`, `laes`, `ras`, `add`;
3. additional annotation presence: `corr`, `subscr`, `materlect`, `surplus`.

Overlapping states must remain simultaneously visible in markup. Styling must not rely on color alone, and the plain textual content must stay readable if CSS is unavailable.

## What #42 must not do

- parse AOxml or source markup again;
- mutate feature values or TF schema;
- choose among competing morphological analyses;
- invent brackets or editorial notation not represented by the corpus contract;
- reconstruct cuneiform from transliteration;
- use raw feature values as HTML/CSS tokens;
- register replacement renderers on word/line/container types;
- break the upstream-link adapter from #41;
- turn optional provenance into a renderer dependency.

## Research conclusion

The minimum justified implementation is a thin, sign-local Text-Fabric rendering adapter that emits escaped `sym`/`after` text plus a fixed set of stable semantic classes derived from existing sign features. It should layer all active states, preserve the stock hierarchy and line-level cuneiform format, and leave morphology/provenance untouched.
