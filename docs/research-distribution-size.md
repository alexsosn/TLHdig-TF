# Research: what the dataset costs a consumer

Issue: (not yet filed)

Measured on branch `feat/docid-raw` at `c54384306456b553849d7a27521f0f289d6b149c`, on macOS
with the repo's own `.venv`. Every figure below is an observation, not an estimate, except
where the text says otherwise.

The question this answers is not "how big is the repository" but "how much space does a
consumer spend at each of the three moments that cost them anything": download, first
compile, and a live session.

## 1. What is in the repository today

```text
tf/0.1.0                390M
tf/0.2.0                390M   121 files
tf-provenance/0.1.0      54M
tf-provenance/0.2.0      54M   README.md, src_span.tf (26M), srcxml.tf (28M)
corpus/                 380M   24,135 tracked files
.git                    2.4G
total on disk           4.1G
```

Two published dataset versions, both complete copies. `tf/0.2.1` will be a third.

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
12M  lexeme.tf / gloss.tf / stemclass_raw.tf / morph.tf
11M  lemma.tf / index.tf
```

Node inventory from `otype.tf`: 3,386,344 `sign` slots, then `analysis` (1,626,932),
`cluster`, `word`, `line` and the rest. `oslots.tf` — every non-slot node listing the
signs it spans — is the single largest file and is pure Text-Fabric structure, not
provenance and not redundant.

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

There is no Text-Fabric app, so `use("alexsosn/TLHdig-TF")` is not the path. `README.md`
documents `Fabric(locations="tf/0.2.1")`, which presupposes a local checkout. A consumer
therefore clones:

| path | cost |
|---|---:|
| `git clone` (full history) | ~4.1 GB |
| `git clone --depth 1` | ~1.7 GB |
| `tf/0.2.0` alone, `tar` + `gzip -6` | **125,186,161 B (125 MB)** |

The dataset compresses 3.1×. A consumer who needs one version currently downloads roughly
33× what that version costs to ship.

## 4. First compile

TF compiles loaded features to a binary cache in `.tf/` beside the dataset. It compiles
only the features actually loaded, so the cache tracks the working set, not the release.

No TLHdig cache exists on this machine to measure. Ratios from corpora that are present:

```text
etcbc/bhsa/tf/c                   147M text -> 178M cache   1.21x
etcbc/dss/tf/0.6                  100M text ->  87M cache   0.87x
Nino-cunei/oldbabylonian/1.0.4     16M text ->  14M cache   0.88x
github/HuygensING/suriano/1.0.2e   21M text ->  54M cache   2.6x
```

Extrapolating the large-corpus band to 390M gives roughly 350–470M for a full load. This
is the one number here that is an estimate; TLHdig's own ratio has not been measured.
The `README.md` example loads 17 of ~120 features and would compile a fraction of it.

## 5. Live

`docs/AGORA-INTEGRATION.md` and `README.md:82` both record ~5 GB peak RAM and ~12 minutes
for a first `loadAll()`, ~40 seconds afterwards.

Independent corroboration of the order of magnitude: `programs/build.py` was observed at
5,679,436 KB RSS (~5.4 GB) during conversion of this same corpus.

Subset loads cost proportionally less. The 5 GB figure is `loadAll()`, which the README
already advises against.

## 6. What this implies

The download is the only phase where the cost is mostly accidental. Compile and live cost
are properties of a 3.4M-slot corpus and are reduced by loading fewer features, which is
already documented. The 33× download multiplier is not a property of the data — it is a
consequence of distributing a dataset as repository contents and keeping every published
version in the working tree.
