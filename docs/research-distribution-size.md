# Research: what the dataset costs a consumer

Issue: #39

Measured on branch `feat/docid-raw` at `c54384306456b553849d7a27521f0f289d6b149c`, on macOS
with the repo's own `.venv`. Every figure below is an observation, not an estimate, except
where the text says otherwise.

The question this answers is not "how big is the repository" but "how much space does a
consumer spend at each of the three moments that cost them anything": download, first
compile, and a live session.

## 1. What is in the repository today

```text
tf/0.1.0                390M
tf/0.2.0                390M   121 files (119 .tf + LICENSE + BUILD-COMPLETE)
tf-provenance/0.1.0      54M
tf-provenance/0.2.0      54M   README.md, src_span.tf (26M), srcxml.tf (28M)
corpus/                 380M   24,135 tracked files
```

Two published dataset versions, both complete copies. `tf/0.2.1` is a third.

**Do not measure `.git` with `du` on a working copy.** A checkout that has been used for
local builds accumulates loose objects that were never pushed and that no consumer
receives. This one held 1,800 loose objects — 1.52 GiB — which is most of the difference
between what the disk reports and what anyone downloads:

```text
$ git count-objects -vH
count: 1800          size: 1.52 GiB      # local only, never pushed
in-pack: 28718       size-pack: 1.40 GiB

$ gh api repos/alexsosn/TLHdig-TF --jq .size
1583104 KB = 1.51 GB                     # GitHub's figure for the published repo
```

Two independent sources agree: **the published repository is ~1.5 GB.**

## 2. Where the 390M of a single version goes

The provenance module is 12% of a release, not the bulk, and it is a separate directory
that is not loaded unless asked for. The main dataset is ordinary features over a large
corpus:

```text
59M  oslots.tf      4,903,205 lines
24M  sym.tf
22M  cu_sign.tf
19M  after.tf
15M  cu.tf
13M  raw.tf
```

Node inventory from `otype.tf`: 3,386,344 `sign` slots, then `analysis` (1,626,932),
`word` (1,234,497), `cluster` (656,389) and the rest. `oslots.tf` — every non-slot node
listing the signs it spans — is the single largest file and is pure Text-Fabric structure,
not provenance and not redundant.

At 3.4M slots across ~120 features, stored as plain text, 390M is close to what the format
costs. TF's compact node-set encoding (`1697,4616,4943,…<TAB>value`) is already in use.

### The one genuine redundancy

`tf-provenance/0.2.0/README.md` says of `srcxml` (28M):

> Not needed to read or query the corpus: every tag inside `srcxml` is modelled in the
> main dataset — wrappers as `sgr`/`agr`/`det`/`num`, damage as `cluster` nodes with
> offsets, `corr` and `note` as their own features.

It is recoverable a second way as well: `src_span` gives a byte range into the file
`src_file` names, and `corpus/` is tracked in this same repository. So those 28M store
what two other tracked things already determine. It is kept deliberately, for the
byte-exact round trip Contract A verifies, and it is already quarantined into an optional
module. This is a defensible trade, not a defect — but it is the only part of the release
that is duplicated rather than derived.

## 3. Download

`README.md` documents both paths: `Fabric(locations="tf/0.2.1")` against a checkout, and
an `app/config.yaml` for the Text-Fabric app, so `use("alexsosn/TLHdig-TF")` resolves
too. The app matters here because of what it does *not* fetch — see §6.

| path | cost |
|---|---:|
| `git clone` (full history) | **~1.5 GB** downloaded, ~3.2 GB on disk |
| `git clone --depth 1` | ~0.2 GB pack + 1.7 GB checkout |
| `tf/0.2.0` alone, `tar --exclude=.tf` + `gzip -6` | **125,186,176 B (125 MB)** |

The dataset compresses 3.27×. A consumer who needs one version currently downloads
roughly **12×** what that version costs to ship.

## 4. First compile

TF compiles loaded features to a binary cache in `.tf/` beside the dataset. A cache now
exists on this machine, so this is measured rather than extrapolated:

```text
$ du -sh tf/0.2.0/.tf
250M
```

That is for a **12-feature** load, and its composition is the important part:

```text
184M   fixed structural precompute   __levDown__ 75M, __levUp__ 50M,
                                     __boundary__ 26M, __order__ 16M,
                                     __rank__ 11M, __sections__ 5.5M
 66M   the 12 feature caches         oslots 44M, sym 9.6M, after 5.3M, cu 5.1M, …
```

**Loading fewer features does not proportionally shrink the cache.** The 184M of
structural precompute is paid regardless of how few features are requested, so a
12-feature subset already costs ~250M — about two thirds of what a full load would. This
corrects the intuition that a subset is cheap on disk: it is cheap on *memory and time*,
not on cache size.

For comparison, whole-corpus text→cache ratios from other corpora present on this machine
(these conflate both components, which is why they vary so widely):

```text
etcbc/bhsa/tf/c                   147M text -> 177M cache   1.20x
etcbc/dss/tf/0.6                  100M text ->  87M cache   0.87x
Nino-cunei/oldbabylonian/1.0.4     15M text ->  13M cache   0.87x
github/HuygensING/suriano/1.0.2e   20M text ->  54M cache   2.64x
```

## 5. Live

`README.md:82` records ~5 GB peak RAM for a full `loadAll()`.
`docs/AGORA-INTEGRATION.md:56-57` and
`wiki/independent-code-architecture-review-2026-08-30.md:460-461` add ~12 minutes for a
first load and ~40 seconds afterwards.

Independent corroboration of the order of magnitude: `programs/build.py` was observed at
5,679,436 KB RSS (~5.4 GB) during conversion of this same corpus.

Subset loads cost proportionally less *here* — this is the phase where loading fewer
features genuinely helps.

## 6. What this implies

The download is the only phase where the cost is mostly accidental, and the Text-Fabric
app is what makes it avoidable: verified against the installed text-fabric 13.1.0,
`advanced/repo.py` `downloadRelease()` takes a release asset when one exists and otherwise
falls back to `downloadDir(commit, exclude=r"\.tfx")`, which walks only the `relative`
subdirectory for the requested version. Neither path fetches `.git` or `corpus/`.

Compile cost is dominated by a fixed structural precompute and is not reduced much by
loading less; live cost is, and is already documented. The ~12× download multiplier is not
a property of the data — it is a consequence of distributing a dataset as repository
contents and keeping every published version in the working tree.
