# Consuming TLHdig-TF: Agora, Context-Fabric, and the Text-Fabric app

Three different consumers load this repository, and they need different things from it.
Two of them do **not** need the `app/` directory at all — a point worth stating up front,
because "make `use()` work" and "make it installable in Agora" are separate tasks.

| Consumer | Entry point | Needs `app/`? | Needs the dataset committed? |
|---|---|---|---|
| Agora marketplace → Context-Fabric MCP | `load_corpus("TLHdig-TF")` | no | **yes** |
| `cfabric` / `text-fabric` directly | `Fabric(locations="tf/0.4.0")` | no | no (any local path) |
| TF app + browser | `use("alexsosn/TLHdig-TF")` | **yes** | yes |

## How Agora actually loads this repo

Verified against `agora-context-fabric` 0.1.0 and `cfabric-mcp` 0.1.7 as installed:

1. `GitStore` clones the repository `--no-checkout` and sparse-checkouts only the
   registry's `tf_path`. If `upstream.ref` is absent, Agora follows the upstream default
   branch; an explicit ref is optional acquisition policy, not a requirement of the loader.
2. It then requires exactly one thing: `otype.tf` must be a file at that path. Nothing
   else is inspected — no `app/`, no README, no licence file.
3. `cfabric_mcp.corpus_manager` loads it with `cfabric.Fabric(locations=path, silent="deep")`
   followed by `loadAll()`.

So the Agora contract is a committed Text-Fabric dataset at the configured `tf_path`, plus
whatever source-revision policy the registry chooses. For TLHdig-TF the current pre-alpha
policy deliberately follows the upstream default branch: there is one mutable current
artifact, and historical generated snapshots are not supported compatibility targets.

That was the blocker until 2026-08-30 — `main` carried the converter but no `tf/`, which
the original registry entry recorded as *"Current main contains newer converter work but
no committed tf/ dataset."*

## The registry entry

The current Agora registry intentionally leaves `upstream.ref` unset and selects the one
supported current artifact at `tf/0.4.0`:

```yaml
- id: TLHdig-TF
  upstream:
    repository: alexsosn/TLHdig-TF
    tf_path: tf/0.4.0
  acquisition:
    strategy: repository
    lazy: true
    notes: Follow the upstream default branch so rebuilt tf/0.4.0 datasets are picked up without introducing a revision pin.
  licenses: {data: CC-BY-4.0, redistribution: permitted}
```

The original Agora entry used `5d5e9af248566222738f8ac65ab8f9bb1b6aed3c` with the
now-retired historical `0.1.0` artifact. That pin predates every marker-conservation fix
and must not be copied into current configuration. It belonged to the earlier publication
model; the current pre-alpha registry deliberately follows the default branch instead.

`redistribution: unknown` was a fair reading of the early repository, because the licence
table assigned everything outside `corpus/` to MIT, and that swept in `tf/`. A conversion
is an adaptation of a CC-BY-4.0 work and cannot be relicensed. Fixed: `tf/**` is
CC-BY-4.0, and every `.tf` file now carries `@license` and `@attribution`, so the
dataset answers the question by itself once detached from the repo.

## What a consumer should still expect

* **Historical load-cost measurement:** the old `tf/0.1.0` Agora measurement observed
  roughly 5 GB of RAM and ~12 minutes for the first load, with ~40 seconds afterwards.
  Those numbers do **not** describe the current `tf/0.4.0` artifact; it has not yet been
  remeasured under the same setup. `loadAll()` pulls every feature, so a client that only
  needs morphology should load a subset where its API permits that.
* **`docid` is not unique** — 141 values are shared by more than one document node — so a
  `(docid, collabel, lnno)` section address can be ambiguous. `docgroup` nodes record which
  records claim the same manuscript, but section addressing itself is still ambiguous.
* **The build remains an integration prototype.** The damage and lexical layers are
  present and independently checked where applicable; 52 files do not parse, and 74
  crossing-tag repairs are unreviewed. See [KNOWN-ISSUES.md](../KNOWN-ISSUES.md).
* **cfabric caches in `.cfm/`**, not `.tf/`, next to the dataset. Neither is committed.

## `get_text_formats()` returned nothing, and why that mattered

Context-Fabric's server instructions tell an agent to *"call `get_text_formats()` before
lexical/surface text searches"* and to use the samples to build search patterns. Measured
against cfabric 0.1.7, this corpus returned:

```
formats found: 0
"No text format metadata available or no orig/trans pairs defined"
```

`describe.py:_parse_otext_format_pairs` pairs a format named `…-orig-X` with one named
`…-trans-X`. This dataset declared `text-orig-full`, `text-orig-plain` and
`line#text-cuneiform` — no `-trans-` name, therefore no pair, therefore no samples.

Two candidate fixes were tested on a synthetic dataset rather than reasoned about:

* Pairing cuneiform against transliteration (`text-orig-cuneiform={cu}` /
  `text-trans-cuneiform={sym}{after}`) **registers but yields zero samples**:
  `_get_exhaustive_text_samples` iterates `range(1, maxSlot + 1)`, and `cu` lives on
  `line`, so every slot returns empty text and is skipped.
* Pairing the source notation against the clean reading — `text-orig-full={srcxml}{after}`
  with `text-trans-full={sym}{after}` — yields real samples, e.g. `"[ya"` → `"ya"`.

The second is shipped. It is **not** a script/romanisation pair: this corpus is
transliteration throughout. It is the source's own editorial notation, brackets and damage
marks included, against the normalised reading — which is precisely the encoding
distinction someone writing a surface-text query has to know about.

## The cuneiform format never worked

Testing the above turned up a separate defect in the shipped 0.1.0 build. It declared:

```
@fmt:line#text-cuneiform={cu}
```

TF's `Text.splitFormat` splits the **template** on `#`, not the format name
(`tf/core/text.py:1225`). With the prefix on the name the format registers as
`line#text-cuneiform` with descend type `sign`, TF evaluates `{cu}` on every sign — signs
have no `cu` — and each line renders as a run of spaces. Measured:

```
T.text(line, fmt="line#text-cuneiform")  ->  '   '
```

Corrected to `@fmt:text-cuneiform=line#{cu} `, which registers with descend type `line`:

```
T.text(line, fmt="text-cuneiform")  ->  '𒉡𒍑𒊭 '
T.text(doc,  fmt="text-cuneiform")  ->  '𒉡𒍑𒊭 𒀭𒍣𒅀 '
```

The existing test asserted that `cu` was present on line nodes, which it always was, so it
passed the whole time. A feature being present is not the same as a format that renders it.


## The TF app

`app/config.yaml` is what `use()` and the TF browser need, and it is checked by
`programs/check_app.py` on every push. TF only validates an app config when `use()` loads
the corpus, and a `features:` entry naming a feature that does not apply to that node type
never raises — it renders as nothing. The first draft of this config had two such entries
(`surface` on `column`, `invnr` on `fragment`); the gate found both in under a second.
