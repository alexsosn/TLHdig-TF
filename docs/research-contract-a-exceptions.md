# Research: Contract-A provenance exceptions

Issue: #142  
Baseline: `main@0261d2d46b3419a1f907e231a03f749d133cfb5e`

## Problem statement

`programs/contract_a_known.txt` currently exempts 16 source files from the graph-level
Contract-A check. Its header and every row describe them as crossing-tag repairs whose
word boundaries no longer map soundly to the immutable source.

That description is factually too broad.

The frozen #12 crossing-recovery inventory contains only 9 of those 16 paths. Seven
allowlisted files have no crossing event at all. The canonical `src_span` feature
description is also stale: it says all length-changing repaired documents index the
repaired byte stream, but production conversion calls
`OffsetMap.span_to_original()` before emitting `src_span`.

This ticket must therefore remeasure the exceptions rather than preserve their
historical explanation.

## Static census before graph measurement

The current allowlist has 16 files.

### Owned by #12 crossing recovery: 9

| source | current repair shape |
|---|---|
| `CTH 144_XML_SVH/KUB 26.29+.xml` | crossing wrapper close + structurally coupled delayed close deletion |
| `CTH 381_XML_GEBET/KUB 6.46.xml` | stray wrapper close + crossing wrapper close |
| `CTH 409_XML_BESRIT/KBo 53.35+.xml` | four crossing wrapper closes plus four coupled delayed-close removals |
| `CTH 420_XML_TLH/KBo 53.31.xml` | crossing wrapper close |
| `CTH 458_XML_BESRIT/KBo 56.227.xml` | three crossing wrapper closes plus three coupled delayed-close removals |
| `CTH 460_XML_TLH/KBo 56.45.xml` | two crossing wrapper closes plus two coupled delayed-close removals |
| `CTH 570_XML_HDivT/KUB 50.123.xml` | one independent stray `</w>` plus an end-of-text crossing/open-word defect |
| `CTH 577_XML_HDivT/AT 454.xml` | crossing `sGr` close |
| `CTH 819_XML_TLH/KUB 4.89.xml` | crossing `AO:TabSep` close + coupled delayed-close removal |

These paths should not be independently “fixed” by #142 while #12 is changing their
prepared-source semantics. #142 still has to measure them so the current provenance
failure is known precisely.

### Non-crossing exceptions: 7

| source | actual repair class |
|---|---|
| `CTH 372_XML_GEBET/KUB 31.127+.xml` | three independent stray `</w>` removals |
| `CTH 526_XML_KULTINV/KUB 42.100+.xml` | two independent stray `</w>` removals |
| `CTH 526_XML_KULTINV/VS.NF 12.111.xml` | one independent stray `</w>` removal |
| `CTH 529_XML_KULTINV/KBo 12.53+.xml` | four independent stray `</w>` removals |
| `CTH 581_XML_HDivT/KBo 18.142.xml` | escape one literal `<` inside a footnote attribute value |
| `CTH 790_XML_TLH/KBo 64.188.xml` | three stray ODF close-tag removals |
| `CTH 831_XML_TLH/KBo 64.209.xml` | five malformed duplicate/bare `<w` fragment removals |

None of these seven belongs to the #12 crossing-event census. KBo 70.109+, the
balanced-but-lossy source owned by #13, is a different file and is already represented
in `known_lossy.txt`; it must not be conflated with these provenance exceptions.

## Coordinate contract in current code

The current source path is:

1. immutable source bytes are read;
2. the repair manifest is applied in memory;
3. Expat scans the repaired byte stream and records element byte spans;
4. `OffsetMap(original, patches)` maps repaired coordinates back to immutable source;
5. `_State._span()` emits the mapped coordinates as `src_span`;
6. `document.src_file` names the immutable source path.

`OffsetMap` is a piece table. Offsets in unchanged copy pieces map one-to-one.
Offsets inside replacement pieces are deliberately inexact and collapse to the
original start of the replacement. The meaningful measurement for every candidate word
therefore includes both:

- `is_exact(outer_start)`;
- `is_exact(outer_end)`;

followed by the actual mapped immutable byte slice.

A length-changing repair elsewhere in the document does **not** by itself make later
spans ambiguous. Copy pieces after the edit can still map exactly.

## Graph contract in current code

`programs/check_contract_a_graph.py` verifies the shipped graph, but skips every word
in an allowlisted document before inspecting it. This means its current zero-mismatch
result says nothing about which word in these 16 documents still fails.

The remeasurement must run the same checks without the exemption:

- every graph word with `src_span` must slice a valid immutable-source `<w>` element;
- tokenising the sliced immutable bytes must reproduce the graph's
  `srcxml + after` sign stream, except for separately declared `known_lossy`
  semantics;
- failures must report the graph node and span, not only the file.

Source-coordinate ambiguity and graph/token mismatch are separate measurements. A word
can have exact repaired→original boundaries yet still disagree with the graph for a
different semantic reason.

## Current corpus-wide baseline

The committed report currently records:

- 1,228,007 graph words with `src_span`;
- 1,228,007 accepted as a `<w>` slice after excluding allowlisted documents;
- 1,223,906 byte-identical graph/source words;
- 4,101 words skipped through `known_lossy.txt`;
- 6,505 words skipped through `contract_a_known.txt`;
- zero mismatches outside those explicit exclusions.

The 6,505 skipped words are the population #142 must open up and classify.

## Research measurement

A deterministic corpus census will be generated from the committed current artifact,
the pinned corpus, and the current repair manifest.

For each of the 16 files it will record:

- immutable source SHA;
- ordered repair reasons and a coarse repair class;
- whether the path is in the frozen #12 crossing inventory;
- number of converter-visible top-level `w` source spans;
- count of inexact start and end boundaries under `OffsetMap`;
- representative inexact span offsets and their mapped immutable coordinates;
- graph word count;
- graph spans that do not slice an immutable-source `<w>`;
- graph/source sign mismatches;
- representative failing node/span/chunks;
- whether the current allowlist exception is actually required.

The census is evidence. It does not itself delete an exception.

## Research hypotheses to falsify

1. **All seven non-crossing exceptions are stale.**  
   Plausible because `OffsetMap` was introduced after the historical blanket warning,
   but not assumed. Any inexact boundary or graph mismatch keeps the exception until
   its class has a tested fix.

2. **Crossing exceptions are boundary ambiguity only.**  
   Not assumed. #12 already demonstrated graph-level filtered-loss effects in a
   different set of crossing documents; the graph census must distinguish bad
   coordinates from token/structure loss.

3. **Every length-changing repair makes downstream spans repaired-stream-relative.**  
   Expected false by construction of the piece table. This obsolete blanket statement
   should be removed from `src_span` documentation once measured evidence is frozen.

## Ownership boundary

- #12 owns structural recovery for the 62 reviewed crossing files.
- #13 owns the balanced-but-lossy KBo 70.109+ structure.
- #142 owns provenance exception measurement, non-crossing provenance fixes, the
  allowlist semantics, and the canonical `src_span` description.
- If measurement finds a graph/sign bug independent of coordinate mapping, that root
  cause should receive its own issue rather than being hidden under a provenance
  exception.
