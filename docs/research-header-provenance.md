# Research: byte-exact document-header provenance

Issues: #57, #58, #10

## Question

The converter currently makes the body recoverable through the optional provenance module but leaves the entire `AOHeader` outside Contract A. This research asks whether the existing `src_span` / `srcxml` mechanism can be extended to `document` nodes without inventing a parallel provenance model, and whether doing so makes the bespoke core feature `docid_raw` obsolete.

This phase is read-only with respect to TF artifacts. `programs/research_header_provenance.py` measures the pinned corpus; the temporary research workflow runs it in a clean hosted checkout. No converter/schema/version change is made before a separate plan and RED gate.

## Current architecture

### What the converter preserves today

`programs/tlhdig/source.py` scans the exact source byte stream and reports outer/inner byte spans for every XML element. `convert.py` uses those spans for source-derived graph nodes. Repairs are applied in memory; `repair.OffsetMap` translates repaired offsets back to the original on-disk file named by `src_file`.

The optional provenance module contains exactly two node features:

- `src_span` — original-file byte range;
- `srcxml` — verbatim source fragment retained on graph nodes (currently sign-level fragments).

`build.py` physically moves those features from the main TF directory into `tf-provenance/<version>`, so adding values on another node type does not require a new module or a new feature name.

### The blind spot

`_document()` creates a `document` node and normalized/queryable metadata, but never assigns either provenance feature. It extracts `docID` separately and iterates only `AOHeader/meta//*` for known edit-event kinds. Consequently, metadata not explicitly modelled is unrecoverable from the TF graph.

Contract B now detects this loss and currently reports, among other things:

- 148 `mDocID` values;
- 75 `merged` wrappers;
- 149 `doc` wrappers;
- 1,738 ordinary `annot@data` attributes;
- one malformed `mDodID` and one malformed `ann` record;
- three direct `AOHeader/annot` events outside the converter's `meta//*` path.

The provenance change should make all of these bytes recoverable without pretending they are semantically modelled.

## Proposed provenance unit

The natural source unit is the **outer byte range of the single direct `<AOHeader>...</AOHeader>` element** associated with the emitted document node.

For a document node `d`:

- `src_file(d)` continues to identify the immutable upstream file;
- `src_span(d)` should be the `start-end` byte range of the complete original `AOHeader` outer element;
- `srcxml(d)` should be the exact original bytes of that range decoded as the existing UTF-8/surrogateescape string representation.

This deliberately excludes XML declarations / stylesheet processing instructions before `<AOxml>` and excludes `<body>`: provenance is attached to the graph object it describes, not to the whole file.

## Multi-line TF values are supported

A complete header is multi-line. Text-Fabric's documented TF file format permits arbitrary string values and requires backslash, tab and newline to be escaped. Text-Fabric's own helpers serialize `\\`, `\t` and `\n` and reverse those escapes on load. Therefore a multi-line `document.srcxml` value does not require a separate encoding scheme; the normal TF writer/loader contract is the encoding layer.

Reference: https://annotation.github.io/text-fabric/tf/about/fileformats.html

A permanent regression still needs to round-trip a representative multi-line header through the actual pinned Text-Fabric writer/loader before implementation is accepted.

## Repair-coordinate contract

The converter parses **repaired in-memory bytes** but `src_file` names **original immutable bytes**. A correct document span therefore cannot simply copy the repaired `AOHeader` coordinates.

The existing `OffsetMap.span_to_original()` is the correct abstraction for the endpoints. The proposed implementation must also retain the original source byte string long enough to assign `srcxml` from the mapped original range rather than from the repaired parse stream.

Research must prove, over the exact converted population:

1. every emitted document has exactly one depth-1 `AOHeader` span in the repaired scanner stream;
2. mapping that span's endpoints through `OffsetMap` yields exactly the raw `<AOHeader>...</AOHeader>` range in the original file;
3. no production case requires an exception/allowlist;
4. whether any repair changes bytes **inside** the header (distinct from merely shifting its offsets because a repair occurred earlier in the file).

If any mapped range is inexact, implementation must stop and classify the source case rather than fabricating provenance.

## Contract A impact

This is not complete merely when the converter emits values. `check_contract_a_graph.py` currently validates graph→source correspondence only for `word` nodes.

The provenance change should extend the independent graph gate so that for every `document` node it:

1. resolves `src_file`;
2. parses `src_span`;
3. slices the original source bytes;
4. requires that slice to be exactly one `AOHeader` outer element;
5. requires decoded slice bytes to equal graph `srcxml` exactly;
6. requires complete document coverage (no silent `document_without_header_span` or missing `srcxml`).

Unlike word reconstruction, document-header verification should need **no known-lossy exception**: the feature is intended to preserve the original header bytes wholesale, irrespective of semantic modelling.

## `docid_raw` decision

`docid_raw` currently duplicates normalized `docid` for 23,881 of 23,884 documents and is wrong for the remaining three trailing-space cases. A byte-exact document header makes the original `<docID>` recoverable together with every other header field.

Keeping `docid_raw` after that would preserve a bespoke core raw feature whose only unique information is already available in the optional provenance module. The research direction is therefore to **retire `docid_raw` in the same schema release that adds document header provenance**, while keeping normalized `docid` unchanged.

This resolves #10 by deliberate replacement rather than by reviving the obsolete standalone 0.2.1 correction PR. The plan must still prove that section addressing, duplicate grouping, upstream links and all other `docid` consumers remain unchanged.

This decision does **not** imply a general purge of every `*_raw` feature. `lang_raw`, `stemclass_raw`, etc. have different semantics and populations and require their own evidence before any removal.

## `mDocID` is a separate semantic question

Making the header recoverable does not automatically promote `mDocID` to queryable join semantics. The 148 values are an independent witness that should be compared against the manuscript join graph under its own research/TDD contract. That follow-up is tracked separately in #63 so provenance does not invent relations it has not established.

## Version / concurrency boundary

Adding `src_span`/`srcxml` values on `document` nodes and removing `docid_raw` changes shipped TF feature bodies/schema. It therefore requires a new immutable TF version.

At research time, PR #55 owns the active 0.4.0 artifact lane for sign-level language. This branch must not generate a competing 0.4.0 artifact. Research, plan and RED tests can proceed independently; production artifact integration must first rebase onto whichever version `main` contains after the active release lane is resolved, then allocate the next unused version.

## Hosted research measurement

`programs/research_header_provenance.py` records:

- converted document count;
- exact mapped original-header span count;
- repaired-source count;
- headers whose offsets shift because of repairs elsewhere;
- headers whose own bytes actually change under repair;
- total header payload bytes;
- newline/tab/backslash populations relevant to TF escaping;
- the existing `docid_raw != docid` population;
- parse/exclusion counts.

Exact numbers are filled from the clean hosted run; they are evidence, not constants to guess locally.

## Research acceptance

Research is complete when the hosted analyser proves exact original-header span coverage for every emitted document or names every exception; the TF serialization contract for full multi-line headers is established; Contract-A verification and version/concurrency implications are explicit; `docid_raw` has a reasoned keep/retire decision; and semantic `mDocID` modelling is kept out of provenance scope.
