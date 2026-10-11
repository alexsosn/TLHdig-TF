# Installing and loading TLHdig-TF

This is the single canonical installation page. Everything else in this repository links
here rather than repeating install commands, so there is only one place to keep correct.

TLHdig-TF is pre-alpha. `main` carries one supported current generated artifact,
`tf/0.4.0`. Its bytes and schema may change as correctness work lands, and historical
generated snapshots are not a compatibility promise. Read
[`../KNOWN-ISSUES.md`](../KNOWN-ISSUES.md) before drawing conclusions from the data.

## Which path do you want?

| You want | Use | Needs network at load time |
|---|---|---|
| The corpus in Python, reproducibly pinned | **A — local clone** | no |
| Text-Fabric to fetch and cache it for you | **B — Text-Fabric acquisition** | first time only |
| The corpus through the Agora / Context-Fabric MCP | **C — Agora** | handled by Agora |

All three resolve to the same current artifact. Path A is the most deterministic and is
what the documentation's query examples assume.

## A — local clone (recommended)

```bash
git clone https://github.com/alexsosn/TLHdig-TF.git
cd TLHdig-TF
python -m pip install text-fabric==13.1.0
```

The dataset is committed, so the clone already contains it. Load only the features you
need — `loadAll()` is convenient but expensive:

```python
from tf.fabric import Fabric

TF = Fabric(locations="tf/0.4.0")
api = TF.load("sym after trans lemma gloss morph pos cu_sign cu_aligned")
F, L, S, T = api.F, api.L, api.S, api.T
```

The clone is roughly 400 MB for `tf/0.4.0` plus the pinned source corpus.

## B — Text-Fabric acquisition

Text-Fabric can fetch the app and dataset into `~/text-fabric-data` itself:

```bash
python -m pip install 'text-fabric[github]==13.1.0' 'PyGithub<2.7'
```

```python
from tf.app import use

A = use("alexsosn/TLHdig-TF", hoist=globals())
```

or the browser:

```bash
tf alexsosn/TLHdig-TF
```

Two parts of that install line are load-bearing, and the plain
`pip install text-fabric==13.1.0` from path A will not work here:

- **`[github]`** installs Text-Fabric's GitHub backend. Without it, acquisition fails with
  `Backend provider github not supported`.
- **`PyGithub<2.7`** is required because Text-Fabric 13.1.0 calls
  `get_rate_limit().core`. PyGithub 2.7.0 changed that return type to
  `RateLimitOverview`, so newer PyGithub aborts the download with
  `'RateLimitOverview' object has no attribute 'core'`. The pin is a consumer-side
  workaround for an upstream incompatibility, not a project requirement; it is
  deliberately absent from `requirements.txt`, which pins the *build* environment and is
  bound by `BUILD-MANIFEST.json`.

No checkout specifier is needed: Text-Fabric takes the current release, which carries the
dataset as a single `tf-0.4.0.zip` asset, so the first fetch is one ~127 MB download
rather than 140 separate API calls. `programs/check_distribution.py` is the gate that
keeps the published release current; see
[research-distribution-acquisition.md](research-distribution-acquisition.md) for the
resolution rules and [RELEASE.md](RELEASE.md) for how the release is published.

The dataset lands in `~/text-fabric-data/github/alexsosn/TLHdig-TF/tf/0.4.0/` and includes
`BUILD-MANIFEST.json`, so a downloaded copy can still verify itself.

Because pre-alpha rebuilds replace the current artifact in place, a cached copy can fall
behind. To force the current default-branch head instead of the cached release:

```python
A = use("alexsosn/TLHdig-TF:hot", checkout="hot", hoist=globals())
```

Note that `hot` fetches file-by-file and is therefore slow for this dataset; prefer it only
when you specifically need a commit newer than the release.

## C — Agora / Context-Fabric

The corpus is registered in the Agora resource registry as `TLHdig-TF`:

```python
load_corpus("TLHdig-TF")
```

Agora does a sparse git checkout of the registry's `tf_path` from the upstream default
branch. It does not use GitHub releases and does not need `app/`, so it always follows
the current artifact. See [AGORA-INTEGRATION.md](AGORA-INTEGRATION.md) for the registry
entry and the loader contract.

## Verifying what you got

The dataset carries its own build record:

```bash
python programs/check_build_manifest.py
```

That recomputes input, executable/config and generated-output identities against
`tf/0.4.0/BUILD-MANIFEST.json`. See [RELEASE.md](RELEASE.md) for what the manifest
asserts and what it deliberately does not.

Within a Python session, the loaded version is on the dataset itself:

```python
print(TF.features["otype"].metaData.get("version"))
```

## Licensing

The converter code is MIT. The corpus under `corpus/` and the generated dataset under
`tf/` are CC-BY-4.0, inherited from the source dataset, which must be attributed. Every
`.tf` file carries `@license` and `@attribution`, so the dataset answers this on its own
once detached from the repository. Cite the source dataset, not this conversion, for any
Hittitological claim — see [`../CITATION.cff`](../CITATION.cff).
