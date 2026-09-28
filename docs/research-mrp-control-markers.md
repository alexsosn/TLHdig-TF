# Research: TLHdig/HFR morphology control markers (#92)

## Scope

This note records the research gate for issue #92 against pinned TLHdig 0.3 and the
current TF 0.4.0 artifact. It concerns only leading control syntax inside the first
field of source `mrpN` values. It does not reinterpret `mrp0sel`, broad punctuation,
layout-only morphology (#105), or nested-word morphology (#109).

## Authoritative upstream evidence

HFR documents a three-stage annotation pipeline: automatic candidate generation,
manual pre-validation, and later manual validation. The public annotation manual gives
raw XML examples in which `①` precedes the actual lemma inside an `mrpN` field, e.g.
the example for `petanzi` contains `mrp1='① ped=a- ...'` and
`mrp2='① ped=ae- ...'`. In the same manual, the linguistic stem/lemma is the table
field consumed by the automatic annotator; the leading symbol is not described as part
of the Hittite lexical form.

Sources:

- https://www.hethport.uni-wuerzburg.de/HFR/annotation.php
- https://www.hethport.uni-wuerzburg.de/HFR/material/Handreichung_Annotation.pdf
  (section 4.1, the `petanzi` XML example)
- https://www.hethport.uni-wuerzburg.de/HFR/tools.php

The public documentation does **not** define a reliable linguistic meaning for each
individual sub-glyph in all observed compound runs. We therefore must not invent one.
For TF the safe semantics are: the complete observed run is source annotation-generator
/control metadata, retained verbatim as an opaque value, while the following text is
the lexical first field.

## Corpus census

The research scripts deliberately use two detectors:

1. a broad discovery detector that surfaces any non-ordinary leading symbol;
2. a narrow control grammar that accepts only source-observed control families.

The source contains **1,631,440** `mrpN` candidates. The narrow grammar identifies
**542,680** candidates on **231,158** words with an annotation-control prefix.

Exactly 21 source-observed control families occur:

`①`, `②Ⓐ`, `ⓐⒸ`, `⓶ⓑⒸ`, `⓷Ⓐ`, `②Ⓑ`, `②ⓐⒸ`,
`②ⓐⒸⓢⓣ`, `⓶Ⓒⓐ`, `⓶`, `⓷`, `⓷Ⓑ`, `②Ⓒⓐ`, `⓶ⓐⒸ`,
`⓷ⓐⒸ`, `②ⓑⒸ`, `②ⓐⒸⓐ`, `⓶Ⓒⓑ`, `ⓢⓣ`, `②Ⓒⓑ`, `Ⓑ`.

The common families occur in selected, unselected, and no-numeric-selector candidates.
That distribution is evidence that these runs are not equivalent to `mrp0sel` state.

Normal syntax is:

```
CONTROL_RUN + whitespace + lexical first field
```

or a control-only first field. Six represented source records omit the whitespace after
a lone `⓷`; they have five distinct lexical remainders:

- `kinun`
- `KÙ.BABBAR` (two records)
- `kattan`
- `maniaḫḫ=eššar`
- `lukkatta`

Only these measured glued spellings are accepted. A future glued `⓷...` form is not
silently generalized.

## Structural accounting

Since #131, readable words before the first `<lb>` are represented as document-owned
word/sign nodes. The #92 accounting therefore classifies every non-nested top-level
source word by the same sign-producing criterion regardless of line position.

The source control population partitions as:

- 542,678 represented analysis candidates;
- 2 layout-only candidates (#105);
- 0 nested candidates.

The seven readable pre-line candidates added by #131 carry no broad/control prefix; they
belong to the represented candidate population and explain the temporary +7 research
guard seen before the classifier was refreshed.

## Lexical identity impact

The current shipped artifact has **28,282** `lex` nodes. Control-prefixed analyses
touch **14,227** of them.

If only the narrow, evidence-backed control grammar is removed from lemma identity,
the projected lexical inventory is **15,853** `(lemma, gloss)` identities: a delta of
**-12,429**. There are **6,776** collision groups where several current marker-contaminated
keys collapse to the same lexical identity. Typical examples include `apa-` “er”,
`LUGAL` “König”, `ka-` “dieser”, and `kinun` “jetzt”.

These are intended merges: the marker varies while the lexical remainder and gloss are
the same. Candidate analysis nodes remain distinct.

## What is not a control marker

The broad detector also finds prefixes such as `½`, `½-`, `=`, `?`, `[`, and
`°`. They are not covered by the control evidence and must remain untouched. In
particular, `½` is lexical content in numeral analyses.

The production grammar must therefore use the exact 21-family allowlist, not Unicode
category stripping and not the broad detector.

## Unknown/future syntax

Unknown control-like Unicode runs must fail closed. The guard covers both Unicode names
containing `CIRCLED` and parenthesized Latin-letter glyphs, because the observed
alphabet contains both forms.

For an unknown run the parser must:

- preserve the exact raw `mrpN` value;
- mark the analysis parse as failed/unsupported;
- not expose the control-contaminated first field as a lexical lemma;
- therefore not create a lexeme identity from it.

This makes a future upstream marker addition visible to CI instead of silently expanding
the normalization grammar.

## Research decision

Production may now normalize only the exact observed control grammar.

The complete source run should be retained verbatim on the analysis node as
`mrp_control`. Its sub-glyphs remain intentionally opaque until upstream documentation
defines them. The normalized `lemma` and `lexeme` identity use only the lexical
remainder. Existing `raw` recovery remains mandatory for every normalized analysis.
