# Research: HFR annotation status and TLHdig-TF

Issue: #79

Date: 2026-09-09

Status: research frozen before any production/schema/UI change.

## Question

The live HFR/TLHdig interlinear display distinguishes **pre-validated** annotation (magenta) from **not validated** annotation (grey). The question is whether that workflow status can be represented faithfully from the distributed TLHdig 0.3 XML / certified TF 0.4.0, rather than inferred from unrelated metadata.

## Authoritative HFR semantics

HFR documents a three-stage annotation workflow:

1. **automatic annotation** — context-free matching against possible Hittite word forms; ambiguous forms retain multiple proposals; the live HFR mouse-over/interlinear view displays this stage in **grey**;
2. **manual pre-validation** — project staff reduce automatic proposals using syntax and text understanding while retaining genuine residual ambiguity; the live view displays this stage in **magenta**;
3. **full manual validation** — performed in the course of critical-edition work, where reconstruction, translation and commentary provide stronger textual understanding.

Authoritative public description:
- https://www.hethport.uni-wuerzburg.de/HFR/annotation.php
- https://www.hethport.uni-wuerzburg.de/HFR/material/Handreichung_Annotation.pdf

The annotation handbook's manual examples use `mrp0sel` to choose a candidate / alternative, e.g. numeric selectors such as `1`, `1a`, `1j`, etc. This establishes `mrp0sel` as a source **disambiguation/selection mechanism**.

However, the HFR Basiscorpus production handbook documents completion of manually checked annotation separately: completed individual files are recorded in a project status file as `/ANN_[NAME] [DATE]`, and a completed CTH group is marked in a separate overview spreadsheet. It also describes an `OUTPUT_XMLbasis` stage for automatically annotated but not yet validated XML.

Authoritative production handbook:
- https://www.hethport.uni-wuerzburg.de/HFR/material/Handreichung_Basiscorpus.pdf

Therefore the workflow-status concept is broader than the existence of a numeric selector on one word.

## Reproducible production-corpus census

`programs/research_annotation_status.py` was run in GitHub Actions on exact head `2e3c2c93ac176d2c4e5ed8e921a83efa94fe27c6` after the adversarial classification fixes.

Hosted evidence:
- workflow run: `34338871533`
- job: `102424659321`
- conclusion: success

The hardened census scans only `*.xml`, reads the committed exclusion ledger, excludes the 53 non-shipped records before drawing conclusions about the released population, reports mixed unresolved selectors (`???` plus a numeric fallback hint) separately, and does not mistake compressed Text-Fabric feature-file physical lines for assignment counts.

Population:

| measure | count |
|---|---:|
| source XML files | 23,937 |
| excluded XML files | 53 |
| production/shipped-source XML files | 23,884 |
| production HFR XML files | 8,286 |

### `mrp0sel` states in all production words

| selector class | words |
|---|---:|
| empty/missing | 905,531 |
| numeric selection | 453,149 |
| plain `???` / unknown | 18,429 |
| `???` + numeric fallback hint | 20 |
| `DEL` | 197,493 |
| `AKK` | 42,848 |
| `HURR` | 18,921 |
| `HAT` | 6,359 |
| `SUM` | 2,201 |
| `LUW` | 2,083 |
| special + numeric | 201 |
| other malformed/nonstandard | 62 |

Candidate-presence census:

- 756,376 words have one or more `mrpN` candidates;
- 890,921 words have no `mrpN` candidates.

Production documents may contain several selector classes. 18,715 documents contain at least one numeric selector; 3,783 contain at least one plain `???` selector; and 14 contain at least one `???` + numeric fallback selector. These document categories can overlap.

### HFR subset

Among 8,286 production HFR documents, word-level selector states are:

| selector class | HFR words |
|---|---:|
| empty/missing | 197,900 |
| numeric selection | 271,186 |
| plain `???` / unknown | 535 |
| `???` + numeric fallback hint | 6 |
| `DEL` | 76,517 |
| `HAT` | 4,576 |
| `HURR` | 3,311 |
| `AKK` | 236 |
| `LUW` | 696 |
| `SUM` | 1 |
| special + numeric | 175 |
| other | 39 |

7,399 HFR documents contain at least one numeric selection; 291 contain at least one plain `???` selection; and 5 contain at least one `???` + numeric fallback selector. These document categories can overlap.

This is compatible with `mrp0sel` being heavily used during manual annotation, but **does not prove that every numeric selector means the live page would label that word pre-validated**. The corpus contains multiple projects and workflow histories; HFR itself separately records completion state outside per-word `mrp0sel`.

## Header `<annot>` events are not word validation status

The source header has annotation/edit history, but it is too broad and at the wrong structural level to stand in for grey/magenta word status.

Across all 23,884 production documents:

- 23,538 have at least one header `<annot>` event;
- 346 have none;
- `editor="auto"` with no date occurs 23,566 times;
- empty-editor/no-date annotation events occur 23,565 times;
- many named/datetime editor events also occur.

Among the 8,286 HFR documents:

- 8,253 have an annotation header event;
- only 33 do not;
- the template-like `editor="auto"` event occurs 8,312 times and the empty-editor event 8,311 times.

Those near-universal document events coexist with heterogeneous word selector states. They are editorial/history provenance and must not be presented as a token/analysis validation-status feature.

## What TF 0.4.0 already preserves

TLHdig-TF preserves the source selector mechanics at word level:

- `mrpsel` — the raw `mrp0sel` disambiguation pointer;
- `mrpsel_kind` — parsed selector class (`analysis`, `none`, `unknown`, `DEL`, `AKK`, `HURR`, `HAT`, `SUM`, `LUW`);
- selection-related analysis edges/features preserve selected candidate information and ambiguity without forcing one analysis to become source-authoritative when the source does not do so.

These are useful research semantics and should be documented as such. They are **not renamed validation status** by this research.

## Live presentation mechanism

The independent review required the live display to be traced to its actual presentation hooks rather than merely trusting the legend. `programs/research_annotation_ui.py` therefore fetched three representative public HFR pages plus their linked stylesheets and recorded bounded raw-HTML examples, tag/class counts and response hashes.

Hosted evidence:
- workflow run: `34349566223`
- job: `102459214922`
- exact probe head: `f7d82c56f272ec0b0caf2f22b992b7a57d018cbe`
- conclusion: success

Representative responses:

| page | decoded HTML SHA-256 | bytes |
|---|---|---:|
| KBo 35.208 (CTH 500) | `4a22f1c2d2ecdccc743ae231533a8f4480c52fd756c8f0bfe301d4cba779b7f5` | 28,714 |
| KBo 37.62 (CTH 741) | `8ac49eebe2044537ffb56410961bef820137dffe0e9f070e772be45f1292ffa5` | 25,691 |
| KBo 38.103 (CTH 670) | `10f62d186180c5e1587b236788c713e26f45b26e6bbd9a387b9022796f5abd74` | 34,284 |

All three responses contain the annotation-status legend directly in HTML: `pre-validated (magenta text)` uses inline `color: #b404ae`, while `not validated (gray text)` uses inline `color: #888`.

The actual interlinear presentation is class-based at the rendered word/analysis-cell level:

- `<td class="text">…</td>` is the magenta analysis cell;
- `<td class="grau">…</td>` is the grey analysis cell;
- tooltip-bearing words use `<a … class="ttp3">`;
- the tooltip analysis payload is `<span class="ttp3text">…</span>` for the magenta presentation and `<span class="ttp3grau">…</span>` for the grey presentation.

The stylesheet evidence is explicit:

- `custom.css`, SHA-256 `7fd7cd4d7fd23f1e7ae82dd74b2fcaa94873c2875ac80475c5d07e45bfb0c6a4`, defines `.tblcls .grau { color: #707070; }` and `.tblcls .text { color: #b404ae; }`;
- `ttp3.css`, SHA-256 `232d967efc803ced708c6e5d7a9912a82881302ce25a05f49a2f4e62b8160e86`, defines `.ttp3 .ttp3text` with `color: #B404AE` and `.ttp3 .ttp3grau` with `color: #888`; the latter rule is preceded by the source comment `grau für nicht validierte Annotation` (“grey for non-validated annotation”).

KBo 35.208 demonstrates mixed status in one interlinear context: a displayed `1` has a `ttp3text` tooltip and `text` cell, whereas `DUG`, `KAŠ` and `IŠ-TU` have `ttp3grau` tooltips and `grau` cells. KBo 38.103 likewise mixes grey cells/tooltips such as `an-da` with magenta ones such as `i-en-zi`. This proves that the visible status is emitted at the displayed word/analysis level rather than merely once per document.

KBo 37.62 is an important edge case: the sampled response has `text` / `ttp3text` classes but no grey classes, and several `ttp3text` spans are empty. Therefore **class existence by itself is not a safe source-data predicate**. The presentation classes are evidence for how the live server renders its current status, not a standalone semantic export that can be mechanically joined to distributed XML/TF.

No status-specific `data-*` attribute was observed in these sampled response units. The server emits presentation classes and tooltip payloads; the stable semantic meaning comes from HFR documentation, not from reverse-interpreting colour values alone.

This closes the UI-tracing question but does **not** change the corpus conclusion: the distributed source does not contain a demonstrated, versioned, corpus-wide validation-status field or joinable status export from which TLHdig-TF could reproduce these classes without inference.

## Live-page evidence and its limit

A live page for IBoT 3.129 exposes `mrp0sel="???"` artifacts in unresolved material, supporting a relationship between selector mechanics and annotation workflow. But that source file is one of the 53 committed exclusions (`unparseable`), so it is **not** used as evidence for the semantics of the shipped TF population.

The live interface is authoritative evidence for the current presentation mechanism. It is not a reproducible substitute for a missing exported workflow-status field in the distributed corpus.

## Separate morphology defect discovered during research

The first exploratory census also found opaque HFR analysis-generation/control glyphs at the beginning of some `mrpN` first fields. The current morphology parser can therefore leak those glyphs into derived lexical lemmas. At least 578 shipped TF 0.4.0 lemma assignments were proven marker-prefixed by a conservative detector; the true population is larger because additional circled-marker families were intentionally not interpreted.

This is **not annotation-status evidence**. It is tracked separately in #92: *Separate HFR analysis-generation markers from lexical lemma values*.

## Research conclusion

1. The HFR grey/magenta distinction has a clear authoritative meaning: automatic/context-free annotation versus manual pre-validation.
2. The live server implements that distinction at rendered word/analysis cells and tooltip payloads using `text`/`grau` and `ttp3text`/`ttp3grau` presentation classes.
3. `mrp0sel` is clearly a source disambiguation/selection mechanism and TLHdig-TF already preserves it.
4. A numeric `mrp0sel` is **not sufficient evidence** to assert the live HFR validation-stage label corpus-wide. HFR documents completion status separately in project status files/overview material.
5. Header `<annot>` events are not a word-level validation-status proxy.
6. No reproducible, universally applicable validation-status field has been established in the distributed TLHdig 0.3 XML, and sampled live presentation classes are not such an export.
7. Therefore TLHdig-TF must **not** synthesize a new `validation_status` feature or reproduce grey/magenta browser colours from inference.
8. The useful local semantic is already the selector/disambiguation state. Documentation should explain that state and explicitly distinguish it from HFR workflow validation status; this is tracked by #94 and should coordinate with #44/#46.
9. If HFR later publishes a stable, versioned machine-readable status export with a defensible join key, that should receive a new research/TDD integration ticket rather than changing this conclusion retroactively.

## Acceptance disposition

The exact UI semantics, live HTML/CSS presentation mechanism, and source selector mechanism are established. The distributed XML does not provide enough evidence for a universal first-class validation-stage feature. The safe outcome is **upstream-only workflow status + locally preserved selector state**, with explicit documentation and no production/schema/UI change in #79.
