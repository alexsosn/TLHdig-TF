# Plan: supported Text-Fabric browser product smoke

Issues: #135, implementing later through #44, #45 and acquisition work in #47.

This is implementation-free. It freezes the product contract and test architecture after research plus adversarial review iteration 1.

## Support contract is conditional on acquisition mode

Do **not** currently advertise bare `tf alexsosn/TLHdig-TF` as the supported current-corpus command. An older GitHub release exists, so default Text-Fabric resolution is not proven to select current `tf/0.4.0`.

Until #47 aligns default acquisition, support two explicit pre-alpha modes.

### Current online development corpus

```bash
tf alexsosn/TLHdig-TF:hot --checkout=hot
```

This explicitly requests the latest online commit for both app and main data. It matches the project's moving-main pre-alpha policy.

### Deterministic local checkout

With the repository at Text-Fabric's standard clone location `~/github/alexsosn/TLHdig-TF`:

```bash
tf alexsosn/TLHdig-TF:clone --checkout=clone
```

This is the canonical CI/development browser path because app and data come from the exact checked-out repository and no network is needed after checkout.

### Future default command

```bash
tf alexsosn/TLHdig-TF
```

may become the preferred first-user command only after #47 proves from an empty cache that it resolves the same current artifact/version as supported main. The browser lane must not fix this by hiding release precedence inside custom app code.

For automation append `-noweb`, or call pinned `python -m tf.browser.start ... -noweb` when subprocess control requires it.

The browser remains a **local** interface, not a hosted TLHdig replacement. Ordinary browser loading must not pull `tf-provenance/0.4.0`.

## Four test layers

### Layer 1 — static app contract

Keep fast ordinary-CI checks for:

- `app/config.yaml` version equals `TF_VERSION`;
- configured types/features/formats exist;
- `TfApp` is discoverable;
- referenced app static files and generated feature docs exist;
- no ordinary browser declaration requires provenance-only features;
- user-facing browser documentation contains only commands currently proven by the corresponding acquisition smoke.

### Layer 2 — exact local app/load contract

Use an isolated temporary home. Put or link the exact checkout at its standard TF clone path:

```text
$HOME/github/alexsosn/TLHdig-TF
```

Load app and data explicitly with `clone` semantics. Assert:

- selected app/data are the exact checkout/current `TF_VERSION`;
- no previously downloaded/release cache is consulted;
- provenance-only `srcxml`/`src_span` are absent from ordinary browser load;
- default text renders a known passage non-empty;
- the canonical programmatic query fixtures execute;
- duplicate-document upstream links remain fail-closed.

Run once without compiled TF cache and once warm where runtime permits.

### Layer 3 — exact HTTP/browser contract

Use the real pinned Text-Fabric 13.1 setup seam, not a synthetic Flask wrapper:

```python
from tf.browser.web import setup
webapp = setup(
    False,
    "alexsosn/TLHdig-TF:clone",
    "--checkout=clone",
)
client = webapp.test_client()
```

The isolated environment must expose the current checkout at TF's standard clone path. Requests must use fields actually consumed by `tf.browser.servelib.getFormData()`.

Exercise:

1. `GET /` succeeds and identifies TLHdig-TF/current app;
2. passage navigation using the actual `sec0`, `sec1`, `sec2` form flow renders a verified ordinary passage;
3. `POST /query` with each canonical query returns `status=true`, non-zero/expected-shape results and renderable table content;
4. one expanded/pretty path contains stable corpus-specific semantic class/label evidence from the reviewed renderer;
5. `/data/static/...` serves a required TLHdig-TF asset;
6. no route requires live `hethport.net` access;
7. setup/load confirms optional provenance is absent.

Do not snapshot complete HTML. Assert HTTP status plus stable semantic content/classes/links and JSON fields.

If a future TF upgrade changes `web.setup()` or the form contract, the integration test should fail explicitly and force re-research rather than silently switching to a home-grown browser path.

### Layer 4 — real process/clean-user smoke

Implement one subprocess harness that:

- starts actual `tf ... -noweb`;
- sets an isolated home/cache environment;
- waits for the server-ready signal/listening URL under a hard timeout;
- fetches localhost;
- terminates the full server process tree;
- records selected acquisition identity plus startup/RSS/cache evidence.

Run it in three distinct modes:

**clone/offline** — exact current checkout, no network; candidate for required integration CI.

**hot/online** — empty TF download cache, explicit `:hot --checkout=hot`; slower distribution smoke.

**bare/default diagnostic** — empty state, bare app name; assert/report which release/commit/version was actually selected. Until #47 fixes distribution, this diagnostic is allowed to demonstrate that the default path is stale, but it must never be confused with current-browser success.

## Canonical researcher journeys

Concrete fixtures are selected during RED work by stable semantic identity, not raw node number.

### A — read a normal passage

Use `KUB 21.8 / Vs. II / 1′` or another independently verified stable section:

- non-empty transliteration;
- document/column/line context visible;
- internal navigation works;
- unambiguous node has separate `TLHdig ↗` action.

### B — morphology search

A documented query for a stable attested `analysis` lemma returns results whose rendering exposes lemma/gloss/morphology. If a word has competing analyses, the journey must not invent a uniquely authoritative candidate.

### C — ambiguity

A stable query/fixture reaches a word with multiple analysis nodes. Expanded rendering preserves multiplicity/order according to the existing renderer/data contract.

### D — editorial/damage search

A query reaches a non-zero-width `cluster type=del` or equivalent stable damage fixture and provides readable context. A point marker is not treated as a damaged span.

### E — known browser limitations

Include:

- one duplicate-document identity from #16: no arbitrary upstream link or silent record collapse;
- one missing/empty line address from #15: explicitly unavailable/fail-closed rather than fabricated.

The browser smoke must remain green because limitations are handled honestly, not because it avoids every difficult document.

## RED phase for #45

After #135 merges, #45 enters RED. Cover at least:

1. unsupported/stale CLI spelling in browser docs;
2. bare/default acquisition resolving an artifact different from current `TF_VERSION`;
3. clean clone-mode setup depending on an existing maintainer cache;
4. ordinary app load seeing provenance-only features;
5. default reading format empty on the stable passage;
6. `/passage` or actual section-navigation request failure;
7. `/query` parse/search/render failure for a documented template;
8. missing app static asset;
9. custom `TfApp`/renderer hook missing from real `web.setup()` path;
10. duplicate `docid` creating an unsafe arbitrary TLHdig link;
11. missing line address being represented as valid when it is not;
12. required browser startup attempting live TLHdig access;
13. subprocess server leaking after test completion;
14. browser docs claiming performance/resource guidance without current baseline evidence.

Reuse already-green lower-level renderer/link/config tests instead of duplicating them.

## Resource baseline protocol

Measure separately for `clone`, `hot`, and bare/default diagnostic. Never mix network download time into local renderer/load timing.

Record:

- OS/architecture/runner;
- Python and Text-Fabric version;
- TLHdig-TF commit and `TF_VERSION`;
- app checkout mode and data checkout mode;
- selected release/commit identity;
- command start → server ready wall time;
- peak RSS of server process tree;
- TF download/compiled-cache footprint before/after;
- warm startup time;
- localhost latency for root, one passage and canonical queries.

First iteration establishes a baseline only. Do not invent a numeric regression threshold before repeated comparable measurements establish noise. Crash, OOM and hard timeout are correctness failures regardless.

## CI placement

### Required ordinary CI

- Layer 1;
- local isolated Layer 2 if runtime is acceptable;
- Layer 3 using pinned `web.setup()` + Flask test client if runtime is acceptable;
- no live TLHdig requests.

### Current-artifact / app integration validation

Run the full deterministic clone-mode browser smoke whenever corpus query-facing schema, current artifact, app config, custom app code or renderer changes.

### Scheduled/manual/distribution-change smoke

- online `hot` empty-cache acquisition;
- bare/default empty-cache distribution diagnostic;
- resource measurements too noisy/slow for normal PR CI;
- optional live TLHdig reachability sample, separate from deterministic URL-construction correctness.

## #44 documentation output

Create `docs/browser.md` only after #45 proves the commands. It should state:

- supported TF version/install prerequisite;
- while default distribution is stale, `tf alexsosn/TLHdig-TF:hot --checkout=hot` as the current online pre-alpha command;
- local deterministic `:clone --checkout=clone` path for a clone in TF's standard location;
- bare command only after #47 makes its empty-cache resolution current;
- measured cold/warm resource guidance, explicitly separating acquisition from local startup;
- one tested passage journey;
- copy-pasteable tested morphology and damage searches;
- expansion/pretty-result behavior and `TLHdig ↗`;
- #15/#16 browser limitations;
- when selective direct `Fabric` is preferable;
- optional provenance is not loaded;
- troubleshooting via server terminal output.

README should link to the browser page, not duplicate it.

## #47 distribution requirement surfaced by this research

#47 must explicitly test default empty-cache Text-Fabric resolution. Its acceptance for browser/app distribution is:

> bare `use("alexsosn/TLHdig-TF")` / `tf alexsosn/TLHdig-TF` either resolve the same supported current `TF_VERSION` as main, or documentation clearly requires an explicit checkout specifier instead.

The old `tlhdig-0.3_tf-0.2.0` release must not silently become the supported current corpus merely because Text-Fabric can load something from it.

## Boundaries

- no second server/framework;
- no Playwright/Selenium unless a reviewed client-only behavior cannot be covered through the real Flask app;
- no provenance auto-load;
- no live TLHdig dependency in required CI;
- no fixing #15/#16 inside browser smoke;
- no full-page HTML snapshots as primary oracle;
- no raw node IDs or volatile aggregate counts in the public support contract;
- no release/certification machinery added merely to make browser smoke convenient.

## Independent review iteration 2 checklist

The revised plan must be re-attacked for:

- bare/default release precedence still leaking into a supposedly current test;
- isolated HOME that nevertheless reuses global `~/text-fabric-data` or `~/github` state;
- `clone` tests that do not use the exact checkout layout expected by TF;
- app and data checkout specifiers accidentally differing;
- `web.setup()` route tests submitting forms unlike the actual browser;
- route success with zero useful results;
- `A.pretty()` coverage substituted for actual HTTP coverage;
- only ideal section fixtures, hiding #15/#16;
- provenance sneaking into load;
- network time confused with TF startup/search cost;
- server subprocess leaks;
- distribution docs advertising bare command before #47 proves it.

Any blocking finding revises this plan again before #44/#45 RED work begins.
