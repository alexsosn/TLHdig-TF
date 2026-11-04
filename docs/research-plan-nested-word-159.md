# #159 — Research and TDD plan: repair erroneous cross-line source-word nesting

## Source and independent evidence (2026-10-28)

Pinned immutable file: `corpus/TLHdig-0.3/CTH 479_XML_BESRIT/KBo 41.49+.xml`.
Its source has 288 literal `<w>` opens, 274 explicit closes and 84 literal
`<lb>` elements. An independent tag-stream push/pop audit identifies exactly
14 outstanding word starts; **every one starts** `<w><del_in/><del_fin/>`,
with no readable sign before its subsequent line break. Thirteen are followed
only by whitespace before the next `<lb>`; the fourteenth has `gap` and
`note` elements before the line break. Only one `<lb>` occurs at depth zero,
while 83 occur inside an open `<w>` (maximum line depth 14, peak word depth 15).

The existing immutable-source patch in `programs/patches.yaml` appends fourteen
`</w>` tags at `</text>`, making the source parseable but preserving the
erroneous nested ancestors. `tlhdig.convert._document` excludes a child
`<w>` when it has any `<w>` ancestor to prevent double-tokenising
genuinely nested words; therefore source-attested
`<w>pé-e-da-an-zi</w>` on `{€1+2+3} Rs. III 2/2′` is not queryable.

### Hypothesis and limits

For this record only, source-marked *contentless* words of exactly the
`<w><del_in/><del_fin/>` form that remain unmatched and cross their next
`<lb>` can be closed immediately before that line without claiming a new
reading. This is distinct from #158's valid unwrapped mixed content, and from
legitimate nested `<w>` on one line. In particular, do **not** mechanically
close every `<w>` at every `<lb>`: a readable source token could legitimately
span a line. The fourteenth case includes gap and note events; review its exact
node/event ordering and the source- and output-marker ledgers separately.

The repair must preserve the pinned original XML; any inferred closing
boundaries must be declared and hash-pinned in the repair manifest, with
an `OffsetMap` translating repaired coordinates back to the original source.
The existing fourteen end-of-text closing tags must be adjusted, not left
in addition to earlier closes.

### Gates

1. **Research** (this file): verify specific unmatched starts by source
   coordinate, source line and direct `<w>` child; inspect existing patch
   exactly. Compare other records before genericizing.
2. **Plan**: scope to this one file; use a reviewable hash-pinned change in
   `programs/patches.yaml`, not a generic XML autocorrector. Show before/after
   word ownership and marker-note provenance on actual source.
3. **RED TDD**: add an actual single-file Text-Fabric integration fixture
   expecting `pé, e, da, an, zi` in the Rs III 2/2′ line, while the current
   converter demonstrably fails. Source and negative controls separately
   assert immutable count, real crossing parents, genuinely nested words and
   order. Confirm the test is RED on hosted Python 3.13.
4. **Implementation**: adjust only the reviewed repair sites. Prove the
   `OffsetMap` correctly maps unchanged source bytes and flags synthetic
   boundaries, and source marker/note counts remain equal to graph output.
5. **Tests**: source round trip; first and later recovered lines; fully
   populated file's ordered sign sequence; 84 line ownership positions;
   genuine nested word negative control, damage and note conservation;
   source/graph word census; external sign-reference checks.
6. **Full integration**: wait for #160 release artifact; then rebuild
   current TF and provenance once with both corrections; compare node IDs,
   alignment, morphology, and original glyph/provenance controls. Complete
   `validate_current` + manifest CI before merging.
7. **Independent adversarial review**: challenge every proposed earlier
   closing position against original XML and raw bytes, reject speculative
   lexical structure or extra editorial signs, test genuine cross-line words.
8. **E2E**: at release completion, perform a clean-user TF acquisition,
   `A.pretty()`/text smoke and representative newly recovered line query.

### Explicitly excluded

No reading inferred from `lb@cu` and no attempt to recover the remaining
13,022 no-slot lines by asserting they all share this defect. Do not
mutate the source repository, introduce XML blobs or treat the one-file
repair as proof for every malformed nested word.
