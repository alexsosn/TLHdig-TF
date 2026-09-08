# Plan: sign-local Hittitological Text-Fabric renderer

Issue: #42

Research: `docs/research-hittitological-renderer.md`

## User contract

In normal transliteration displays, Text-Fabric should expose the Hittitological semantics already present on sign nodes instead of rendering every sign identically. Sumerograms, Akkadograms, determinatives, numerals, damage/lacuna states, erasures, additions, corrections and rarer editorial annotations must be represented by stable semantic markup while the readable transliteration itself remains unchanged.

The renderer must preserve the existing TLHdig source-link behavior, the graph, cuneiform format, competing morphology and optional provenance contract.

## Architecture

Extend the existing `TfApp` in `app/app.py`; do not create a second app class or replace the #41 lifecycle logic.

### Pure state extraction

Add a pure-ish helper over the loaded TF API:

`sign_state_classes(app, node) -> tuple[str, ...]`

It returns only names from a fixed app-owned class vocabulary:

- `tlh-sgr`
- `tlh-agr`
- `tlh-det`
- `tlh-num`
- `tlh-missing`
- `tlh-laes`
- `tlh-ras`
- `tlh-add`
- `tlh-corr`
- `tlh-subscr`
- `tlh-materlect`
- `tlh-surplus`

For `sgr`, `agr`, `det`, and `num`, string/integer zero is false; merely having the feature loaded is not enough. Sparse annotation features are active when they carry a non-empty value. Missing/unloaded optional feature objects must not crash rendering.

The helper returns every active state, not a precedence-selected state.

### Plain rendering

Register `plainCustom` **only for `sign`**.

The bound sign renderer receives Text-Fabric's `options`, obtains the stock text for that sign using the requested `fmt`, HTML-escapes it, and wraps it in one span with:

- the Text-Fabric format class from `app.context.formatCls`;
- `tlh-sign`;
- all active fixed semantic classes when the requested format is transliteration (`text-orig-*` / `text-trans-*`).

For non-transliteration formats it preserves the requested stock text but does not add transliteration/editorial semantic classes. It must not synthesize cuneiform or fall back to `sym` when the requested format has no sign-level text.

This keeps `sym`/`after` handling in Text-Fabric's existing text-format machinery rather than duplicating the converter's separator logic.

### Pretty rendering

Register `prettyCustom` only for `sign`. It adds `tlh-sign` and the same stable semantic classes to the sign container/label class context so the normal pretty renderer keeps responsibility for text, feature display and hierarchy.

No word, line, document or other container gets a replacement renderer.

### Lifecycle

Add `_install_renderer()` alongside `_install_tlhdig_weblink()`.

- `__init__`: after `super().__init__`, install the link adapter and renderer hooks when an API exists.
- `reinit()`: reinstall both integrations after Text-Fabric reuse/reset.

The two adapters must not overwrite one another.

## CSS contract

Replace the current “not styled yet” comment with selectors for the exact `tlh-*` classes emitted by the app.

CSS goals:

- Sumerogram/Akkadogram/determinative/numeral remain distinguishable without changing text content;
- missing/damaged/erased/added states have non-color cues (e.g. opacity, decoration, border/background/text treatment as appropriate);
- corrections and rare annotation states are visible but subordinate;
- overlapping classes compose rather than one rule erasing another;
- styling remains legible in light/dark browser themes;
- no per-node inline style or raw feature value becomes a selector.

The tests assert selector/markup correspondence, not pixel appearance.

## RED gate

Commit failing tests before any production renderer/CSS changes. Required cases:

1. custom app still discovers `TfApp` and retains the #41 `webLink` adapter;
2. renderer hooks are registered for `sign` only;
3. ordinary sign text and separator remain unchanged;
4. explicit integer/string `0` for `sgr`/`agr`/`det`/`num` does not activate a class;
5. active writing-system flags emit their fixed classes;
6. missing/laes/ras/add emit fixed classes;
7. corr/subscr/materlect/surplus emit presence classes without exposing raw values as class names or HTML;
8. overlapping states emit all classes;
9. hostile `sym`/text such as `<script>` is escaped;
10. a non-transliteration/cuneiform format is not replaced with transliteration and receives no transliteration semantic classes;
11. missing feature APIs fail gracefully rather than crashing;
12. `reinit()` reinstalls both renderer and upstream-link integrations;
13. stylesheet contains selectors for every emitted semantic class and no longer claims the renderer is absent.

Where a real Text-Fabric fixture can exercise `plain()`/`pretty()` cheaply, prefer it over tests that merely call helpers directly.

## GREEN implementation limits

Production changes are limited to:

- `app/app.py` renderer helpers/hook installation;
- `app/static/display.css` semantic styling;
- tests and, if justified, the lightweight research census.

No TF artifact rebuild, schema feature, parser/converter edit, corpus patch, app version change, morphology policy or provenance module change belongs in #42.

## Test gate

After ticket-local GREEN:

- run full `programs/tests`;
- run `programs/check_app.py`;
- run generated feature-doc drift check;
- run the renderer research census as a sanity check against 0.3.0;
- run the complete existing hosted corpus CI before finalization.

A browser smoke may be added if the unit/real-TF fixture cannot prove hook execution through Text-Fabric's actual rendering path. Normal CI must not require upstream TLHdig availability.

## Independent adversarial review

A fresh review context must try to falsify:

- hook scope accidentally replacing word/line descendants;
- explicit-zero flags treated as true;
- HTML injection from sign or annotation values;
- raw annotation values leaking into CSS classes;
- loss/change of `after` separators;
- semantic styling applied to cuneiform or unrelated formats;
- failure with partially loaded feature sets;
- incompatibility with Text-Fabric 13.1 `plainCustom`/`prettyCustom` signatures;
- `reuse()` losing either renderer or #41 web links;
- overlapping classes producing unreadable output;
- CSS selectors that the app never emits;
- hidden graph/schema/provenance changes.

Any blocking finding restarts implementation → test → logically independent review.
