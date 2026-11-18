# Reading and querying in the Text-Fabric browser

TLHdig-TF includes a **local** Text-Fabric browser for reading individual lines,
inspecting morphology and querying the current pre-alpha graph. It is not an
online hosted edition and does not replace the [original TLHdig](https://hethport.net/TLHdig/)
for manuscript consultation.

The browser is useful when you have enough memory to load the full high-level
application. For computational research on a laptop, the
[selective `Fabric` loading path](install.md) is
usually more practical.

## Local launch: verified app and HTTP routes

The following is the local clone layout used by the
[real TF 13.1 browser smoke](https://github.com/alexsosn/TLHdig-TF/actions/runs/44358055538).
First install the pinned `text-fabric==13.1.0` dependency using the single
[canonical installation guide](install.md), then create a local clone:

```bash
mkdir -p ~/github/alexsosn
git clone https://github.com/alexsosn/TLHdig-TF.git ~/github/alexsosn/TLHdig-TF
tf alexsosn/TLHdig-TF:clone --checkout=clone
```

The `:clone` app selector and `--checkout=clone` data selector are separate.
Both must point to the same checkout. The source/data files come from your
clone; the browser runs locally. On a previously cloned checkout, update the
repository before launching to get the current moving pre-alpha artifact.

The smoke uses the pinned Text-Fabric `tf.browser.web.setup()` and actual
Flask routes with a fresh isolated HOME, rather than a mock web server.
The app identity, version `0.4.0`, current source checkout and missing optional
provenance are checked. It verified home, passage, morphology-query and CSS
responses (all HTTP 200). A separate [real CLI-process and online release
smoke](https://github.com/alexsosn/TLHdig-TF/actions/runs/44378687539)
subsequently confirmed the published corpus can be acquired and served without
any local clone. Both runs used Ubuntu/Python 3.13, not every operating system.

### What to read and search

Open the passage navigator and select:

- **Document:** `KUB 21.8`
- **Column:** `Vs. II`
- **Line:** `1′`

This location is also used by the [tested Python section example](querying.md#resolve-a-section-and-read-text).
Navigation and transliteration come from the TF graph; the browser cannot
fill in unaddressed lines or infer absent readings.

In the query panel, enter:

```text
analysis lemma=wed=a-
```

On the smoke-tested current artifact this produced nonempty rendered results,
and candidate analyses remain distinct. The number of hits is not a fixed
corpus contract. The browser's normal condensation selector is part of its
query form. For querying damage rather than morphology, a useful pattern is:

```text
cluster type=del width>1
```

This restricts results to editorial spans with positive extent; point-like
markers should not be interpreted as equally sized damaged passages.
For direct Python searches and more elaborate concordances, see
[Querying](querying.md) and [Morphology](morphology.md).

### Read competing morphology within a word

Use the **expanded / pretty** view of a passage such as `KUB 21.8`,
`Vs. II`, line `2′` or `3′`. On source-attested words, the reading
includes a group of numbered **Candidate** rows below that word's
transliteration. Numbers are source `analysis.index` values (including gaps),
not a probability score. Every candidate remains visible, including a source
parse-failed candidate explicitly labelled **Unparsed**. Neither the browser
nor this conversion promotes one candidate to an authoritative reading.

This supplementary markup uses the existing TF `word → analyses` edge and
the word's own pretty container. It does not alter the sign transcription,
the independent queryable analysis nodes, or selected-candidate source
semantics. Compact/plain views may omit these expanded rows. Exceptional
overlapping word/sign ownership fails closed, rather than attaching a
candidate to a possibly wrong word. For source uncertainty and candidate
selection, see [Morphology](morphology.md).

## Memory and startup

The **first measured cold browser run** on GitHub-hosted Ubuntu with Python
3.13 and Text-Fabric 13.1.0 reported:

| Measurement | Hosted result |
|---|---:|
| Browser kernel setup | 286.03 seconds |
| Peak RSS | 11,977,656 KiB (about 11.4 GiB) |
| Current artifact | TF 0.4.0 |
| Route checks | Home, passage, query and app CSS all passed |

Evidence: [Actions run 44358055538](https://github.com/alexsosn/TLHdig-TF/actions/runs/44358055538)
and [browser smoke test](../programs/tests/test_browser_product_smoke.py).
A separate [cold-online release + real CLI run
44378687539](https://github.com/alexsosn/TLHdig-TF/actions/runs/44378687539)
measured **230.88 seconds** for first remote acquisition and full `use()` load
with **12,391,120 KiB peak RSS (~11.8 GiB)**. Launching the real CLI from
that acquired cache took **27.92 seconds** to respond over HTTP and reached
**12,909,360 KiB VmHWM (~12.3 GiB)**. All tested routes returned HTTP 200.
These are measurements on specific GitHub-hosted Ubuntu runners, not guaranteed
startup times or universal minimum hardware requirements. Warm cache and other
machines may differ substantially. Allow substantial free memory for the full
browser. See [memory optimization issue #164](https://github.com/alexsosn/TLHdig-TF/issues/164).

If this cost is prohibitive, avoid the high-level browser and load just the
features needed by your question:

```python
from tf.fabric import Fabric

TF = Fabric(locations="tf/0.4.0")
api = TF.load("sym after trans lemma morph gloss docid lnno")
```

Do not use `loadAll()` merely to run a small selective query.

## Online acquisition and current-release identity

`tf alexsosn/TLHdig-TF` and `use("alexsosn/TLHdig-TF")` use
Text-Fabric's GitHub acquisition and may prefer the **latest release** to
`main`. The release publication/distribution gate checks that the
downloadable `tf-0.4.0.zip` matches the current main artifact.
For online acquisition, install the additional backend dependencies and see
[Install and load](install.md#b--text-fabric-acquisition).

The published ZIP and latest-release identity were verified after the
2026-11-18 rebuild. The [cold-home online acceptance run
44378687539](https://github.com/alexsosn/TLHdig-TF/actions/runs/44378687539)
subsequently loaded release `tlhdig-0.3_tf-0.4.0` (tag commit
`468da078`) with no clone or prior cache. It checked every acquired
main-module file against `BUILD-MANIFEST.json`, recovered attested readings
from `KBo 31.40` and `KBo 41.49+`, and ran a real
`tf alexsosn/TLHdig-TF -noweb` server with successful root, passage,
morphology query (1,108 matches), and stylesheet requests. JavaScript-driven
clicks in a graphical browser remain outside these HTTP smoke tests.

**Updating an existing installation:** Text-Fabric 13.1 may keep the old
app code when a pre-alpha release is replaced under the same tag.
If new word-owned candidate rows are missing on an older installation,
refresh only the app (`tf alexsosn/TLHdig-TF:hot -noweb`), without forcing
a ~400 MB source-data download. See the
[app-only refresh instructions](install.md#b--text-fabric-acquisition)
for Python use and the separate full-data refresh case.

## Research limitations

The browser preserves the current source's uncertainty and can expose it
through node features and query results:

- Source-damaged or restored spans need editorial-aware filtering.
- Multiple morphological candidates are not automatically reduced to an
  authoritative reading.
- Some cuneiform sign alignments are unavailable or based on more complex
  mechanisms; consult [Cuneiform](cuneiform.md) before treating `cu_sign`
  as uniformly certain.
- Duplicate `docid` values mean a section label need not identify a
  unique source record. Ambiguous upstream links are intentionally
  suppressed instead of choosing an arbitrary manuscript.
- Some source files are excluded and some XML boundary repairs still
  need specialist review. See [KNOWN-ISSUES.md](../KNOWN-ISSUES.md)
  and [Quality and limitations](quality.md).

The ordinary browser does **not** automatically load the optional
`tf-provenance` module. Researchers who require original-source XML,
offsets or detailed repair provenance should use the separate
[provenance instructions](provenance.md).

For reproducibility, record the source/TF version, selected query features,
and any filters on damage and cuneiform alignment. The current pre-alpha
`tf/0.4.0` tree can be rebuilt and replaced without a schema-version bump.
