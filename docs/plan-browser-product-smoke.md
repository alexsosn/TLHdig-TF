# Plan: supported Text-Fabric browser product smoke

Issues: #135, implementing later through #44, #45 and acquisition work in #47.

This is implementation-free. It freezes the product contract and test architecture after research plus three adversarial review iterations.

## No browser command is promoted to supported without a clean-state smoke

Do **not** currently advertise bare `tf alexsosn/TLHdig-TF` as the supported current-corpus command. An older GitHub release exists, so default Text-Fabric resolution is not proven to select current `tf/0.4.0`.

Pinned Text-Fabric research establishes the semantics of two explicit candidate commands; it does **not** yet establish that either is a usable TLHdig-TF product path. #45 must prove them empirically before #44 documents them as supported.

### Candidate A — current online development corpus

```bash
tf alexsosn/TLHdig-TF:hot --checkout=hot
```

Upstream TF semantics say this requests the latest online commit for both app and main data. It is the correct candidate for the project's moving-main pre-alpha policy, but remains provisional until an empty-cache smoke proves that TLHdig-TF actually acquires, loads, serves and searches successfully with acceptable resource behavior.

### Candidate B — deterministic local checkout

With the repository at Text-Fabric's standard clone location `~/github/alexsosn/TLHdig-TF`:

```bash
tf alexsosn/TLHdig-TF:clone --checkout=clone
```

Upstream TF semantics say app and data come from that clone without online checkout. It is the preferred candidate for CI/development, but remains provisional until the isolated-home smoke proves the real TLHdig-TF browser starts and works.

### Bare/default command

```bash
tf alexsosn/TLHdig-TF
```

is a distribution diagnostic only. It may become the preferred first-user command only after #47 proves from an empty cache that it resolves the same current artifact/version as supported main.

### Allowed outcomes of #45

The RED/implementation work must permit evidence to choose among these outcomes rather than forcing a preselected answer:

1. `clone` and `hot` both pass → document both, with `hot` as current-online and `clone` as deterministic-local;
2. `clone` passes but `hot` acquisition is broken/impractical → document local browser support only and keep #47 open for online distribution;
3. neither passes → do **not** advertise the TF browser as supported yet; keep direct selective `Fabric` as the user path and file/fix the measured blockers;
4. after #47, bare/default also passes and resolves current → simplify docs to the bare command while retaining explicit checkout modes for reproducibility/development.

For automation append `-noweb`, or call pinned `python -m tf.browser.start ... -noweb` when subprocess control requires it.

The browser is a **local** interface, not a hosted TLHdig replacement. Ordinary browser loading must not pull `tf-provenance/0.4.0`.

## Critical test-harness rule: isolate HOME before importing Text-Fabric

Pinned TF 13.1 computes its home directory at module import time in `tf.core.files`:

```python
_tildeDir = normpath(os.path.expanduser("~"))
_homeDir = _tildeDir  # except the iPad special case
```

Therefore `monkeypatch.setenv("HOME", ...)` after `import tf` is **not** a clean-cache test.

Every Layer 2/3 test that claims clean home/cache isolation must:

1. create a fresh temporary home;
2. arrange the exact repository checkout at `$HOME/github/alexsosn/TLHdig-TF`;
3. start a fresh child Python interpreter with `HOME` (and platform-equivalent home variables if needed) set in its environment;
4. import Text-Fabric **only inside that child after the environment is set**;
5. run the app/browser probe in the child;
6. emit compact JSON or another machine-readable result to the parent test;
7. assert reported app/data/cache paths live under the isolated home and the selected `TF_VERSION` is current.

If the child reveals that TF uses another path source on a supported platform, add that platform's isolation variable/path explicitly. Do not solve this by deleting the maintainer's real cache.

Layer 4 remains a separate real-CLI subprocess proof even though Layers 2/3 also use a child interpreter for isolation.

## Four test layers

### Layer 1 — static app contract

Keep fast ordinary-CI checks for:

- `app/config.yaml` version equals `TF_VERSION`;
- configured types/features/formats exist;
- `TfApp` is discoverable;
- referenced app static files and generated feature docs exist;
- no ordinary browser declaration requires provenance-only features;
- user-facing browser documentation contains only commands already proven by the corresponding acquisition smoke.

### Layer 2 — exact local app/load contract

Inside the import-safe isolated child described above, attempt app and data load explicitly with `clone` semantics. The test is allowed to expose a blocker; success requires:

- selected app/data are the exact checkout/current `TF_VERSION`;
- reported app/data/cache paths are below the temporary home, not the runner's real home;
- no previously downloaded/release cache is consulted;
- provenance-only `srcxml`/`src_span` are absent from ordinary browser load;
- default text renders a known passage non-empty;
- canonical programmatic query fixtures execute;
- duplicate-document upstream links remain fail-closed.

Run once without compiled TF cache and once warm where runtime permits.

### Layer 3 — exact HTTP/browser contract

Inside the same kind of fresh child process, use the real pinned Text-Fabric 13.1 setup seam, not a synthetic Flask wrapper:

```python
from tf.browser.web import setup
webapp = setup(
    False,
    "alexsosn/TLHdig-TF:clone",
    "--checkout=clone",
)
client = webapp.test_client()
```

Requests must use fields actually consumed by `tf.browser.servelib.getFormData()`.

Success requires:

1. `GET /` succeeds and identifies TLHdig-TF/current app;
2. passage navigation using the actual `sec0`, `sec1`, `sec2` form flow renders a verified ordinary passage;
3. `POST /query` with each canonical query returns `status=true`, non-zero/expected-shape results and renderable table content;
4. one expanded/pretty path contains stable corpus-specific semantic class/label evidence from the reviewed renderer;
5. `/data/static/...` serves a required TLHdig-TF asset;
6. no route requires live `hethport.net` access;
7. setup/load confirms optional provenance is absent;
8. child-reported resource paths prove the route test used the isolated clone/cache.

The child emits statuses, selected identity/path facts, result counts/shapes and selected semantic assertions to the parent. Do not snapshot complete HTML.

If a future TF upgrade changes `web.setup()` or the form contract, the integration test should fail explicitly and force re-research rather than silently switching to a home-grown browser path.

### Layer 4 — real process/clean-user smoke

Implement one subprocess harness that starts the actual executable rather than importing browser setup directly:

- start `tf ... -noweb` for the selected candidate mode;
- set an isolated home/cache environment **before process start**;
- wait for the server-ready signal/listening URL under a hard timeout;
- fetch localhost;
- terminate the full server process tree;
- record selected acquisition identity plus startup/RSS/cache evidence.

Run it in three distinct modes:

**clone/offline candidate** — exact current checkout, no network.

**hot/online candidate** — empty TF download cache, explicit `:hot --checkout=hot`.

**bare/default diagnostic** — empty state, bare app name; assert/report which release/commit/version was actually selected. Until #47 fixes distribution, this diagnostic may demonstrate that the default path is stale, but it must never be confused with current-browser success.

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

A future supported browser smoke remains green because limitations are handled honestly, not because it avoids every difficult document.

## RED phase for #45

After #135 merges, #45 enters RED. Cover at least:

1. unsupported/stale CLI spelling in browser docs;
2. bare/default acquisition resolving an artifact different from current `TF_VERSION`;
3. clean clone-mode setup depending on an existing maintainer cache;
4. a test that sets `HOME` after TF import and would therefore false-green — the production harness must prove import-safe isolation instead;
5. ordinary app load seeing provenance-only features;
6. default reading format empty on the stable passage;
7. `/passage` or actual section-navigation request failure;
8. `/query` parse/search/render failure for a documented template;
9. missing app static asset;
10. custom `TfApp`/renderer hook missing from real `web.setup()` path;
11. duplicate `docid` creating an unsafe arbitrary TLHdig link;
12. missing line address being represented as valid when it is not;
13. required browser startup attempting live TLHdig access;
14. subprocess server leaking after test completion;
15. browser docs claiming performance/resource guidance without current baseline evidence.

Reuse already-green lower-level renderer/link/config tests instead of duplicating them.

## Resource baseline protocol

Measure separately for `clone`, `hot`, and bare/default diagnostic. Never mix network download time into local renderer/load timing.

Record:

- OS/architecture/runner;
- Python and Text-Fabric version;
- TLHdig-TF commit and `TF_VERSION`;
- app checkout mode and data checkout mode;
- selected release/commit identity;
- effective app/data/cache paths;
- command start → server ready wall time;
- peak RSS of server process tree;
- TF download/compiled-cache footprint before/after;
- warm startup time;
- localhost latency for root, one passage and canonical queries.

First iteration establishes a baseline only. Do not invent a numeric regression threshold before repeated comparable measurements establish noise. Crash, OOM and hard timeout are correctness failures regardless.

## CI placement after candidate evaluation

### Required ordinary CI

Only move checks here once their candidate path has passed exploratory RED/implementation smoke:

- Layer 1 always;
- import-safe isolated Layer 2 if runtime is acceptable;
- import-safe isolated Layer 3 if runtime is acceptable;
- no live TLHdig requests.

### Current-artifact / app integration validation

Once a candidate is accepted, run its full deterministic browser smoke whenever corpus query-facing schema, current artifact, app config, custom app code or renderer changes.

### Scheduled/manual/distribution-change smoke

- online `hot` empty-cache acquisition if it proves viable;
- bare/default empty-cache distribution diagnostic;
- resource measurements too noisy/slow for normal PR CI;
- optional live TLHdig reachability sample, separate from deterministic URL-construction correctness.

## #44 documentation output

Create `docs/browser.md` only after #45 proves at least one candidate command. It should include only empirically supported paths.

If `hot` passes, document it as the current online pre-alpha path. If `clone` passes, document it as the deterministic local path. If neither passes, do not create a misleading launch guide; document the browser as not yet supported and keep the measured blockers visible.

When a browser path is supported, the page should also include:

- supported TF version/install prerequisite;
- what is acquired/cached on first launch;
- measured cold/warm resource guidance, separating acquisition from local startup;
- one tested passage journey;
- copy-pasteable tested morphology and damage searches;
- expansion/pretty-result behavior and `TLHdig ↗`;
- #15/#16 browser limitations;
- when selective direct `Fabric` is preferable;
- optional provenance is not loaded;
- troubleshooting via server terminal output.

README should link to the browser page rather than duplicate it.

## #47 distribution requirement surfaced by this research

#47 must explicitly test default empty-cache Text-Fabric resolution. Its browser/app distribution acceptance is:

> bare `use("alexsosn/TLHdig-TF")` / `tf alexsosn/TLHdig-TF` either resolve the same supported current `TF_VERSION` as main, or documentation explicitly requires a smoke-proven checkout specifier instead.

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

## Final independent review checklist

Re-attack the final plan for:

- checkout semantics being mistaken for empirical product success;
- bare/default release precedence leaking into a supposedly current test;
- HOME/cache isolation happening after TF import;
- child path evidence failing to prove isolation;
- `clone` tests not using the exact layout expected by TF;
- app and data checkout specifiers accidentally differing;
- `web.setup()` route tests submitting forms unlike the actual browser;
- route success with zero useful results;
- `A.pretty()` substituted for HTTP coverage;
- only ideal section fixtures, hiding #15/#16;
- provenance sneaking into load;
- network time confused with TF startup/search cost;
- server subprocess leaks;
- documentation promoting a command before its clean-state smoke passes.

Any blocking finding revises this plan again before #44/#45 RED implementation begins.
