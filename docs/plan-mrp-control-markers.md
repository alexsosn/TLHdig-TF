# Plan: separate morphology control markers from lexical lemmas (#92)

Research source: [research-mrp-control-markers.md](research-mrp-control-markers.md).

## Goal

Make the current TF artifact expose lexical lemmas without TLHdig/HFR annotation-control
syntax while retaining the exact source control run and raw `mrpN` record.

No historical TF version is allocated. Under #115 this is a replacement of the one
current pre-alpha 0.4.0 artifact.

## Production model

### Parser

Extend `programs/tlhdig/morph.py` with the researched exact control grammar:

- exact 21-family allowlist;
- ordinary boundary: control run is the complete first field or is followed by
  whitespace;
- only the five measured glued `⓷` lexical remainders are accepted;
- broad non-control punctuation is untouched;
- a new/unknown control-like run fails closed.

Add `Analysis.control: str`.

For a known control run:

1. preserve the original `Analysis.raw`;
2. set `Analysis.control` to the complete run;
3. replace the parsed base lemma with the lexical remainder;
4. set `normalised=True` so raw recovery is retained.

For an unknown control-like run:

1. keep `raw`;
2. set `ok=False` with an explicit note;
3. do not expose the contaminated first field as `base.lemma`;
4. consequently do not create a `lex` identity from it.

### TF schema/converter

Add sparse analysis feature `mrp_control` with a canonical description in
`programs/tlhdig/featuremeta.py`.

`convert.py` emits `mrp_control` when non-empty. Existing lexeme accumulation then
automatically uses the normalized `a.base.lemma`; no special merge algorithm is added.
Analysis-node multiplicity and word→analysis edges remain unchanged.

### Documentation

Update morphology/data-model documentation to state:

- `lemma` is lexical content after removal of the researched control run;
- `mrp_control` is opaque upstream annotation-generator/control metadata;
- `raw` is the lossless source record for normalized cases;
- unknown future control syntax is a parse failure, not an inferred extension.

Regenerate the current feature reference from the rebuilt artifact.

## TDD gate

RED must be committed before production implementation.

### Parser RED

Tests must cover:

- representative `①`, `②Ⓐ`, `ⓐⒸ`, `⓶ⓑⒸ`, `⓷Ⓐ`;
- all 21 exact family strings parametrically;
- marker-free lemma unchanged;
- `½`, `½-`, `=` and other broad non-control prefixes unchanged;
- control-only first field;
- each measured glued `⓷` remainder;
- a new glued `⓷foo` rejected;
- an unknown circled glyph rejected;
- an unknown parenthesized Latin glyph rejected;
- raw recovery and `normalised=True`.

### Converter/graph RED

A synthetic AOxml build must prove:

- analysis `lemma` contains the lexical remainder;
- `mrp_control` contains the exact source run;
- `raw` contains the exact source value;
- two analyses differing only by control run link to one `lex` node for the same
  `(lemma, gloss)`;
- analysis nodes themselves remain distinct;
- unknown control-like syntax creates no contaminated lexeme identity.

### Corpus/current-artifact gates

After GREEN:

1. run unit tests and the ordinary morphology/source-conservation gates;
2. rebuild current TF 0.4.0 and provenance with `programs/build.py`;
3. run `programs/validate_current.py`;
4. regenerate feature docs;
5. assert the post-build control census:
   - known control values are present in `mrp_control`;
   - no known control run remains at the start of `analysis.lemma`;
   - source/control counts balance after excluding the two #105 layout-only candidates;
   - lexical-node count and merge delta match the independently predicted research
     census, unless a separately explained concurrent change alters the baseline;
6. commit the replacement current artifact and manifest.

## Independent adversarial review

Review must be logically independent of implementation and challenge at least:

- over-stripping of lexical punctuation/numerals;
- under-stripping of any of the 21 families;
- future unknown glyph/combo handling;
- glued-`⓷` overgeneralization;
- raw/source round-trip loss;
- accidental collapse of analysis nodes rather than only lex identities;
- selector semantics (`mrp0sel`) remaining unchanged;
- current-artifact/manifest consistency;
- documentation claiming meanings for individual glyphs that upstream does not define.

Only after those checks pass should PR #102 be marked ready and merged.
