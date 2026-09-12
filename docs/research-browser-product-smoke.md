# Research: Text-Fabric browser product smoke

Issues: #135, informing #44, #45, and #47.

## Question

What must be demonstrated before TLHdig-TF can call the Text-Fabric browser a supported pre-alpha user entry point, rather than merely saying that `app/config.yaml` is compatible with the corpus?

This is product/integration research. It does not change corpus data or app behavior.

## Pinned Text-Fabric contract

TLHdig-TF pins Text-Fabric **13.1.0**. The matching upstream source commit inspected for this research is `0c45c386916cb52be84098796ec27ce97e5bf9fc`; its `tf/parameters.py` and `setup.cfg` both identify 13.1.0.

The pinned source establishes:

- the installed browser executable is `tf`;
- an app checkout specifier follows the app name, e.g. `org/repo:clone` or `org/repo:hot`;
- the main-data checkout specifier is the separate `--checkout=...` argument;
- `clone` uses the local repository under the standard `~/github/<org>/<repo>` layout;
- `hot` uses/checks the latest online commit;
- `latest` uses/checks the latest online release;
- the default empty checkout may use an available local/downloaded copy and otherwise resolves through the normal online release/commit machinery;
- `-noweb` starts the server without opening a desktop browser;
- `tf.browser.web.setup(debug, *args)` parses the same app/data arguments as the CLI, calls `findApp()`, creates the TF kernel, and returns the actual Flask app;
- the Flask app exposes `/`, `/sections`, `/tuples`, `/query`, `/passage`, and `/data/static/...` routes;
- request parsing is explicit in `tf.browser.servelib.getFormData()`: browser query text is the `query` form field and passage navigation uses `sec0`, `sec1`, `sec2` plus the normal display fields.

This gives #45 a faithful deterministic test seam: use the **real 13.1 `tf.browser.web.setup()`** and its Flask test client, not a synthetic web wrapper.

Upstream references:

- <https://annotation.github.io/text-fabric/tf/about/browser.html>
- <https://annotation.github.io/text-fabric/tf/browser/start.html>
- <https://annotation.github.io/text-fabric/tf/about/datasharing.html>
- pinned `tf/browser/web.py`, `tf/browser/serve.py`, `tf/browser/servelib.py`, `tf/browser/command.py` and `tf/docs/about/usefunc.md` at the source commit above.

## Current TLHdig-TF browser surface

### App configuration exists and targets current main

On current `main`, `app/config.yaml` declares `provenanceSpec.relative: /tf` and version `0.4.0`. It defines the default text format, section-navigation level, node displays, feature visibility and documentation targets. `app/app.py` supplies the reviewed `TfApp`, safe `TLHdig ↗` adapter and sign renderer.

### Existing tests remain mostly below the product boundary

The repository already has useful component coverage:

- `programs/check_app.py` checks config types/features/default format/version against shipped TF files;
- `test_tlhdig_weblink.py` exercises the custom source-link policy and `TfApp` discovery;
- `test_hittitological_renderer.py` exercises renderer hooks and escaping;
- generated feature-doc checks cover app-facing feature documentation.

All can be green while a first user still receives stale data, cannot launch the server, sees an HTTP 500, runs a documented query that fails, or incurs unacceptable startup memory.

### There is no supported browser manual yet

There is no `docs/browser.md` on current `main`. The README spells out direct selective `Fabric`, but not a verified clean-user browser journey. `docs/AGORA-INTEGRATION.md` describes integration paths, not first-user browser operation.

### Current browser resource guidance is unmeasured

The README deliberately labels the historical ~5 GB observation as an old 0.1.0 `loadAll()` measurement. There is no current 0.4.0 cold/warm browser startup, peak-RSS, cache-size or representative-query baseline.

## Adversarial review iteration 1: default acquisition is a blocker

The first review challenged the assumption that `tf alexsosn/TLHdig-TF` necessarily means **current main**. It does not.

GitHub currently exposes an older release:

- tag/release: `tlhdig-0.3_tf-0.2.0`;
- release assets: none;
- the tag's own `app/config.yaml` declares `provenanceSpec.version: "0.1.0"`;
- current `main` declares version `0.4.0`.

Text-Fabric treats app checkout and data checkout independently and can prefer release-backed/downloaded material under default checkout semantics. Therefore the bare command cannot presently be advertised as a proof that a clean user receives the one supported current 0.4.0 artifact.

This is a **real #47 acquisition/distribution defect**, not a browser-rendering defect.

### Consequence for current pre-alpha support

Until #47 aligns default distribution with the one current artifact, distinguish these modes explicitly:

**Current online development state**

```bash
tf alexsosn/TLHdig-TF:hot --checkout=hot
```

Both app and data are requested from the latest online commit. This matches the moving-main pre-alpha policy but intentionally does not promise stable historical bytes.

**Deterministic local checkout**

```bash
tf alexsosn/TLHdig-TF:clone --checkout=clone
```

when the repository is present at Text-Fabric's standard `~/github/alexsosn/TLHdig-TF` clone location. This is the preferred required-CI/browser-development path because it is offline after checkout and cannot silently select an older release.

**Bare/default command**

```bash
tf alexsosn/TLHdig-TF
```

must remain a **distribution diagnostic**, not the documented current-corpus command, until an empty-cache test proves it resolves the same `TF_VERSION`/artifact as current main.

The same distinction applies to `use()`.

## Product-quality model

Browser support has four distinct layers. A green lower layer is not evidence for a higher one.

| Layer | What it proves | Current state |
|---|---|---|
| configuration | app names real types/features/formats and the expected version | substantially covered by `check_app.py` |
| acquisition/app load | selected checkout really resolves current core TF and not optional provenance | not systematically clean-cache tested |
| HTTP/browser | real TF Flask setup/routes can read and search without server errors | no permanent end-to-end gate |
| researcher journey | a user can read, search, inspect results, follow source/docs links and understand known limitations | not frozen/tested |

## Clean-user scenarios

Tests must isolate Text-Fabric state rather than inherit the maintainer's cache.

### Required deterministic scenario

Create an isolated temporary home, place or link the checked-out repository at its standard `~/github/alexsosn/TLHdig-TF` location, and launch app+data with `:clone --checkout=clone`. No network should be necessary after the checkout exists.

Repeat once with no compiled TF cache and once warm. This separates first local compilation/load cost from normal repeated use.

### Online current-main scenario

With empty TF download/cache state, exercise `:hot --checkout=hot`. This verifies the current moving-main acquisition path but depends on GitHub and belongs in a slower distribution smoke, not necessarily every PR.

### Bare/default distribution diagnostic

With empty state, exercise the bare app name and record the app/data commit/release/version actually selected. Before #47 is complete, the expected research result may be **not current**; the test must report that clearly rather than silently passing because some corpus loaded.

The ordinary browser must never require `tf-provenance/0.4.0`; provenance-only `srcxml`/`src_span` belong to optional validation/research use.

## Representative researcher journeys

Use semantic expectations rather than raw node IDs or full-page snapshots.

### Reading/navigation

- open a verified ordinary section such as `KUB 21.8 / Vs. II / 1′` and require non-empty transliteration;
- navigate document → column → line;
- verify corpus-specific rendering on a stable state-bearing example;
- preserve internal navigation and expose `TLHdig ↗` only for an unambiguous mapping;
- include one duplicate-document case from #16 and one missing-line-address case from #15 as explicit fail-closed/known-limit behavior.

### Search

Freeze small stable query classes, each executed both programmatically and through the real `/query` route:

- morphology/lexicon: known attested `analysis` lemma;
- ambiguity: a word with multiple analyses;
- editorial state: a non-zero-width `cluster type=del` or equivalent stable fixture;
- document/line structure;
- optionally aligned cuneiform, only with the documented alignment-confidence caveat.

Assert successful execution, non-empty/expected result shape and readable rendering. Avoid public contracts on current aggregate counts unless the count is itself the invariant.

## Exact browser test seam

The independent review rejected a vague “Flask test-client” plan because a home-grown request could differ from real TF behavior. The pinned source resolves this:

```python
from tf.browser.web import setup
webapp = setup(False, "alexsosn/TLHdig-TF:clone", "--checkout=clone")
client = webapp.test_client()
```

The test environment must make the current repository available under the isolated clone root expected by TF. Requests must use the actual form fields consumed by `getFormData()`.

Exercise at least:

- `GET /`;
- `POST /passage` or the exact browser passage flow with `sec0/sec1/sec2`;
- `POST /query` with `query=<template>`;
- `/data/static/...` for an app-specific asset.

If pinned 13.1 setup requires additional normal form values, derive them from `getFormData()`/interface defaults rather than inventing an alternate endpoint contract.

This is stronger and less brittle than full GUI automation. Add Playwright/Selenium only if a reviewed test gap is genuinely client-JavaScript-only.

## Real process smoke

A separate slower smoke should start the actual `tf ... -noweb` subprocess, wait for the listening URL, fetch localhost, and terminate the whole process tree cleanly.

Measure the process smoke separately for:

- local clone/offline mode;
- online `hot` cold acquisition;
- bare/default resolution as a distribution diagnostic.

Do not mix network download time into local browser-load performance and then treat it as renderer performance.

## Performance evidence

Record before setting thresholds:

- OS/runner, Python, TF 13.1.0, TLHdig-TF commit and TF version;
- acquisition mode (`clone`, `hot`, bare/default);
- wall time to server ready;
- peak RSS of the process tree;
- bytes/cache footprint before/after where practical;
- warm startup time;
- latency of root, one passage and representative queries.

Initial values are baselines, not pass/fail budgets. OOM, crash and hard timeout remain correctness failures. Add numerical regression budgets only after repeated measurements establish noise.

## Research conclusions after review iteration 1

1. #44's `text-fabric ...` spelling is stale; the executable is `tf`.
2. More importantly, **bare `tf alexsosn/TLHdig-TF` is not currently a defensible current-0.4.0 support contract** because an old GitHub release exists.
3. #47 must own alignment of default TF acquisition with the one current artifact. Until then, browser documentation should use explicit `hot` for current online main and `clone` for deterministic local use.
4. `check_app.py` remains a configuration gate, not an end-to-end browser smoke.
5. The pinned 13.1 `tf.browser.web.setup()` plus Flask test client is the exact deterministic HTTP/browser seam; form fields come from `getFormData()`.
6. Required CI should use isolated clone/offline state and must not contact live TLHdig.
7. Online `hot` empty-cache acquisition belongs in a slower distribution smoke; bare/default acquisition is separately checked for distribution correctness.
8. Browser performance needs a current cold/warm baseline before thresholds exist.
9. #15/#16 must appear in the smoke matrix as known fail-closed limitations; happy-path-only fixtures are insufficient.
10. #76/#78 improve reading quality but do not block proving generic browse/search usability.
