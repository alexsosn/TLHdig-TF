# Research: byte-exact document-header provenance

Issues: #57, #58, #10

## Question

The converter currently makes the body recoverable through the optional provenance module but leaves the entire `AOHeader` outside Contract A. This research asks whether the existing `src_span` / `srcxml` mechanism can be extended to `document` nodes without inventing a parallel provenance model, and whether doing so makes the bespoke core feature `docid_raw` obsolete.

This phase is read-only with respect to TF artifacts. `programs/research_header_provenance.py` measures the pinned corpus in a clean hosted checkout. No converter/schema/version change is made before a separate plan and RED gate.

## Current architecture

`programs/tlhdig/source.py` scans the parsed source byte stream and reports outer/inner byte spans for every XML element. Repairs are applied in memory; `repair.OffsetMap` translates repaired coordinates back to the original on-disk file named by `src_file`.

The optional provenance module already contains exactly the two features needed here:

- `src_span` — original-file byte range;
- `srcxml` — verbatim source fragment retained on graph nodes.

`build.py` moves those feature files wholesale into `tf-provenance/<version>`. Adding values on `document` therefore needs neither a parallel module nor new provenance feature names.

The blind spot is `_document()`: it creates normalized/queryable document metadata, but never assigns either provenance feature. It separately consumes `AOHeader/docID` and only recognized events under `AOHeader/meta//*`. Header content not explicitly modelled is therefore unrecoverable from the graph.

Contract B now exposes that loss, including 148 `mDocID` values, 75 `merged` wrappers, 149 `doc` wrappers, 1,738 ordinary `annot@data` attributes, malformed `mDodID` / `ann`, and three direct `AOHeader/annot` events outside the converter's `meta//*` path.

## Provenance unit

The natural unit is the **outer byte range of the single direct `<AOHeader>...</AOHeader>` element** associated with each emitted document.

For document node `d`:

- `src_file(d)` continues to identify the immutable upstream XML file;
- `src_span(d)` is the `start-end` byte range of the complete original `AOHeader` outer element;
- `srcxml(d)` is exactly those original bytes decoded with the existing UTF-8/surrogateescape representation.

This excludes XML declarations / stylesheet processing instructions and excludes `<body>`: the provenance value describes the document-header source object, not the whole file.

## Hosted corpus measurement

Clean hosted workflow run **34227007271** executed `programs/research_header_provenance.py` against the exact branch merge with current `main` and succeeded without an allowlist:

| measurement | count |
|---|---:|
| emitted / converted documents | **23,884** |
| exact original `AOHeader` spans | **23,884** |
| repaired source files encountered | 173 |
| header offsets shifted by repairs | **0** |
| header bytes changed by repairs | **0** |
| original header payload | **8,852,903 bytes** |
| headers containing newline | 12 |
| headers containing tab | 8 |
| headers containing backslash | 0 |
| source `docID` differing from normalized `docid` | **3** |
| missing `docID` | 0 |
| empty `docID` | 0 |
| unparseable after configured repairs | 52 |
| parseable-but-no-text documents | 0 |
| patch failures | 0 |

The decisive result is **23,884 / 23,884 exact original-header spans**. No repaired production file mutates the header or even moves its endpoints, so the implementation does not need a current-corpus exception list. It must nevertheless keep using `OffsetMap`: that is the generic coordinate contract and remains necessary if future repair placement changes.

The 52 still-unparseable source files are not emitted document nodes and therefore are outside this graph feature's population; their salvage/exclusion semantics remain owned by the malformed-source work.

## Multi-line Text-Fabric values

A complete header can contain tabs/newlines. Text-Fabric's file format supports arbitrary string values by escaping backslash, tab and newline on serialization and reversing them on load. The corpus confirms the case is small but real (12 newline-bearing, 8 tab-bearing headers), so this cannot be dismissed as theoretical.

The implementation plan must include an actual pinned Text-Fabric 13.1 writer/loader regression using a representative multi-line/tab-bearing header. No bespoke base64 or alternate feature encoding is justified.

## Repair-coordinate contract

The converter parses repaired in-memory bytes but `src_file` names original immutable bytes. Production therefore must not set document provenance from repaired coordinates/bytes directly.

The implementation should:

1. retain the original byte string before repair;
2. identify the unique depth-1 `AOHeader` span in the repaired scanner stream;
3. map its endpoints through `OffsetMap.span_to_original()` when a map exists;
4. validate the mapped slice is exactly one outer `AOHeader` in the original bytes;
5. assign both `src_span` and `srcxml` from that original slice;
6. fail rather than fabricate provenance if this invariant ever stops holding.

The hosted census proves this policy has zero current exceptions.

## Contract A impact

Emitting values is insufficient. `check_contract_a_graph.py` currently verifies graph→source correspondence only for `word` nodes. The existing release gate should be widened, not supplemented with a weaker ad-hoc check.

For every `document` node it must independently:

1. resolve `src_file`;
2. require and parse `src_span`;
3. slice original source bytes;
4. require the slice to be exactly one `AOHeader` outer element;
5. require decoded slice bytes to equal graph `srcxml` exactly;
6. require complete document coverage.

Unlike word reconstruction, document header provenance should have **no known-lossy exception**: this feature preserves the original header wholesale, independently of whether individual fields have semantic graph models.

## `docid_raw` decision

`docid_raw` duplicates normalized `docid` in 23,881 of 23,884 documents and is wrong for the remaining three trailing-space cases. Whole-header provenance recovers the original `<docID>` bytes together with all other header data.

Keeping `docid_raw` after this would leave a bespoke core raw feature whose only unique information is already available in the optional provenance module. Research therefore decides to **retire `docid_raw` in the same schema release that adds document header provenance**, while keeping normalized `docid` behavior unchanged.

This resolves #10 by deliberate replacement rather than reviving the obsolete standalone 0.2.1 correction branch. The implementation still has to prove that document grouping, section addressing, upstream links and every other consumer of normalized `docid` remain unchanged.

This decision is specific to `docid_raw`; it is not evidence for removing `lang_raw`, `stemclass_raw`, or other raw-valued features with different semantics.

## `mDocID` is a separate semantic question

Making the bytes recoverable does not automatically make `mDocID` a queryable join relation. The 148 values are an independent source witness for composite membership and should be compared against the manuscript join graph under their own research/TDD contract. That work is filed separately as #63 so provenance does not invent unsupported semantics.

## Version and concurrency boundary

Adding `src_span` / `srcxml` values on document nodes and removing a shipped core feature changes artifact bodies/schema, so it requires a new immutable TF version.

At research time PR #55 owns the active **0.4.0** artifact lane for sign-level language. This branch must not generate a competing 0.4.0 artifact. Research, plan and RED tests can proceed independently. Before production/version integration, rebase onto the then-current `main` and allocate the next unused TF version (expected to be 0.5.0 if 0.4.0 lands first; never hard-code that assumption before rebase).

## Research acceptance

Research is complete:

- exact original header provenance is feasible for all **23,884** emitted documents with zero exceptions;
- repair-coordinate behavior is measured and has zero current header mutations;
- Text-Fabric escaping supports the observed multi-line/tab payload class, with a real writer/loader regression required in TDD;
- Contract A extension is explicit;
- `docid_raw` has a reasoned retire decision while normalized `docid` remains stable;
- semantic `mDocID` modelling is separated into #63;
- artifact/version work is serialized behind the active 0.4.0 lane.
