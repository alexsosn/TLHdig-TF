# Known issues in `tf/0.1.0`

Raised by an independent code review and **verified against the released files**. The
dataset is an integration prototype: the parsing components are well tested, but several
of them are not wired into the generated graph, and some documented guarantees are
therefore false of `0.1.0`.

Status key: ❌ open · 🔧 fixing · ✅ fixed

---

## Critical

### ✅ 1. `src_span` is wrong for repaired documents

`director()` reads the original bytes, applies the repair manifest **in memory**, then
scans the *repaired* stream for byte offsets — while `document.src_file` still names the
unmodified file. **166 of the 173 repaired files change length**, so every `src_span`
after the first patch site is shifted.

Demonstrated on `CTH 167_XML_TLH/KBo 9.43+.xml` (−1 byte): a word's span slices
`<w trans="ša" …>` from the repaired stream and ` <w trans="ša" …` from the original.

This also undermines the decision to store `raw` only when `parse_ok=0`: the argument
was that the verbatim `mrpN` string stays recoverable through `src_span`. For repaired
documents it does not.

**Fixed** by `repair.OffsetMap`, which translates every recorded span back to original
coordinates. Tested against insertion, deletion and multi-patch cases, plus an
integration test that slices `src_file` for every word of a repaired document.

### ✅ 2. The damage model is not in the dataset

`otype.tf` contains: `analysis colon column document edit layout line paragraph sign
surface word`. There is **no `cluster` node type**.

`convert.py` builds a `brackets.Tracker`, feeds it, and calls `finish()` — then never
emits `tracker.clusters` as nodes. Three further integration defects sit behind that:

* **Marker offsets are discarded.** The tokeniser records `(tag, offset)` per sign and
  is tested on a `del_fin` after character 3, but the converter does
  `for tagname, _off in t.markers`, so every marker would land at offset 0.
* **The cross-line lookahead is unused.** `Tracker.start_line(line_no, continues=…)`
  implements the rule measured in plan §6, but the converter calls
  `start_line(self.line_no)` with no hint — so the 74,634 genuine cross-line ranges
  cannot survive as ranges.
* **Sign damage flags are stamped after all of a sign's markers are fed**, so a
  `del_in` mid-sign marks the whole sign damaged, a mid-sign `del_fin` can leave it
  unmarked, and an open+close inside one sign leaves it unmarked. Mid-sign markers were
  the main argument for sign slots, so this needs to be right.

**Fixed**, and the fix needed two rounds. Cluster emission, marker offsets and the
lookahead were all wired in — and the first rebuild still produced **9** cluster nodes
instead of ~648,000, because the tracker was fed a per-document sign counter while
cluster slot sets are looked up among global TF slot numbers. The two coincide only in
the first document, so the single-document unit test could not detect it; the
regression test now builds three. The dataset now has **655,336 clusters** (504,518
`del`, 144,257 `laes`, 6,211 `ras`, 350 `add`), 484,705 with a boundary inside a sign
and 74,884 crossing a line — against 648,480 and 74,634 predicted by the standalone
bracket analysis.

---

## High

### 🔧 3. Contract B is only partly delivered

**Largely delivered since.** `note`, `fragment` and `docgroup` nodes exist, with
`noteref`, `witness`, `edition`, `startsAt` and `endsAt` edges; `<AO:Manuscripts>` is
processed into fragments, inventory numbers and joins; and editorial history now reads
`meta//*` rather than `meta/*`, recovering the ~33% of events held in `<annotation>`
and `<neu>` wrappers. **Still missing: `lex`.** The lexical layer is derivable from
`analysis` nodes but is not built.

The original text of this finding follows.


Missing node types: `note`, `fragment`, `lex`, `docgroup`. (`cluster` now exists —
655,316 of them.) Missing edges:
`witness`, `joins`, `noteref`, `edition`, `lexeme`.

`<AO:Manuscripts>` is not processed at all, so the witness layer — publication sigla,
inventory numbers, 1,060 direct and 166 indirect joins — is absent.

Editorial history is partial: `_document()` uses `root.iterfind("AOHeader/meta/*")`,
which sees direct children only, missing the `<annotation>` wrapper that holds ~58,372
`<annot>` events and the nested `neu` structures.

### ✅ 4. Documents can vanish while the build reports success

The conversion loop has two silent `except: continue` paths (patch failure, parse
failure). **23,937 source files produce 23,884 document nodes** — 52 unaccounted for
beyond the one encrypted file, with no error raised.

**Fixed** by `convert.Ledger`. The build now reports
`23,937 = 23,884 converted + 52 unparseable + 1 encrypted` and aborts if it does not
balance.

### ✅ 2a–2c. Cluster extents, induced flags, marker-only coordinates

Fixed and verified at corpus scale. Orphan ranges now carry their known extent (to line
end / from line start); induced flags are **derived from** cluster coverage rather than
stamped during the walk, so they cannot disagree — asserted per family on every build.
Zero-width ranges are kept as points rather than discarded (that discarding cost 30% of
all ranges in one intermediate build). See [`reports/census.md`](reports/census.md).

### 🔧 2d. `OffsetMap` order-dependence — fixed; its gate still missing

**Fixed.** `OffsetMap` is now a piece table (`repair.py:399`) rebuilt after every patch,
so patch order no longer matters. The original defect was real: patches are proposed
iteratively and revisit earlier sites — `KBo 31.47.xml` fixes a right-hand site, then a
left-hand one, then returns to the right — and a cumulative shift recorded per patch is
never revised, so a left-hand edit silently invalidates every coordinate to its right.

**The gate now exists, and it found the answer to be "no".**
`programs/check_contract_a_graph.py` slices every word's `src_span` out of the file
`src_file` names and requires those bytes to be the signs the word carries. Result over
the shipped dataset:

| | |
|---|---:|
| words verified | 1,229,376 |
| span is a `<w>` element | 1,229,376 |
| slice reproduces the graph's signs | 1,225,269 |
| mismatches | 0 |

Contract A holds for **all 23,711 unrepaired documents**. It fails in **16 repaired
ones**, every one of them in `programs/patches.yaml`, listed with the reason in
`programs/contract_a_known.txt` so a seventeenth fails the gate. The cause is not the
piece table's arithmetic: a crossing-tag repair moves an element boundary — `<AO:Akkgram>`
opening inside one `<w>` and closing inside the next — so expat's idea of where the `<w>`
ends is not the editor's, and the mapped span splits a tag or collapses to zero length.

That is the demonstration this section asked for. Fixing it means resolving the
crossing-tag repairs themselves, which is the philological work in issue 3 awaiting a
Hittitologist, not an offset bug.

### ✅ 15. The compactor rewrote values onto the wrong nodes

**Fixed.** Every published build before 2026-08-30 carried this. `compact.py` groups
nodes that share a value; its reader skipped blank lines. TF writes an empty value *as* a
blank line and advances the implicit node on every line including that one
(`tf/core/data.py:_readDataTf`). Skipping them desynchronised the counter, so every value
after the first empty one was rewritten onto the wrong node.

`<sGr>UR.SAG</sGr>` shipped as `<sGr>UR-SAG</sGr>`: the separator between two signs was
wrong, and `srcxml + after` no longer reproduced the source. On a six-sign document, 5 of
6 `after` values were wrong after compaction.

`check_signs.py` could not see it. It verifies the tokeniser against the source, and the
tokeniser was always right — the corruption happened between the tokeniser and the file
that ships. It was found by `check_contract_a_graph.py` (issue 7) on its first run, which
is the entire argument for gates that start from the artefact rather than the intent.
`programs/tests/test_shard.py` now re-reads every node feature before and after
compaction on each push.

### ❌ 17. Cuneiform is not sign-aligned, and cannot be aligned by counting

**Measured, not assumed.** `cu` holds Unicode cuneiform for a whole line, not per sign,
so the corpus cannot be queried by grapheme, sign frequencies cannot be counted, and
Context-Fabric can show no script/transliteration pair (its sampler walks slots, and no
slot carries cuneiform).

The obvious fix — split `cu` by codepoint and zip it with the line's signs — was tested
across all 412,637 lines:

| | lines | |
|---|---:|---|
| codepoints == non-anchor sign slots | 188,594 | 45.7% |
| surplus == word count | 47,018 | consistent with a word divider |
| surplus == word count − 1 | 42,222 | consistent with dividers *between* words |
| **unexplained** | **130,116** | **32%** |
| no `cu` at all | 4,687 | 1.1% |

The surplus is almost always positive: `cu` has *more* codepoints than we have signs,
+1 on 111,982 lines. A word-divider rule explains a fifth of the mismatches and leaves a
third of the corpus unaccounted for, so there is no single mechanical rule to apply.

Worse, **equal counts do not prove correct pairing**: two sequences of the same length
still misalign if one sign renders as two codepoints and another as none. So even the
45.7% is a hypothesis rather than a result.

**Correction: counting is the wrong tool, but the mapping is largely mechanical.**
Unicode names every cuneiform character after its sign name — `U+12217 CUNEIFORM SIGN
LUGAL` — so a sign's identity can be read straight out of the standard. Measured over
the 1,483,793 pairs on equal-count lines, with only crude normalisation:

| | pairs | |
|---|---:|---|
| `sym` equals the Unicode sign name | 971,407 | **65.5%** |
| differs | 512,386 | 34.5% |

And the differences are not misalignment. Every frequent one is a legitimate
sign-name / phonetic-value pair:

| `sym` | Unicode name | |
|---|---|---|
| `D` | AN | the divine determinative is written with AN |
| `ši` | IGI | IGI has the reading /ši/ |
| `wa` | PI | PI has the reading /wa/ |
| `ku` | DUR2 | |
| `ḫa` | HA | only our normalisation failing on ḫ |
| `DUMU` | TUR | logogram vs sign name |

So the pairs *are* correct where counts match — the Unicode name is a verification
signal, which is exactly what was missing. What is needed is a reading→sign table, and
one exists machine-readably: Oracc's OGSL. That is engineering, not scholarship, though
a Hittitologist should review the result.

This also suggests the way past the 32% of lines whose counts do not match: use the
signs whose Unicode name confirms them as anchors, then align the gaps between anchors,
rather than zipping blindly.

**Independently validated against Oracc's sign list (OSL, `oracc/osl`, `00lib/osl.asl`).**
The learned table in `programs/signmap.tsv` was checked entry by entry against OSL's
`@v` readings and `@ucun` codepoints:

| | entries | |
|---|---:|---|
| agree with OSL | 630 | **96.2%** of those OSL knows |
| disagree | 25 | |
| reading OSL does not list | 364 | mostly Hittite-specific values |

The 25 disagreements are not misalignments:

- `x` → ▒ — the illegible-sign placeholder, not a sign; OSL rightly has no entry
- `ku` / `KU` / `TUŠ` → 𒂉 (named DUR2 in Unicode) — one sign under several names, a
  naming divergence between HPM's font mapping and OSL
- `EZEN₄` → a Private Use Area codepoint with no Unicode name at all

So the corpus-internal table and an external authority agree on the mapping. The
alignment on equal-count lines is confirmed from two independent directions, which is
what the caveat above asked for.

An earlier version of this section said reconstructing the alignment "needs the HPM sign
table or a Hittitologist, not a derivation". That was wrong, and it was wrong in the
direction that stops work: it treated a data-integration task as a scholarly one.

### 🔧 16. 39 lines have no section address

**Open, cause established.** 39 `line` nodes carry no `lnno`, so Text-Fabric reports
`__sections__ WARNING: line-node N has no section heading` and those lines cannot be
cited by section reference — which matters for citing an attestation.

The cause is in the source, not the converter: 25 `<lb>` elements have no `lnr`
attribute and 14 have an empty one, across 35 files. That is exactly the 39. The
converter is right to emit a line node for each — they are real lines with real signs —
but there is no reference to build an address from.

An external report on the pinned commit `5d5e9af` saw five such warnings on the final
five line nodes and reasonably inferred a trailing-boundary bug in section assignment.
That inference does not hold on the current build, where the 39 are scattered through the
range and the last of them is 27,385 nodes short of the end. The five were simply the
ones that build happened to have.

Fixing it means deciding what to address a referenceless line by — a synthesised
ordinal, or nothing — which is an editorial question, not a bug fix.

### 🔧 14. 22 element names are preserved as bytes but not modelled

**Open, inventoried, pinned.** `programs/check_tags.py` declares a destination for every
one of the 61 element names under `<text>` and fails on an undeclared one. That turns
Contract B from a claim into a check — and puts a number on the gap:

| destination | elements | occurrences |
|---|---:|---:|
| modelled (structure, wrapper, damage, annotation, layout, note, apparatus) | 37 | 4,501,718 |
| **raw only** — in `srcxml`, no derived feature | **22** | **3,889** |
| malformed source (`del_iin`, `_in`) | 2 | 2 |

The raw-only set is the real scope of the finding, and it is smaller than it looks:
`AO:ParagrNr` (3,177) dominates, `AO:Sumgram` and `AO:Akkgram` are 48 occurrences
between them, and much of the rest is ODF styling the authoring tool leaked into the
source. Full inventory in [`reports/tags.md`](reports/tags.md).

### 🔧 13. Nested `<w>` inside a repaired span loses its content

**Open, measured, pinned — now 15, down from 310.** 297 of the original 310 were
literally `<w></w>`, which tokenises to nothing, so the converter returned without
emitting either node and the element left no trace in any count; those now get a layout
node with their span. The remaining 15, and the 45 repaired files that fail the filtered
sign round-trip (299,941 bytes), share the cause below.
Both have one cause: `convert.py` skips a nested `<w>` because it is "covered by the
enclosing word's bytes", and in these documents the crossing-tag repair leaves a `<w>`
span enclosing whole lines — 2,397 `<lb>`, 2,047 `<w>`, 208 `<clb>` sit inside dropped
tokens. The enclosing word then tokenises to a single empty token, which the converter
filters, and the children go with it.

The structural *nodes* survive (the walk uses the parsed tree, not the byte spans, and
`reports/structure.md` shows line/colon/note matching exactly). What is lost is the sign
content of the swallowed words.

`programs/check_structure.py` pins the deficit at 310 and fails if it grows; the 45 files
are listed in `programs/known_lossy.txt` with this reason. The fix is to descend into a
nested `<w>` when its parent yields no slots, rather than assuming coverage.

### 🔧 5. The gates do not gate

* ✅ `check_morph.py` now fails above its measured residual.
* ✅ The ledger now checks a checked-in `programs/excluded.txt` rather than mere
  arithmetic, and `patch_failed` is fatal.
* ✅ `programs/census.py` regenerates `reports/census.md` from the shipped dataset and
  fails on a broken invariant.
* ✅ `programs/check_markers.py` counts damage markers in the **source XML** with an
  independent parser and requires the shipped graph to match. It shares no code with the
  converter, which is the whole point: the census compares induced flags against the
  cluster coverage they are derived from, so it reported "all invariants hold" through
  four builds that were losing markers. See [`reports/markers.md`](reports/markers.md).
* ✅ `build.py` fails the build if markers are not conserved, counted per document
  inside the walk. It no longer reloads after compaction — that was a second full load
  of the graph the same process had just written, so it checked the writer against
  itself, and cost ~21 minutes per build to do it.
* ✅ CI runs the unit suite, corpus identity, the repair manifest, the sign round-trip
  and the morphology gate on every push.
* 🔧 `census.py` and `check_markers.py` are **not** in CI: both need a full ~30-minute
  build. They are release gates, run by hand before publishing.
* ✅ `check_signs.py` and `check_morph.py` now run over the **repaired** stream, the same
  bytes the converter reads. Reading raw source skipped the 173 repaired files entirely,
  so a defect confined to repaired content was outside both gates — and switching them
  over immediately exposed 45 files (issue 13 above).
* ✅ `programs/check_structure.py` counts `<lb>`/`<clb>`/`<note>`/`<w>` in the source and
  requires the graph to match. This is the check that was missing: the census compared the
  graph against itself, so it reported "all invariants hold" while 15,434 lines, 6,802
  colons and 3,848 notes were being deleted as unlinked nodes.
* ✅ `programs/check_stamp.py` binds `BUILD-COMPLETE` to a digest of the `.tf` files it
  certifies, so a stamp cannot survive an unverified in-place rebuild.
* ✅ `programs/check_app.py` validates `app/config.yaml` against the shipped dataset in
  under a second. TF only checks an app config when `use()` loads the corpus, and a
  `features:` entry naming a feature absent from that node type never raises at all.
* ✅ `programs/check_contract_a_graph.py` starts from the shipped graph: for every
  `word` it slices `src_span` out of the file `src_file` names and requires those bytes
  to be the signs the word carries. It found issue 15 on its first run.
* ✅ `programs/tests/test_shard.py` builds a real dataset from 91 adversarial documents
  on every push and compares source counts with graph counts, in ~13 seconds.
* 🔧 `check_contract_a.py` still validates the source against itself. It is now a
  tokeniser test rather than a Contract A gate, and should be renamed to say so;
  `check_contract_a_graph.py` is the gate.

### 🔧 6. Duplicate `docid` makes section addressing ambiguous

**Grouping implemented:** `docgroup` nodes with `edition` edges now express which
records claim the same manuscript. `docid` itself is still not unique, so a
`(docid, …)` section address can still be ambiguous — that is inherent to using it as
the level-1 section feature and would need a different section key to resolve.

The original text of this finding follows.


`docid` is the level-1 section feature, and **141 values are shared by more than one
document node** (`KUB 26.71` covers 3). The planned `docgroup`/`edition` layer that
would keep record identity separate from manuscript identity is not implemented.

---

## Medium

### 🔧 7. Crossing-tag repairs make structural choices

The manifest's safeguards (SHA-256, exact bytes, unique target, post-repair parse) are
sound for lexical damage. But for `<w><AO:Akkgram>…</w>…</AO:Akkgram>` the algorithm
*chooses* to close the wrapper before `</w>` and delete the later close. That changes
which material lies inside the Akkadogram. XML validity cannot tell whether the intended
correction was to move the wrapper boundary or the word boundary.

**Catalogued, not resolved.** All 74 are listed in
[`reports/crossing-tag-review.md`](reports/crossing-tag-review.md) with the old bytes,
the new bytes, and which element's close is moved — 62 files, and in 47 cases it is the
`</w>` word boundary itself that shifts, with the rest moving `AO:HitGLOS` (9),
`AO:TxtPubl` (7), `AO:KolonNr` (3) and a few others.

This needs a Hittitologist, not more code. XML validity cannot distinguish "the editor
meant the wrapper to end here" from "the editor meant the word to end here", and the
converter should not be the thing that decides. Every other patch class (406 stray
`<w` fragments, 55 stray closes, 90 escaping fixes) is mechanical and is not listed.

### ✅ 8. The published files are not the files that were load-tested

`convert.build()` writes and loads the dataset; `build.py` then rewrites every node
feature in place with the compactor and **does not reload**. The reported counts come
from the pre-compaction API. The compactor's tests check its output through its own
parser, not through Text-Fabric.

**Fixed**: `build.py` reloads the compacted dataset and runs a section query, failing
the build if either breaks.

---

## What is sound

The sign tokeniser (100% byte round-trip, adversarial cases for wrappers, mid-sign
markers, separators), the morphology parser (`mrp0`, sparse indices, four separator
forms, literal `+` in data, field-4 classification, selector variants), and the
hash-pinned repair manifest are all in good shape. The problem is localised: components
were tested more thoroughly than they were connected.
