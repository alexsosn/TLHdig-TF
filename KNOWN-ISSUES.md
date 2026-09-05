# Known issues in `tf/0.2.1`

This is the **current-state register** for the shipped Text-Fabric artifact. It is not a
chronological debugging diary. Generated reports are the source of truth for counts; if
a number here disagrees with a generated report, the report wins.

The historical `tf/0.1.0` prototype was rebuilt in place, so that bare version string does
not identify every historical state. Starting with `0.2.0`, published release directories
are immutable; for old `0.1.0` states, record the repository commit SHA as well.

Status key:

- ❌ **open defect** — known incorrect or lossy behaviour;
- ⛔ **blocked** — resolution needs a philological/upstream/editorial decision;
- ⚠ **known limitation** — deliberately incomplete or not fully validated in this build;
- ✅ **resolved / verified** — retained only in the short historical summary at the end.

## Current artifact at a glance

The generated reports currently describe:

- 23,937 source XML files;
- 23,884 converted document nodes;
- 53 declared exclusions: 52 unparseable files and 1 encrypted file;
- 8,289,535 TF nodes in total;
- 656,389 `cluster` nodes;
- 28,282 `lex` nodes;
- 2,993,867 of 3,386,344 signs carrying `cu_sign` (88.4%).

See [`reports/census.md`](reports/census.md),
[`reports/structure.md`](reports/structure.md), and
[`reports/alignment.md`](reports/alignment.md) for generated numbers.

---

## Research blockers

### ⛔ Crossing-tag repairs require philological review

**Legacy review ID: 7.**

The repair manifest contains **74 repairs in 62 files** that do more than restore XML
well-formedness: they choose where an element boundary lands. In **47** cases the moved
boundary is `</w>` itself; the others move wrappers such as `AO:HitGLOS`, `AO:TxtPubl`
and `AO:KolonNr`.

The repair machinery can prove that the patch applies to the expected bytes and produces
parseable XML. It cannot prove whether the editor intended the wrapper boundary or the
word boundary to move. That is a philological decision.

All 74 are listed with before/after bytes in
[`reports/crossing-tag-review.md`](reports/crossing-tag-review.md). They overlap with two
measured downstream problems:

- **16 repaired documents** are known Contract-A exceptions because the structural
  repair changes the parsed word boundary relative to the original file bytes;
- **45 repaired files** are on the filtered sign-round-trip known-loss list, and the
  remaining structural deficit is tied to the same nested-`<w>` pattern.

These repairs should be reviewed before treating the corpus as research-ready.

### ❌ Known lossy word structures remain

**Legacy review ID: 13.**

The current structure report shows **15 missing top-level `<w>` elements**. The parser
sees a nested `<w>` inside a repaired span, the converter assumes that the enclosing word
already covers its bytes, and when that enclosing word yields no slots the nested content
is lost with it.

[`programs/check_structure.py`](programs/check_structure.py) treats 15 as the current
known baseline and fails only if the deficit grows. That makes it a regression guard; it
does **not** mean that structure conservation is complete. The generated report is
[`reports/structure.md`](reports/structure.md).

There is also one separate balanced-but-lossy source case:
`CTH 530_XML_KULTINV/KBo 70.109+.xml`. An unclosed `<w>` swallows roughly 30 lines while
the document remains XML-well-formed, so a well-formedness check cannot detect the
problem. It is recorded in [`programs/known_lossy.txt`](programs/known_lossy.txt).

### ⚠ Contract A has declared repaired-document exceptions

**Legacy review IDs: 1 and 2d.**

`repair.OffsetMap` now maps repaired-stream coordinates back to original-file
coordinates correctly, including insertion, deletion and out-of-order patch cases.
Contract A holds for all **23,711 unrepaired documents**.

It still cannot describe an original `<w>` byte span faithfully when a crossing-tag
repair changes the element boundary itself. **16 repaired documents** are therefore
listed in [`programs/contract_a_known.txt`](programs/contract_a_known.txt); a seventeenth
fails the gate.

This is a declared exception caused by unresolved structural repairs, not an outstanding
piece-table arithmetic bug. See
[`reports/contract_a_graph.md`](reports/contract_a_graph.md).

---

## Coverage and addressing

### ⚠ 53 source files are excluded from the graph

The build ledger balances exactly:

`23,937 sources = 23,884 converted + 52 unparseable + 1 encrypted`.

This is no longer silent data loss: the exclusions are checked in and a new exclusion
fails the build. It remains a coverage limitation of the shipped corpus.

### ❌ 39 lines have no section address

**Legacy review ID: 16.**

Thirty-nine `line` nodes carry no usable `lnno`: 25 source `<lb>` elements have no `lnr`
attribute and 14 have an empty one, across 35 files. The lines themselves are real and
are preserved, but they cannot be cited through the normal `(docid, collabel, lnno)`
section address.

This also exposes a validation weakness: `reports/census.md` currently reports
`section addressing | OK`, but `programs/census.py` establishes that with one known
`nodeFromSection()` probe. It is **not** an exhaustive assertion that every line has a
section heading.

Resolving the 39 lines requires an editorial policy: synthesize an address or preserve
the absence explicitly.

### ⚠ `docid` is not a unique section key

**Legacy review ID: 6.**

**141 `docid` values** are shared by more than one document node. `docgroup` nodes and
`edition` edges now preserve the relationship between records that claim the same
manuscript, but the level-1 section feature is still `docid`.

As a result, `(docid, collabel, lnno)` can be ambiguous for those records. Callers that
need an unambiguous identifier within one release should retain `src_file` as the
release-scoped source-record identity as well; it is not persistent across releases.

---

## Incomplete modelling

### ⚠ 20 source element names are deliberately raw-only

**Legacy review ID: 14.**

[`reports/tags.md`](reports/tags.md) currently lists **20 raw-only element names with
3,841 occurrences**. They survive verbatim in `srcxml` but have no derived semantic
feature. `AO:ParagrNr` dominates the set with 3,177 occurrences; much of the remainder
is styling or authoring-tool residue.

Two additional malformed element names occur once each and are preserved as source
bytes without assigning them a meaning.

Raw-only preservation is a conscious limitation, not evidence that these bytes vanished.
Any raw-only element promoted to a semantic feature should be accompanied by a corpus
measurement and a gate.

### ⚠ Some preservation-map targets are still not implemented

The lexical layer is **not** one of the missing pieces: the current dataset contains
28,282 `lex` nodes and `lexeme` edges.

The remaining declared model gaps include:

- manuscript `joins` edges: direct/indirect join information is still flattened rather
  than represented as fragment-to-fragment graph edges;
- `sign.lang`: language exists at document/line/colon level, not on every sign;
- `cu_pua_unmapped`: PUA use is recorded, but mapped vs. unmapped PUA is not separated
  into the planned feature.

The implementation-status matrix in
[`docs/TF-CONVERSION-PLAN.md`](docs/TF-CONVERSION-PLAN.md) should be read as a plan/status
matrix rather than as a guarantee of the shipped schema.

---

## Cuneiform alignment limitations

### ⚠ Sign-level cuneiform is partial, not absent

**Legacy review ID: 17.**

The shipped graph has sign-level cuneiform for **2,993,867 / 3,386,344 signs (88.4%)**.
By line, **45,849 of the 407,950 lines that carry cuneiform (11.2%)** remain at
alignment level 0; a further 4,687 lines have no `cu` at all and are out of scope. The
current coverage by mechanism is generated in
[`reports/alignment.md`](reports/alignment.md).

A missing `cu_sign` has two distinct causes and callers should not conflate them. On
**2,347 signs** the edition itself could not draw the glyph, and those carry
`cu_unrendered`; elsewhere the absence means the alignment could not decide. `cu` holds
7,462 such marks in all — the remaining 5,115 sit on level-0 lines, which carry no
per-sign values at all, so they cannot be flagged.

The alignment is also checked against external sign-list traditions. In the latest
external report, 31,055 assigned signs are outvoted by every external list that knows the
reading. These are candidates for review, not automatically 31,055 conversion errors:
the external lists also disagree with each other and do not encode every Hittite usage.
See [`reports/signrefs.md`](reports/signrefs.md).

The external-reference check is **not a normal hosted-CI guarantee**. The reference files
live in git-ignored `refs/`; when they are absent, the CI step prints a skip message and
returns success. Treat it as a local/release validation unless the references are made
available to the runner.

---

## Validation limitations

### ❌ `BUILD-COMPLETE` certifies less than "all release gates passed"

**Legacy review ID: 5.**

`programs/build.py` deliberately does not mark a rebuilt dataset complete.
`programs/census.py` loads the shipped `.tf` files in a fresh process, checks its census
invariants, probes one section address, and then writes `BUILD-COMPLETE` bound to the
dataset digest.

That is useful, but it is narrower than a complete release certification. The stamp does
not itself prove that all of these ran successfully for the same artifact:

- `check_structure.py`;
- `check_contract_a_graph.py`;
- `check_markers.py`;
- `check_signrefs.py` with external references actually present.

Current hosted CI runs the unit/adversarial shard, corpus identity, repair verification,
sign round-trip, morphology, app validation, stamp validation, tag inventory,
provenance-split check and cuneiform alignment. The external sign-list step may skip when
`refs/` is absent, and the full release checks above are not all orchestrated by one
command.

Until a single release-check command owns the stamp, interpret `BUILD-COMPLETE` as
**"this artifact loaded from disk and passed the census/stamp invariants"**, not as
"every research-readiness gate passed".

### ⚠ Known-defect lists are regression guards, not zero-defect proofs

Files such as `programs/known_lossy.txt`, `programs/contract_a_known.txt` and
`programs/excluded.txt` are intentionally explicit. A new entry that appears without a
corresponding update fails the relevant gate rather than disappearing into a percentage.

That is the right regression strategy, but a green gate can still mean "the known defect
set did not grow". Consumers should not read allowlisted known loss as successful full
fidelity.

---

## Resolved and verified findings

The detailed forensic history is intentionally not repeated here; Git history and
[`wiki/independent-code-architecture-review-2026-08-30.md`](wiki/independent-code-architecture-review-2026-08-30.md)
preserve the investigation. The following earlier findings are now resolved or
substantially superseded:

- `OffsetMap` arithmetic/order dependence was replaced by a piece-table mapping; only the
  structural-repair exceptions described above remain;
- the damage model is emitted as `cluster` nodes, marker conservation is measured, and
  induced sign flags are derived from cluster coverage;
- silent document disappearance was replaced by a balancing ledger with checked-in
  exclusions;
- contentless structural nodes are retained with anchor slots; current line, colon and
  note counts match the source exactly;
- the compactor blank-line bug that shifted feature values onto the wrong nodes was fixed
  and covered by an adversarial shard test;
- `note`, `fragment`, `docgroup`, `lex`, `witness`, `edition`, `noteref` and `lexeme`
  layers now exist in the shipped graph;
- `app/config.yaml` exists and is validated against the dataset;
- sign-level cuneiform alignment exists and is measured; the remaining limitation is
  incomplete coverage/validation, not absence of an alignment layer.

For current numerical state, prefer the generated files under [`reports/`](reports/)
over historical numbers in old review discussions or commit messages.
