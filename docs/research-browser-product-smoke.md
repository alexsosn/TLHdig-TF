# Research: Text-Fabric browser product smoke

Issues: #135, informing #44 and #45.

## Question

What must be demonstrated before TLHdig-TF can call the Text-Fabric browser a supported pre-alpha user entry point, rather than merely saying that `app/config.yaml` is syntactically compatible with the corpus?

This is product/integration research. It does not change corpus data or app behavior.

## Upstream Text-Fabric 13.1 browser contract

The repository pins Text-Fabric 13.1.0. Current official Text-Fabric documentation establishes:

- the browser command is **`tf org/repo`**, so the TLHdig-TF command is `tf alexsosn/TLHdig-TF`; the older #44 wording `text-fabric ...` is not the documented CLI;
- `python -m tf.browser.start` is the underlying equivalent;
- `-noweb` starts the server without opening a desktop browser, which is appropriate for automated startup probing;
- the browser is a local Flask application backed by the same advanced app API;
- browser routes include `/sections`, `/tuples` and `/query` (plus indexed variants), so server behavior can be exercised without image-based GUI automation;
- browser search uses ordinary Text-Fabric search templates, the same query model available through the API;
- app/data resolution supports local/clone/release/commit modes; with the default empty checkout, Text-Fabric can fall back from local data to an online release or, if no release exists, the latest online commit.

References:

- <https://annotation.github.io/text-fabric/tf/about/browser.html>
- <https://annotation.github.io/text-fabric/tf/browser/start.html>
- <https://annotation.github.io/text-fabric/tf/browser/web.html>
- <https://annotation.github.io/text-fabric/tf/about/datasharing.html>
- <https://annotation.github.io/text-fabric/tf/about/searchusage.html>

## Current TLHdig-TF browser surface

### App configuration exists and targets the current artifact

`app/config.yaml` declares `provenanceSpec.relative: /tf` and `version: "0.4.0"`. It defines the default text format, section-navigation level, node displays, feature visibility and documentation targets. The custom `app/app.py` provides the reviewed TLHdig upstream-link adapter and sign renderer.

This is necessary but not sufficient evidence of usability.

### Existing tests are mostly below the product boundary

The repository already has useful component coverage:

- `programs/check_app.py` statically compares config node types/features/default format/version with the shipped TF files;
- `programs/tests/test_tlhdig_weblink.py` exercises custom upstream-link semantics and `TfApp` discovery;
- `programs/tests/test_hittitological_renderer.py` exercises renderer helpers/hooks and escaping;
- feature-doc checks cover generated app-facing documentation;
- current build validation invokes the app config gate.

These tests can all be green while a clean user still cannot start the browser, acquisition selects the wrong data, startup exhausts memory, a documented query fails, a browser route raises 500, or a page is technically non-empty but unusable.

### Documentation does not yet define a supported browser journey

There is no `docs/browser.md` on current `main`. The README says an app/browser configuration exists, but direct selective `Fabric` is still the only fully spelled-out deterministic quick start. `docs/AGORA-INTEGRATION.md` distinguishes direct `Fabric` from app/browser loading but is integration documentation, not a first-user browser guide.

### Resource guidance is stale for browser use

The README correctly labels the historical ~5 GB `loadAll()` observation as an old 0.1.0 measurement, not a current 0.4.0 benchmark. There is no current cold/warm browser baseline for startup time, cache/disk consumption or peak RSS. Therefore there is currently no evidence-backed answer to "will the browser fit comfortably on an ordinary laptop?"

## Product-quality model

Browser support has four distinct layers. A green lower layer must not be treated as proof of a higher layer.

| Layer | What it proves | Current state |
|---|---|---|
| configuration | app names real features/types/formats and correct TF version | covered by `check_app.py` |
| app/load | clean `use()`/browser acquisition resolves current core TF and no provenance dependency | not systematically clean-cache tested |
| HTTP/browser | server starts and representative `/sections`/`/query` requests return valid content | no permanent end-to-end gate identified |
| user journey | a researcher can find/read a passage, run useful queries, inspect results, follow docs/source links, and understand limitations | not frozen/tested as a support contract |

This four-layer distinction should govern #44/#45.

## Required clean-user scenarios

The research target should be a fresh temporary home/cache, not the maintainer's normal TF directories. At minimum measure two acquisition modes:

1. **online cold cache**: `tf alexsosn/TLHdig-TF -noweb` (or equivalent lower-level setup) with an empty TF cache/home and normal network access, proving what a new user receives;
2. **repository/local deterministic**: browser/app setup against a checked-out current artifact, with network disabled after checkout, proving that app behavior itself does not depend on live TLHdig or hidden cache state.

Repeat the second launch with a warm TF compiled cache. Cold/warm are different product experiences and should be reported separately.

The optional `tf-provenance/0.4.0` module must not be loaded by the ordinary browser path; its large source-fidelity features are validation/research data, not a prerequisite for reading/searching.

## Representative user journeys

Use stable semantic expectations rather than raw node numbers or giant HTML snapshots.

### Reading/navigation

- open a known ordinary passage such as `KUB 21.8 / Vs. II / 1′` and require non-empty transliteration;
- navigate document → column → line through browser section controls;
- expand/pretty-render a result and verify custom Hittitological sign classes are present for a selected fixture/example where the graph contains the state;
- verify the separate `TLHdig ↗` action on an unambiguous document/descendant;
- verify an ambiguous duplicate-`docid` record does not silently link to an arbitrary upstream record;
- exercise a currently known unaddressable/missing-line-number case as an explicit limitation until #15 resolves it.

### Search

Choose queries that exercise distinct graph semantics and have stable `>0`/shape expectations rather than freezing total counts unnecessarily:

- lexical/morphological: an `analysis` query for a known attested lemma;
- ambiguity: a `word` with more than one `analysis`;
- editorial/damage: `cluster type=del` with a non-zero width or an equivalent graph relation;
- structural/document: a query constrained to document/line context;
- optionally cuneiform: a line/sign query requiring `cu_sign`/alignment, but only if the query is documented with the alignment-confidence limitation.

For each documented example, the same template should be executable through the programmatic search API and through the browser query route. Browser-specific assertions should check successful rendering of the results, not reimplement the TF search engine.

## Browser/server test boundary

### Prefer deterministic route tests over full GUI automation

Text-Fabric already uses Flask. The highest-value deterministic test is to instantiate the pinned browser web app against the current local corpus and use its test client to exercise the same endpoints the UI submits:

- root/index page;
- `/sections` for a known section;
- `/query` for representative queries;
- app-specific static asset route(s).

This catches route/template/kernel integration errors that `A.pretty()` alone cannot.

Do **not** introduce Selenium/Playwright merely to prove that a button can be clicked. Add real browser automation only if research finds a critical behavior implemented exclusively in client-side JavaScript and not observable through Flask routes/state.

### One real process smoke remains valuable

A slower smoke should launch `tf alexsosn/TLHdig-TF -noweb` (or `python -m tf.browser.start ... -noweb`) in a subprocess with a fresh cache, wait for the listening URL, issue one HTTP request, then terminate cleanly. This proves CLI → acquisition → load → server wiring as a product path.

Because cold acquisition is network- and GitHub-dependent, it should not necessarily run on every ordinary PR. A local-artifact process smoke can be required CI; a true online-empty-cache acquisition smoke can be scheduled/manual or run on changes to distribution/app wiring.

## Performance measurement

Measure rather than invent pass/fail limits:

- wall-clock until server ready;
- peak RSS of the server process/tree;
- bytes downloaded on cold acquisition if practical;
- resulting TF cache size and compiled-cache size;
- warm startup time and peak RSS;
- latency of one section request and each representative query;
- result count for context only, not automatically as a compatibility promise.

Record OS, Python, Text-Fabric version and commit. Initial measurements are baselines. CI should fail on correctness; performance regression thresholds should be added only after repeated measurements establish noise and an acceptable budget.

## What should not be required

- live `hethport.net` availability: URL construction is locally testable and the upstream edition is external;
- optional provenance module;
- historical pre-alpha TF versions;
- exact pixel screenshots as the primary regression oracle;
- loading every optional feature merely because it exists;
- fixed query result counts unless the count itself is the intended corpus invariant.

## Research conclusions

1. #44 contains a stale CLI spelling and must be corrected to `tf alexsosn/TLHdig-TF` before it becomes user documentation.
2. `check_app.py` is a configuration gate, **not** an end-to-end browser smoke.
3. The support contract should be tested at four layers: config, app/load, HTTP/browser, user journey.
4. Required CI should be deterministic and offline with respect to TLHdig; clean-online acquisition is a separate slower product smoke.
5. Flask route testing plus one subprocess startup smoke gives stronger and less brittle coverage than adopting browser automation by default.
6. Browser performance needs a current 0.4.0 cold/warm baseline before limits are chosen.
7. #16 and #15 remain real browser limitations: duplicate document identities and unnumbered lines must be represented as explicit limitations/fail-closed behavior, not hidden by smoke fixtures that use only ideal documents.
8. #76/#78 improve reading quality but are not prerequisites for proving that the generic TF browser can start, navigate and search the current corpus.
