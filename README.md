# TLHdigTF

Converting **TLHdig** — the *Thesaurus Linguarum Hethaeorum digitalis*, the largest
digital corpus of Hittite cuneiform transliterations — into
[Text-Fabric](https://github.com/annotation/text-fabric) format.

**Status: research and design complete; conversion not yet implemented.**
The corpus has been analysed in full and the target model is specified and validated.
No feature files have been built yet.

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

There is currently **no Hittite corpus in Text-Fabric**. The closest existing datasets
are the Akkadian and proto-cuneiform corpora under
[Nino-cunei](https://github.com/Nino-cunei), whose conventions this conversion follows.

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

## Repository layout

```
corpus/TLHdig-0.3/     source data, unmodified — CC-BY-4.0, see ATTRIBUTION.md
docs/                  research findings and the conversion plan
```

Planned, per [the plan](docs/TF-CONVERSION-PLAN.md) §5.9:

```
programs/              convert.py, checks.ipynb
tf/0.3/                generated Text-Fabric feature files
app/                   Text-Fabric browser app config
reports/               inventory, repairs, validation output (generated)
```

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
