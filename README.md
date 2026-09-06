<p align="center">
  <img src="images/logo.png" alt="TLHdig-TF" width="320">
</p>

# TLHdig-TF

A [Text-Fabric](https://github.com/annotation/text-fabric) conversion of **TLHdig**
(*Thesaurus Linguarum Hethaeorum digitalis*), the largest digital corpus of Hittite
cuneiform transliterations.

TLHdig-TF turns the upstream per-document XML into a corpus graph for querying morphology,
editorial damage, ambiguity, textual structure, witnesses, provenance and — where the
alignment can be justified — Unicode cuneiform at sign level. The original TLHdig remains
the right interface for reading and consulting individual texts; this project is aimed at
corpus-scale analysis.

This repository is an independent conversion and is **not an official TLHdig/HPM
project**.

## Status

**Current TF version: `0.3.0` — integration prototype. Do not use it as the sole basis for
research conclusions yet.**

The generated dataset is committed in [`tf/0.3.0/`](tf/0.3.0), the Text-Fabric app
configuration is in [`app/`](app/), and the main build invariants are checked against the
shipped artefact rather than only against converter internals.

What is already in the build:

- the full sign/word/line/document hierarchy plus analytical layers including `analysis`,
  `cluster`, `lex`, `fragment`, `note`, `edit` and `docgroup`;
- independently checked conservation of every `del` / `laes` / `ras` / `add` / `quot`
  source marker ([report](reports/markers.md));
- morphological alternatives as separate queryable `analysis` nodes;
- lexical nodes and `analysis -> lex` links;
- sign-level Unicode cuneiform (`cu_sign`) for **2,993,867 of 3,386,344 signs (88.4%)**,
  with the alignment mechanism recorded per line ([report](reports/alignment.md));
- source provenance in a separate optional module, plus full-corpus validation reports.

Important remaining limitations:

- **74 crossing-tag repairs** in 62 source files still require Hittitological review;
- 53 source files are excluded from conversion (52 unparseable, 1 encrypted);
- `docid` is not globally unique: 141 values occur on more than one document node;
- some spans affected by boundary-moving repairs are explicitly excluded from strict
  byte-for-byte Contract A verification; see [`reports/contract_a_graph.md`](reports/contract_a_graph.md);
- sign-level cuneiform is incomplete and alignment confidence differs by mechanism — use
  [`reports/alignment.md`](reports/alignment.md), not coverage alone, when filtering it.

The complete, maintained list is in **[KNOWN-ISSUES.md](KNOWN-ISSUES.md)**. Generated
corpus counts and invariants are in **[reports/census.md](reports/census.md)**.

## Quick start

The most deterministic entry point today is a local clone plus `Fabric`. Text-Fabric
`13.1.0` is the version pinned by this repository.

```bash
git clone https://github.com/alexsosn/TLHdig-TF.git
cd TLHdig-TF
python -m pip install text-fabric==13.1.0
```

Load only the features you need:

```python
from tf.fabric import Fabric

TF = Fabric(locations="tf/0.3.0")
api = TF.load(
    "sym after trans lemma gloss morph pos cu_sign cu_aligned "
    "project subcorpus type width docid collabel lnno"
)

F, L, S, T = api.F, api.L, api.S, api.T

line = T.nodeFromSection(("KUB 21.8", "Vs. II", "1′"))
print(T.text(line, fmt="text-orig-plain"))
```

`loadAll()` is convenient but expensive: the measured full load reaches roughly 5 GB peak
RSS on the development machine. For most work, selective feature loading is substantially
faster and smaller.

The repository also ships an [`app/config.yaml`](app/config.yaml) for the Text-Fabric app
and browser. Agora / Context-Fabric, direct `Fabric`, and the TF app have different loading
contracts; see **[docs/AGORA-INTEGRATION.md](docs/AGORA-INTEGRATION.md)** for the exact
paths and caveats.

## What you can do with it

The snippets below show the intended shape of corpus work. For research-oriented examples
and literature-grounded tutorial ideas, see
**[docs/applications-deep-research-report.md](docs/applications-deep-research-report.md)**.

### Query morphology without discarding ambiguity

Morphology belongs to `analysis` nodes rather than `word` nodes because a word can carry
several competing analyses.

```python
hits = S.search("""
analysis lemma=pai-/pā-
""")

for (analysis,) in hits[:10]:
    print(F.lemma.v(analysis), F.morph.v(analysis), F.gloss.v(analysis))
```

This makes questions about ambiguity queryable directly: which forms have several
candidate analyses, which lemmas are systematically confusable, or how much of a result
set depends on an unresolved morphological choice.

### Exclude restored or damaged evidence

Editorial ranges are `cluster` nodes spanning the affected sign slots. A point lacuna is
kept as a zero-width editorial statement, so `width>1` matters when the question is about
material that is actually covered by a damaged range.

```text
word
  analysis lemma=pai-/pā-
/without/
  cluster type=del width>1
/-/
```

The source-marker gate independently checks that the graph accounts for every damage and
editorial marker family; exact current counts are generated in
[`reports/markers.md`](reports/markers.md) and [`reports/census.md`](reports/census.md).

### Work with transliteration and cuneiform at sign level

Where a line has a justified alignment, each `sign` may carry `cu_sign`. `cu_aligned` on
the line records which alignment mechanism was required.

```python
for line in F.otype.s("line"):
    if F.cu_aligned.v(line) != 1:   # direct count-matched alignment only
        continue
    signs = L.d(line, otype="sign")
    pairs = [(F.sym.v(s), F.cu_sign.v(s)) for s in signs if F.cu_sign.v(s)]
    if pairs:
        print(pairs[:12])
        break
```

The current build has sign-level cuneiform on 88.4% of sign slots, but that number is a
coverage figure. Precision checks, disagreement rates and the breakdown by mechanism are
published separately in [`reports/alignment.md`](reports/alignment.md).

### Aggregate across the whole corpus

Once analyses and documents are one graph, distributions no longer require parsing
thousands of XML files independently.

```python
from collections import Counter

hits = S.search("""
analysis lemma=wed=a-
""")

by_project = Counter()
for (analysis,) in hits:
    docs = L.u(analysis, otype="document")
    if docs:
        by_project[F.project.v(docs[0])] += 1

print(by_project.most_common())
```

The same pattern supports frequency lists, distributions by CTH class, collocations,
lexical inventories, editorial-history filters and combinations of morphology × damage ×
language × document structure.

## Corpus at a glance

The table below describes the **shipped Text-Fabric build**, not a hand-maintained estimate
of the upstream XML. It is regenerated by `programs/census.py`; use
[`reports/census.md`](reports/census.md) as the authoritative current census.

| Node type | Current count |
|---|---:|
| signs (slots) | 3,386,344 |
| words | 1,234,497 |
| morphological analyses | 1,626,932 |
| damage/editorial clusters | 656,389 |
| lines | 412,637 |
| lexical nodes | 28,282 |
| documents | 23,884 |
| **all nodes** | **8,289,535** |

The build currently exposes 107 node features and 9 edge features in addition to the
Text-Fabric warp features.

## Upstream: TLHdig

**TLHdig (Thesaurus Linguarum Hethaeorum digitalis)** is an open, growing repository of
transliterated cuneiform manuscripts from Hittite Anatolia and northern Syria (ca.
1600–1200 BCE). It is developed within the **Hethitologie-Portal Mainz (HPM)** and brings
together Hittite texts as well as texts in other languages used by Hittite scribes.

- **[TLHdig online](https://hethport.net/TLHdig/)** — browse and search the original corpus.
- **[Hethitologie-Portal Mainz](https://hethport.net/HPM/)** — the wider research
  infrastructure.
- **[TLHdig Beta 0.3 on Zenodo](https://doi.org/10.5281/zenodo.20328284)** — archived
  source dataset used for this conversion.

The source release contains 23,937 XML files in HPM's AOxml format. TLHdig is a living
manuscript repository rather than a dictionary or critical edition; the conversion keeps
that distinction.

## Data model

The slot type is **`sign`**. This is necessary because editorial markers can begin or end
inside a sign and can cross word and line boundaries.

The main structural hierarchy is:

```text
sign → word → line → column → surface → document
```

Additional structures such as `paragraph` and `colon` coexist with analytical and
relational overlays including `analysis`, `lex`, `cluster`, `fragment`, `note`, `edit` and
`docgroup`.

Navigation uses three section levels:

```text
document / column / line
```

so a location can be addressed in the familiar form `KUB 21.8 / Vs. II / 1′`.

The complete model, feature catalogue and conversion decisions are documented in
**[docs/TF-CONVERSION-PLAN.md](docs/TF-CONVERSION-PLAN.md)** and
**[docs/TF-CONVERSION-RESEARCH.md](docs/TF-CONVERSION-RESEARCH.md)**.

## Research limitations

TLHdig-TF preserves upstream uncertainty; it does not silently repair or normalize it
away.

- Missing or uneven morphological annotation remains missing or uneven.
- Multiple analyses remain multiple analyses unless the source selects one.
- Editorial damage ranges are represented, but some unclosed ranges require an explicit
  extent convention documented by the converter.
- Sign-level cuneiform is derived only where the alignment procedure can justify an
  assignment; unaligned signs remain empty.
- 74 structural XML repairs await specialist review and are catalogued individually in
  [`reports/crossing-tag-review.md`](reports/crossing-tag-review.md).
- The conversion is not a critical edition and does not replace TLHdig for reading a
  tablet, manuscript consultation, photographs or HPM's linked resources.

For reproducible work, record the TF version, the filtering rule used for damaged material
and — when using `cu_sign` — the accepted `cu_aligned` levels.

## Validation

Validation is deliberately run against the generated `.tf` files where possible. The
current reports include:

- [`reports/census.md`](reports/census.md) — node counts and core invariants;
- [`reports/markers.md`](reports/markers.md) — independent source-marker conservation;
- [`reports/alignment.md`](reports/alignment.md) — sign-level cuneiform coverage and
  disagreement rates;
- [`reports/alignment-sample.md`](reports/alignment-sample.md) — stratified alignment
  sample for human inspection;
- [`reports/contract_a_graph.md`](reports/contract_a_graph.md) — graph-to-source span
  verification;
- [`reports/crossing-tag-review.md`](reports/crossing-tag-review.md) — repairs awaiting
  philological review;
- [`reports/structure.md`](reports/structure.md) and [`reports/tags.md`](reports/tags.md) —
  structural and source-tag checks.

For a new dataset release, `programs/release_check.py` is the canonical certification
entry point. It runs the required gates against one unchanged artifact and writes a
manifest-bound `BUILD-COMPLETE`; `census.py` alone cannot certify a release. The exact
build → certify → publish sequence and the `regression-valid` / `research-ready`
distinction are documented in **[docs/RELEASE.md](docs/RELEASE.md)**.

Historical investigation, failed approaches and converter-design reasoning belong in the
research documents and reports rather than in this front page.

## Repository layout

```text
app/                    Text-Fabric app configuration
corpus/TLHdig-0.3/      upstream source data, unmodified
docs/                   research, design and integration documentation
programs/tlhdig/        converter implementation
programs/tests/         pytest suite
programs/check_*.py     corpus-scale validation gates
reports/                generated validation output
tf/0.3.0/               current generated Text-Fabric dataset
tf-provenance/0.3.0/    current optional source-provenance module
```

Two version numbers are intentionally separate: `sourceVersion = 0.3` identifies the
upstream TLHdig release, while `tfVersion = 0.3.0` identifies this conversion model and
build.

## Documentation

- **[TF conversion research](docs/TF-CONVERSION-RESEARCH.md)** — measured description of
  AOxml, morphology, line references, markup and malformed-source cases.
- **[TF conversion plan](docs/TF-CONVERSION-PLAN.md)** — ontology, features, edges,
  conversion pipeline and validation strategy.
- **[Release certification](docs/RELEASE.md)** — canonical full release gate, stamp
  semantics and publication sequence.
- **[Cuneiform alignment research](docs/research-cuneiform-alignment.md)** — how
  line-level cuneiform is aligned to signs, including failed approaches and external
  sign-list validation.
- **[Research applications](docs/applications-deep-research-report.md)** — corpus queries
  and tutorial candidates grounded in Hittitological research questions.
- **[Agora / Context-Fabric integration](docs/AGORA-INTEGRATION.md)** — consumer-specific
  loading behaviour and cache considerations.
- **[Known issues](KNOWN-ISSUES.md)** — open correctness, provenance and usability issues.

## Licensing

The source data and the generated dataset are licensed separately from the converter code:

| Path | Licence | Applies to |
|---|---|---|
| `corpus/**` | **CC-BY-4.0** | upstream TLHdig source data |
| `tf/**` and `tf-provenance/**` | **CC-BY-4.0** | generated adaptations of the source corpus |
| code and repository documentation | **MIT** | converter, tests and project documentation |

Each `.tf` file carries source attribution and licence metadata so that the derived data
remain identifiable when copied out of the repository. GitHub's repository-level licence
badge reads the root MIT `LICENSE`; it does not describe the corpus data.

If you use the textual data for Hittitological research, cite the upstream dataset:

> Müller, G.; Prechel, D.; Rieken, E.; Schwemer, D. *Thesaurus Linguarum Hethaeorum
> digitalis (TLHdig) Beta Version 0.3.* Zenodo, 2026.
> https://doi.org/10.5281/zenodo.20328284

Cite this repository as well when the Text-Fabric conversion, ontology, validation or
alignment procedure itself is part of what you discuss.

## Acknowledgements

The corpus is the work of the TLHdig team at the Hethitologie-Portal Mainz and of the
Hittitological community whose transliterations it aggregates. The conversion draws on
Text-Fabric conventions established by [ETCBC/bhsa](https://github.com/ETCBC/bhsa) and
cuneiform modelling work in [Nino-cunei](https://github.com/Nino-cunei).