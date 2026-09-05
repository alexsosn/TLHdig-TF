# Research: `docid_raw` semantics in TLHdig Beta 0.3

This report is the empirical prerequisite for issue #10. It was generated from the pinned
TLHdig Beta 0.3 corpus before any Phase 4 production or test change.

## Question

The converter currently computes:

```python
docid = (root.findtext("AOHeader/docID") or Path(rel).stem).strip()
docid_raw = docid
```

So `docid_raw` is normalized/fallback-derived rather than source-derived. The research
measures the actual source cases before choosing a replacement contract.

## Method

The measurement follows the converter input boundary, not just parse-clean raw XML:

1. enumerate `corpus_files()` from the pinned corpus;
2. skip the encrypted record exactly as the converter does;
3. apply `patches.yaml` with its expected SHA;
4. run `source.scan()` and `lxml.etree.fromstring()`, matching `convert.director()`;
5. exclude records still unparseable and records with no `body/div1/text`;
6. inspect `AOHeader/docID` with both `find()` and the converter's `findtext()` API.

Here **raw means parsed XML element text before `.strip()` and before filename fallback**.
It is not byte-for-byte XML markup: XML entity expansion and parser line-ending semantics
have already been applied.

## Population

| category | count |
|---|---:|
| source `*.xml` records | 23,937 |
| files with repair-manifest entries | 173 |
| encrypted exclusions | 1 |
| unparseable after approved repairs | 52 |
| missing text element | 0 |
| **converter document population** | **23,884** |

The converter-document count is asserted to equal 23,884, matching TF 0.2.0.

## `<docID>` observations on converter documents

| observation | count |
|---|---:|
| `<docID>` element present | 23,884 |
| `<docID>` element missing | 0 |
| present element with `findtext() is None` | 0 |
| parsed value is exactly empty string | 0 |
| parsed value is non-empty but whitespace-only | 0 |
| parsed value differs from `.strip()` | 3 |
| parsed value contains TAB/LF/CR | 0 |
| `<docID>` has child elements | 0 |
| current filename-fallback cases (`not raw`) | 0 |
| current `docid` blank because raw is whitespace-only | 0 |
| current `docid` happens to equal filename stem | 23,761 |

Trim-delta distribution: **lead=0, trail=1: 3**.

## Artifact impact under candidate policies

This measures consequences; it does not choose policy.

- Preserving parsed text for every **present** `<docID>` would change **3** `docid_raw` values relative to TF 0.2.0.
- Representing a **missing** `<docID>` by an empty string would change another **0** fallback-derived values. Omitting the feature is a distinct plan-stage option.
- Missing/empty values that currently trigger filename fallback: **0**.

Therefore the plan must not assume this is metadata-only: release impact follows from the
measured populations plus the explicit missing/empty representation chosen later.

## Examples where raw text differs from normalized `docid`

| path | parsed value / note |
|---|---|
| `CTH 209_XML_TLH/KBo 50.89 .xml` | `'KBo 50.89 ' — stripped='KBo 50.89'` |
| `CTH 628_XML_HFR/Merzifon I .xml` | `'Merzifon I ' — stripped='Merzifon I'` |
| `CTH 670_XML_TLH/KBo 71.241 .xml` | `'KBo 71.241 ' — stripped='KBo 71.241'` |

## Missing `<docID>` examples

_None observed._

## Empty `<docID>` examples

_None observed._

## Whitespace-only `<docID>` examples

_None observed._

## TAB/newline/carriage-return examples

_None observed._

## Current filename-fallback examples

_None observed._

## Nested-content examples

_None observed._

## Constraints for the implementation plan

1. Preserve the existing `docid` expression and observable behavior in this ticket;
   whitespace-only behavior is measured here, not silently repaired.
2. `docid_raw` must be source-derived. Filename fallback may be useful for `docid`, but
   calling a fallback value `raw` is semantically false.
3. Missing and present-empty are distinguishable at the XML API boundary even if TF
   ultimately chooses the same representation; the plan must state that choice.
4. TAB/LF/CR counts determine whether current corpus data needs a serialization policy;
   future robustness may still justify a synthetic TF round-trip test.
5. Do not change section addressing, duplicate grouping, or introduce a record ID.
