# Plan: supported Text-Fabric browser product smoke

Issues: #135, implementing later through #44 and #45.

This plan is intentionally implementation-free. It freezes the product contract and test architecture after the research in `research-browser-product-smoke.md`.

## Supported pre-alpha browser contract

The supported interactive command is:

```bash
tf alexsosn/TLHdig-TF
```

For automation, use the equivalent no-browser startup form:

```bash
tf alexsosn/TLHdig-TF -noweb
```

or the pinned module entry point when subprocess control requires it:

```bash
python -m tf.browser.start alexsosn/TLHdig-TF -noweb
```

The browser is a **local** interface to the one current pre-alpha corpus. It is not a hosted replacement for TLHdig online. Normal browser loading must use the core `tf/0.4.0` artifact and must not require `tf-provenance/0.4.0`.

Direct selective `Fabric` remains the recommended low-memory Python path when a user does not need the interactive browser.

## Test architecture

Implement #45 as four explicit layers, so a failure identifies which user contract broke.

### Layer 1 — static app contract

Retain and extend existing cheap checks where necessary:

- `app/config.yaml` version equals `TF_VERSION`;
- configured types/features/formats exist on the current artifact;
- app Python module discovers `TfApp`;
- required static files and generated feature-doc targets exist;
- no browser/app declaration requires a provenance-only feature.

This layer should remain fast ordinary CI.

### Layer 2 — local app-load contract

Against a checked-out current artifact and isolated temporary TF/cache directories:

- instantiate the high-level app for the local repository/current data;
- assert the loaded version/path is the current `TF_VERSION`;
- assert provenance-only features such as `src_span`/`srcxml` are absent unless explicitly requested;
- require the default text format to render a known passage non-empty;
- require programmatic `A.search()`/`S.search()` for the documented query fixtures to succeed;
- require `A.webLink()` to preserve fail-closed duplicate-document behavior.

This is deterministic/offline after checkout and should be required CI if runtime is acceptable.

### Layer 3 — HTTP/browser contract

Instantiate Text-Fabric's pinned Flask browser app against the same local current artifact and use its Flask test client where supported by the pinned API.

Exercise:

1. index/root response is successful and contains the TLHdig-TF app identity;
2. section request for a known ordinary passage succeeds and contains non-empty reading material;
3. `/query` submission for each selected query returns a successful result page rather than a 500/error state;
4. at least one pretty/expanded result includes expected corpus-specific rendered semantics;
5. `/data/static/...` serves an app-specific asset required by rendering;
6. no request requires live TLHdig network access.

Do not snapshot entire HTML pages. Assert stable semantic strings/classes/links and response status.

If Text-Fabric 13.1 does not expose a stable enough setup/test-client seam, isolate the minimum adapter around its current `tf.browser` setup rather than mocking the whole browser. Pinning TF 13.1.0 makes use of its current internal seam acceptable, but the test must fail clearly when an upgrade changes that seam.

### Layer 4 — process/clean-user smoke

Create a slower script/check that:

- starts the actual browser CLI with `-noweb` in a subprocess;
- uses an isolated temporary home/cache configuration;
- waits for the announced/listening local URL with a hard timeout;
- fetches one page over localhost;
- terminates the server cleanly;
- records startup wall time and peak RSS where the platform permits;
- reports cache/disk footprint.

Provide two modes:

**local/offline mode** — data/app are supplied from the current checkout; required CI candidate.

**online/cold mode** — no pre-existing TF cache; normal GitHub acquisition semantics; scheduled/manual or distribution-change gate because it depends on external GitHub availability and transfer time.

The process smoke must not contact live TLHdig merely to start/read/search.

## Canonical user journeys

Freeze the following journey classes, but choose concrete corpus fixtures by semantic identity during RED work and record why each is stable.

### Journey A — read a passage

- navigate to `KUB 21.8 / Vs. II / 1′` or another verified stable ordinary address;
- reading is non-empty;
- document/column/line labels are visible;
- internal section navigation remains functional;
- an unambiguous node offers `TLHdig ↗` without replacing internal navigation.

### Journey B — morphology search

A documented TF search template finds at least one analysis of a stable attested lemma and rendered results expose lemma/gloss/morphology without selecting one candidate as uniquely authoritative when alternatives exist.

### Journey C — ambiguity

A query identifies a word with multiple analysis nodes. Expanded rendering exposes all relevant candidates in source/analysis-index order or the behavior already specified by the renderer contract. The smoke checks multiplicity, not an arbitrary corpus-wide total.

### Journey D — editorial/damage search

A query finds a non-zero-width `cluster type=del` (or equivalent stable damage fixture) and expanded context renders readable surrounding text. Point markers and damage extents must not be conflated.

### Journey E — known limitations

Exercise at least one duplicate-document identity and one unnumbered/missing-line-address case. The expected result is **explicit fail-closed/limitation behavior**, not forced successful navigation.

This prevents the browser test suite from proving only the happy path while known #16/#15 defects remain user-visible.

## RED phase for #45

Before implementation, add failing tests/checks demonstrating gaps in the current repository. The RED set should include at least:

1. stale/wrong browser CLI spelling in user-facing browser documentation;
2. no clean-cache launch proof;
3. app load accidentally seeing a provenance-only feature;
4. default reading format empty for the stable passage;
5. documented query rejected or returning browser error;
6. `/sections` route failure;
7. `/query` route failure;
8. missing required app static asset;
9. custom `TfApp`/renderer hook not active in browser setup;
10. duplicate `docid` producing an unsafe arbitrary TLHdig link;
11. a missing-line-address case being presented as successfully addressable when it is not;
12. browser startup depending on live `hethport.net`;
13. browser support docs missing current resource guidance/baseline.

Not every RED needs to fail for the same reason. Existing component tests may already satisfy some contracts; reuse them rather than duplicating assertions.

## Resource baseline protocol

The first implementation run records, separately for cold and warm modes:

- runner/OS and architecture;
- Python version;
- Text-Fabric version;
- TLHdig-TF commit and TF version;
- wall time: command start → server ready;
- peak RSS of the server process tree;
- current checkout size relevant to browser data;
- TF cache size before/after;
- localhost response latency for index, one section, and each canonical query.

Store a compact machine-readable JSON plus a human-readable report under `reports/` only if the measurement is reproducible enough to be useful. Otherwise retain CI log evidence and document a manually sampled range.

**No hard performance budget in the first iteration.** After at least several comparable measurements, create a separate regression threshold only if signal exceeds runner noise. A sudden crash/OOM/timeout remains a correctness failure even before a formal performance budget exists.

## CI placement

### Required ordinary CI

- Layer 1 static checks;
- deterministic local Layer 2 app load;
- deterministic Layer 3 Flask route/user-journey smoke, if runtime fits ordinary CI;
- no external TLHdig requests.

### Dataset/current-artifact validation

Run the full browser smoke when corpus/app changes alter the shipped artifact, app config, custom renderer or query-facing schema. This is the authoritative current-artifact integration proof.

### Scheduled/manual

- online empty-cache acquisition;
- resource benchmarking if too slow/noisy for every PR;
- optional live-TLHdig link reachability sampling, clearly separate from deterministic URL correctness.

## Documentation implementation under #44

Create `docs/browser.md` only after the RED/implementation proves the commands. It should include:

- installation prerequisite: pinned/supported Text-Fabric version;
- `tf alexsosn/TLHdig-TF` launch command;
- what is downloaded/cached on first launch;
- current measured cold/warm resource guidance;
- a known passage navigation example;
- copy-pasteable morphology and damage searches that are exercised by tests;
- how to expand/pretty-print results and follow `TLHdig ↗`;
- known duplicate-ID and unnumbered-line limitations;
- when to use selective Python `Fabric` instead of the browser;
- statement that provenance is optional and not loaded by the ordinary browser;
- troubleshooting pointer to terminal output when the browser returns an internal-server error.

README should link to this page rather than duplicating the complete browser manual.

## Implementation boundaries

- Do not build a TLHdig clone or another server framework.
- Do not add Playwright/Selenium unless a reviewed RED demonstrates an important client-only behavior that Flask/app tests cannot observe.
- Do not load optional provenance to make browser tests easier.
- Do not make required CI depend on external TLHdig uptime.
- Do not solve #15/#16 inside browser smoke; encode their present behavior and keep their owners explicit.
- Do not use full-page HTML snapshots as the primary oracle.
- Do not make raw node IDs or current aggregate query counts part of the public support contract unless separately justified.

## Review checklist

The independent review must attack:

- cache leakage that makes clean launch false-green;
- testing `A.pretty()` while never testing HTTP routes;
- route tests that bypass the same setup used by the CLI;
- query tests that merely assert parser success but render no results;
- fixtures chosen only from ideal documents, hiding #15/#16;
- provenance accidentally pulled into the browser;
- client-side behavior invisible to Flask tests;
- brittle HTML internals masquerading as product semantics;
- performance measurements dominated by network or CI-runner noise;
- startup tests that leave server processes behind;
- current-artifact mismatch between direct `Fabric`, `use()`, and browser paths;
- browser docs advertising a command not exercised from an empty cache.

Any blocking finding revises this plan before #44/#45 RED implementation begins.
