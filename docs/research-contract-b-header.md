# Research: Contract B coverage of `AOHeader`

Issue: #56

## Scope

Contract B is the repository gate implemented by `programs/check_tags.py`: every source element the converter accepts must have an explicit declared disposition. This research asks whether that contract covers `AOHeader`, and if not, how to extend the gate without falsely claiming that currently dropped header data is preserved.

This is research only. No converter/schema/release behavior changes are made here.

## Current gate boundary

`programs/check_tags.py` parses each repaired source document and then does:

```python
text = root.find(".//{*}text")
if text is None:
    continue
for el in text.iter():
    ...
```

The generated `reports/tags.md` therefore certifies exactly **61 element names under `<text>`**. `AOHeader` is a sibling of `body`, not a descendant of `<text>`, so no header element is currently included in Contract B.

The implementation and report agree on that narrow boundary. The problem is the contract wording: `programs/tlhdig/tags.py` says the declaration table covers “every inline AOxml element”, and the checker docstring says an unknown tag survives in `srcxml`. That safety argument is true for body/sign markup only.

## Why `raw` is not a truthful header fallback

The current converter creates document nodes from `AOHeader/docID`, source-path metadata, body language, selected edit-history records, and manuscript apparatus. It does **not** assign `srcxml` or `src_span` to document nodes.

The provenance module likewise documents `srcxml` as a verbatim source fragment of each sign and `src_span` as source byte ranges for source-derived graph nodes. The shipped 0.3.0 graph does not expose either feature on `document` nodes.

Therefore an undeclared body tag can still be byte-preserved in sign provenance, but an unconsumed header element can be lost completely. Extending `tags.DESTINATION` with `raw` for header elements would make the gate green while preserving the defect.

## Header vocabulary and existing converter consumption

The current header vocabulary has **31 distinct element names** over the repaired converted stream (23,884 documents), measured when #56 was filed. It decomposes into these classes:

### Header structure / wrappers

- `AOHeader`
- `docID`
- `meta`
- `annotation`
- `neu`

These establish header structure or wrap editorial records. `docID` is consumed separately by `_document()`; the wrappers themselves are not represented as graph objects.

### Recognized edit-event kinds

The converter has a private `_EDIT_KINDS` set containing 21 names:

- `kor`, `kor2`, `kor1kf`
- `annot`, `uebern`, `format`, `author`, `kolon`
- `val`, `trlst`, `join`, `merge`, `aufheb`, `aufloes`, `korof`, `koltaf`, `kolfot`, `kolfot2`
- `cth`, `creation-date`, `AOxml-creation`

For descendants of `AOHeader/meta`, `_document()` creates `edit` nodes only when the element name is in this set. The edit node stores `kind`, `order`, and only attributes listed in `_EDIT_ATTRS`:

`editor`, `date`, `part`, `src`, `frgm`, `docs`, `comment`, `author`, `alt`, `neu`.

This is a hidden second declaration table: Contract B does not currently verify that the source header vocabulary and this converter allowlist remain synchronized.

### Known dropped / malformed header names

Current issue-level corpus research has already identified five names outside `_EDIT_KINDS`:

- `merged` — 75 occurrences
- `doc` — 149 occurrences
- `mDocID` — 148 occurrences, carrying constituent manuscript identifiers
- `mDodID` — 1 occurrence, source typo for `mDocID`
- `ann` — 1 occurrence, source typo for `annot`

These are not preserved by a document-level raw provenance feature. Their semantic/provenance repair is owned by #57/#58, not by this validator ticket.

The 5 structural/wrapper names + 21 recognized edit kinds + 5 dropped/malformed names account for the measured **31 header element names** exactly.

## Attribute coverage

#56 records **73 distinct element-name@attribute pairs** in `AOHeader`. Contract B currently checks none of them.

The converter intentionally consumes only the ten `_EDIT_ATTRS` listed above from recognized meta events. At least one known real loss is already measured independently: `annot@data` occurs **1,738** times and is not in `_EDIT_ATTRS`, so it is silently discarded.

This means an element-only inventory is insufficient for the header. The extended contract must inventory and declare attributes by element (or by an equivalently precise rule), otherwise new source attributes can appear on an already-known header element and remain invisible to the gate.

## Interaction with sibling work

- #57 owns making the document header recoverable and deciding how `mDocID`/other dropped content is represented.
- #58 owns whether `docid_raw` should remain a bespoke core feature or be retired in favor of header provenance.
- #56 should **not** implement either decision. Its responsibility is detection and explicit disposition.

The validator therefore needs a status that means, in effect, **known-unpreserved / follow-up-owned**. Such a status is deliberately different from body `raw`: it keeps the current loss visible and documented without claiming preservation.

## Required contract properties

A correct fix should satisfy all of these:

1. Report body and header inventories as separate regions so coverage is auditable.
2. Fail on a new/undeclared header element.
3. Fail on a new/undeclared header attribute pair, even when the element itself is known.
4. Centralize the declared header edit kinds/attributes so converter behavior and Contract B cannot drift through independent private allowlists.
5. Distinguish represented/consumed header data from known-unpreserved data.
6. Keep the existing body `raw` semantics unchanged: body raw-only tags still survive in provenance/`othertags` according to the current body contract.
7. Do not change TF feature/node/edge bytes or `TF_VERSION`; this ticket is a validator/reporting/code-contract change only.
8. Keep #57/#58 as the owners of actual header preservation/schema changes.

## RED hypotheses for the plan

The production fix should be preceded by tests that fail on current main for at least:

- a new header element under `AOHeader/meta`;
- a new attribute on an existing header event;
- a known current dropped header element being classified as preserved/raw when it is not;
- drift where converter edit kinds diverge from the Contract-B header declaration;
- report generation that collapses body and header into one undifferentiated inventory.

## Release impact

No corpus artifact change is justified by the validator fix itself. If implementation remains limited to checker/declaration/report code, `tf/0.3.0` remains byte-identical and no TF version bump is required. Any attempt to preserve new header data belongs to #57/#58 and would require their own artifact/version analysis.
