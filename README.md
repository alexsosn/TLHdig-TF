# TLHdig-TF

Converting **TLHdig** — the *Thesaurus Linguarum Hethaeorum digitalis*, the largest
digital corpus of Hittite cuneiform transliterations — into
[Text-Fabric](https://github.com/annotation/text-fabric) format.

**Status: integration prototype — not a trustworthy conversion yet.** A dataset exists
in [`tf/0.1.0/`](tf/0.1.0) and loads in Text-Fabric with working section addressing,
text formats and morphology queries, but an independent review found defects that make
several guarantees below **not yet true of the build**. See
[KNOWN-ISSUES.md](KNOWN-ISSUES.md). Do not rely on `0.1.0` for research.

```python
from tf.app import use
A = use("alexsosn/TLHdig-TF")
```

| | |
|---|---|
| documents | 23,884 |
| sign slots | 3,404,797 |
| nodes | 7,456,283 |
| build time | 19.4 min |
| `.tf` on disk | 314 MB |

Still to come: the TF browser app, `docs/features.md`, and the validation suite against
the post-repair census.

---

## Why

TLHdig ships ~24,000 XML documents in HPM's "AOxml" format: transliterations of
essentially every published cuneiform fragment from Hittite tablet collections, richly
annotated with morphology, editorial apparatus and line-level Unicode cuneiform. It is
searchable through the HPM web interface, but the XML is awkward to compute over —
counting, aggregating, colocation and other corpus-linguistic work all mean writing a
parser first.

Text-Fabric is built for exactly that. It models text as a sequence of slots with
arbitrary annotated nodes over them, which fits cuneiform well: damage brackets that
cut through the middle of a sign and run across word and line boundaries are ordinary
nodes, not a schema violation.

There is currently **no Hittite corpus in Text-Fabric**. The four existing cuneiform
datasets under [Nino-cunei](https://github.com/Nino-cunei) are Akkadian and
proto-cuneiform; this conversion adapts their conventions rather than copying them
(see [the plan](docs/TF-CONVERSION-PLAN.md) §1).

In one sentence: TLHdig already answers *"what does this tablet say?"* well. Text-Fabric
would answer *"what does the corpus do?"* — and specifically, it would let you ask that
while knowing how much of your evidence is broken or undetermined, which is currently
the hardest thing to find out.

## The corpus

| | |
|---|---|
| XML files | 23,937 (23,713 parse cleanly, 224 malformed) |
| Words | 1,221,053 |
| Signs (projected slots) | ≈3,097,100 |
| Lines | 407,623 |
| Documents | 23,713 across 829 CTH classes and 13 sub-corpora |
| Morphological analyses | 1,611,153 |
| Distinct lemmata | 28,091 |
| Lines with Unicode cuneiform | 405,787 |

## What this makes possible

All figures below are measured against the corpus in this repository; the underlying
measurements are in [the research document](docs/TF-CONVERSION-RESEARCH.md) §10.

> **Partly implemented.** Section 1 now works: `cluster` nodes and induced sign flags
> are in the build. Section 5 does not — there are still no `note`, `fragment`, `lex`
> or `docgroup` nodes. Tracked in [KNOWN-ISSUES.md](KNOWN-ISSUES.md).

### 1. Damage-aware querying

**28.7% of words sit inside a damaged range** (356,339 of 1,239,541), and 15.1% of signs
are inside a lacuna. Those are measured from the built dataset, not estimated: break
state is carried by `<del_in/>` / `<del_fin/>` markers at arbitrary character offsets
that cross word *and* line boundaries, so counting it correctly is the whole problem.

*(An earlier estimate here said 53.4%. That came from the naive line-crossing pairing
the research document flags as unreliable, and it over-counted by roughly a factor of
two. Producing a defensible figure was a deliverable of the conversion, not an input to
it.)*

So "give me the attestations of this lemma that are **not** restored" today means
reimplementing bracket-state tracking over the whole corpus. Few people do, which is why
published counts of Hittite forms rarely separate *read* from *restored*. Afterwards:

```
word lemma=pai-/pā-
/without/
  cluster type=del
/-/
```

Measured on three common verbs:

| Lemma | Attestations | Clean | Damaged |
|---|---|---|---|
| `pai-/pā-` "go" | 3,864 | 3,048 | 816 |
| `ēp(p)-/ap(p)-` "seize" | 1,920 | 1,412 | 508 |
| `wed=a-` "build" | 819 | 655 | 164 |

That ratio changes what an argument from frequency is worth. The corpus carries
**655,336 cluster nodes** — 504,518 lacunae, 144,257 damaged-but-legible, 6,211
erasures — of which 484,705 have a boundary falling *inside* a sign and 74,884 cross a
line.

### 2. The ambiguity layer becomes first-class

| | Words |
|---|---|
| selector resolves to one analysis | 429,176 |
| **>1 candidate, no selector — genuinely undetermined** | **215,613** |
| 2–9 candidates | 296,593 |
| ≥10 candidates | 11,525 |

Today those competing readings are `mrp1`…`mrp99` attribute strings: present, but not
queryable. As `analysis` nodes they support questions that currently have no mechanism —
*how often is this form ambiguous between D/L.SG and ALL?* *Which lemmata are
systematically confusable?* *What share of my evidence rests on undisambiguated
readings?* The last is a methodological check no one can presently run.

### 3. Aggregation across documents

The XML is per-file, so every cross-corpus question needs a bespoke parser. `wed=a-`
"build" occurs 868 times, distributed TLH 432 / HDivT 123 / HAnn 116 / MYTH 76 /
KULTINV 51. Frequency lists, collocations, distribution by CTH class or sub-corpus,
hapax identification — one-liners rather than projects.

### 4. Relational search

TF templates express containment and order, which XML cannot without a graph:

```
colon
  word lemma=nu=
  < word pos=PREV
  < word morph~3SG.PRS
```

Multi-layer queries — morphology × damage × language × structural position — are the
normal case in linguistics and are currently impractical.

### 5. Layers that are effectively dark today

* **Witnesses and joins** — which fragments compose a text, joined directly or indirectly.
* **Editorial history** — ~180,000 dated, attributed `<meta>` events, making it possible
  to query the corpus by its own reliability (*which parts have had a second correction
  pass?*).
* **Duplicate editions** — the 114 differing re-editions of one tablet become
  systematically comparable rather than accidental.

### 6. Interoperability

The same query language as [BHSA](https://github.com/ETCBC/bhsa) and the Nino-cunei
corpora, so Akkadian passages *inside* Hittite texts become comparable with Old
Babylonian Akkadian. TF's pandas and MQL exports make the corpus usable as ML input
without anyone writing an AOxml parser first.

### What this does **not** give you

* It does not improve the data. Uneven annotation stays uneven; 473,967 words carry no
  analysis at all and will not gain one.
* It does not disambiguate morphology — it makes ambiguity visible and countable, which
  is a different thing from resolving it.
* It does not replace TLHdig for reading a text, browsing by CTH, or the photographic
  and manuscript apparatus. TF is for asking questions across a corpus, not for
  consulting a tablet.
* Cuneiform stays line-level; there is no sign-aligned Unicode unless upstream has an
  alignment.
* It is not a critical edition, and the plan explicitly forbids the converter from
  drifting into becoming one.

## Repository layout

```
corpus/TLHdig-0.3/     source data, unmodified — CC-BY-4.0, see ATTRIBUTION.md
docs/                  research findings and the conversion plan
```

```
tf/0.1.0/              the generated Text-Fabric dataset (85 features)
programs/tlhdig/       converter: source, signs, morph, brackets, lineref,
                       repair, convert, compact
programs/patches.yaml  repair manifest (173 files, 632 patches)
programs/tests/        118 tests
programs/check_*.py    full-corpus gates
programs/build.py      the full conversion
```

Planned, per [the plan](docs/TF-CONVERSION-PLAN.md) §9: `app/` (TF browser config),
`docs/features.md`, and `reports/` validation output.

**Two version numbers, deliberately unrelated.** `sourceVersion = 0.3` identifies the
upstream TLHdig release; `tfVersion = 0.1.0` identifies this ontology and converter, and
is what `tf/` is named after. Keeping them separate means a fix to the converter or a
change to the node model can ship without implying that TLHdig itself released
anything.

## Documents

* **[docs/TF-CONVERSION-RESEARCH.md](docs/TF-CONVERSION-RESEARCH.md)** — what the corpus
  contains and how AOxml encodes it. Every count is measured against the files on disk;
  where upstream HPM/HFR/SimTex documentation exists it is cited and reconciled with the
  measurements. Includes the full `mrp` morphology grammar, the `lnr` line-reference
  grammar, a complete markup inventory, and a classification of all 224 malformed files.

* **[docs/TF-CONVERSION-PLAN.md](docs/TF-CONVERSION-PLAN.md)** — the target Text-Fabric
  model (node types, feature catalogue, edges, `otext` config), a nine-stage conversion
  pipeline, the validation strategy, and the five questions still open with the TLHdig
  team.

## Design in one paragraph

The slot type is **`sign`**, not `word` — settled by measurement, and independently
confirmed by all four existing cuneiform TF corpora. Editorial damage brackets fall
*inside* a sign in the majority of cases (`laes_fin` 89% of the time, `del_fin` 55%) and
run across word and line boundaries, so word-level slots cannot represent damage extents.

Above `sign` sit `word`, `line`, `column`, `surface`, `paragraph`, `colon` and
`document`, with `analysis`, `cluster`, `note`, `edit`, `fragment`, `lex` and `docgroup`
as analytical and relational overlays. Following Uruk, the full ontology is declared in
`@levels` while only three levels — `document / column / line` — serve as navigational
sections, addressed the way a Hittitologist cites: `KUB 21.8`, `€1 Vs. II`, `5′`.

The plan carries **two explicit guarantees** rather than one vague one: the original
bytes stay recoverable via byte-range features into the source files, and the TF graph
is content-complete, with every AOxml construct resolving to a node, edge or feature
rather than surviving as an opaque string.

At ~3.1M signs and ~7.2M nodes this would be roughly **4× the largest existing cuneiform
TF dataset** (Old Assyrian, 766k signs), so the first milestone is a scale benchmark, not
code.

## Licensing

Two licences apply, and they do not overlap:

| Path | Licence | Applies to |
|---|---|---|
| `corpus/**` | **CC-BY-4.0** — [licence text](corpus/TLHdig-0.3/LICENSE), [attribution](corpus/TLHdig-0.3/ATTRIBUTION.md) | the data |
| everything else | **MIT** — [licence text](LICENSE) | the code and documentation |

`SPDX-License-Identifier: MIT` for the code; `SPDX-License-Identifier: CC-BY-4.0` for
everything under `corpus/`. GitHub's repository-level licence badge reads the root
`LICENSE` only and will therefore show MIT — that badge does **not** describe the
corpus.

If you use the corpus, cite the dataset, not this repository:

> Müller, G.; Prechel, D.; Rieken, E.; Schwemer, D. *Thesaurus Linguarum Hethaeorum
> digitalis (TLHdig) Beta Version 0.3.* Zenodo, 2026.
> <https://doi.org/10.5281/zenodo.20328284>

## Acknowledgements

The corpus is the work of the TLHdig team at the Hethitologie-Portal Mainz and of the
Hittitological community whose transliterations it aggregates. The conversion design
follows [Nino-cunei/tfFromAtf](https://github.com/Nino-cunei/tfFromAtf) for cuneiform
modelling and [ETCBC/bhsa](https://github.com/ETCBC/bhsa) for Text-Fabric conventions.
