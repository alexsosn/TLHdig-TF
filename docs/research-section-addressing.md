# Research: exhaustive section addressing for unnumbered lines (#15)

## Scope and method

This research follows the converter's actual input path rather than a raw-text regex:
`programs/research_section_addressing.py` applies the checked repair manifest, requires a
strict XML parse, inventories every `<lb>` without a non-empty `lnr`, then reconciles the
result to the shipped Text-Fabric graph by `(src_file, srcln)`. The full per-case census is
materialized in `reports/section-addressing-research.json`; this document records the
conclusions that govern the implementation.

No source file is edited by this ticket and no scholarly line number is inferred unless
it is forced by the source evidence.

## Census

The repaired, strictly parseable source population contains 412,796 `<lb>` elements.
Among them, 41 lack a usable `lnr` across 36 files:

- 27 have no `lnr` attribute;
- 14 have `lnr=""`;
- 41/41 fail the conservative local inference rule.

The shipped TF 0.2.0 graph contains 39 corresponding unaddressed `line` nodes. There are
no TF-only cases. The two repaired-source candidates that do not become shipped line
nodes are terminal `<lb>` elements:

1. `CTH 134_XML_SVH/KBo 53.250+.xml`, repaired-source `<lb>` index 33;
2. `CTH 448_XML_TLH/DAAM 3.149+.xml`, repaired-source `<lb>` index 30.

Thus the known shipped defect count of 39 is correct even though the repaired source
contains 41 candidate `<lb>` elements. The checked report records every matched and
source-only row, including raw public `<lb>` attributes, neighboring `lnr` values, source
path, `txtid`, TF line node, source-line index, column node and `collabel`.

## Classification of the 39 shipped cases

For converter policy, all 39 are classified **truly unnumbered**:

- `source-label recoverable`: 0;
- `deterministically inferable`: 0;
- `truly unnumbered`: 39.

Here `truly unnumbered` means only that the pinned TLHdig source supplies no usable label
and the label cannot be recovered deterministically from adjacent source labels. It does
not claim that no external edition could ever supply an editorial line number.

The inference rule intentionally requires both neighboring labels to parse as simple line
numbers in the same column/prime regime, with a numeric gap exactly equal to the number of
missing rows. None of the 41 repaired-source candidates satisfies those conditions.

### Contentful counterexample to sequence inference

`CTH 570_XML_HDivT/KUB 50.123.xml` contains genuine contentful unnumbered lines
interleaved with numbered lines:

- `Rs. 2′`
- unnumbered content containing `3 ... SIG₅-in ...`
- `Rs. 3′`
- unnumbered content
- `Rs. 4′`
- unnumbered content
- `Rs. 5′`
- unnumbered content containing `10 TE-RA-A-NU SIG₅`
- `Rs. 6′`

Assigning the sequence positions `3′`, `4′`, etc. to those unnumbered rows would collide
with real source labels and would be philologically false. Sequence position therefore
cannot be used as a displayed or source-like line number.

## Column context and collision risk

Every one of the 39 shipped unaddressed lines currently belongs to a column whose
`collabel` is `"-"`, while its `lnno` is empty. The defect is consequently not limited to
the third section level: the affected graph also relies on an anonymous level-2 label.

A synthetic address placed directly into `lnno` would still overload source metadata and
could collide with source-provided strings. A synthetic address placed into a separate
section feature can use a reserved namespace and can be checked globally for collisions
before the artifact is written.

The same principle applies to anonymous/duplicate column headings: if a column requires a
synthetic section heading, that heading belongs in a separate section-address feature,
not in `collabel`.

## Online TLHdig evidence

A research-only probe attempted representative online lookups for `KUB 50.123`,
`DAAM 5.61` and `DAAM 5.77`. The tested URL form returned the same 1,737-byte generic
page for all three queries: document titles and target transliteration strings were
absent. This does **not** establish that the online application has no independent line
labels. It establishes only that the probed endpoint is not a usable document-rendering
endpoint.

Accordingly, no label is recovered from the online application and no negative claim is
made about labels that might be exposed through another endpoint.

## Text-Fabric behavior and precedent

Text-Fabric section addressing is driven by the configured `sectionTypes` and
`sectionFeatures`. `sectionFromNode()` returns the configured feature values, including
missing values, and `nodeFromSection()` resolves through maps keyed by those feature
values. Text-Fabric does not invent a missing section label for the corpus.

The public `Nino-cunei/oldbabylonian` TF dataset uses
`@sectionTypes=document,face,line` with `@sectionFeatures=pnumber,face,lnno`. Its `lnno`
metadata explicitly states that the value may be nonnumeric (`$` or `#`, with primes),
and shipped values include forms such as `$a`. This demonstrates that TF section values
need not be numeric scholarly line numbers. It does not justify copying the ATF `$a`
semantics into TLHdig; it supports using an explicit nonnumeric internal address where a
corpus genuinely lacks a source number.

## Preserve absence as data

The source distinction remains research-relevant:

- absent `lnr` and empty `lnr` are different raw-source states;
- existing `lnr`, `lnno` and `collabel` features already expose the scholarly/source
  representation;
- overwriting any of them with a generated value would erase or falsify that state.

Therefore the section-address mechanism must be separate from the source-facing
features. Synthetic values must be recognizable as synthetic and must not be presented
as source line numbers.

## Interaction with duplicate document IDs

Issue #16 owns the 141 duplicated `docid` values and any redesign of level-1 document
identity. #15 must not solve that problem indirectly. Its exhaustive validator must
measure and report pre-existing level-1 ambiguity separately from line/column-address
completeness, while preventing #15 from introducing new level-2/3 collisions.

After #10 lands, #15 will build on the next immutable TF artifact version. It will not
rewrite 0.2.0 or the 0.2.1 artifact reserved by #10.

## Research conclusion

The evidence rules out source-like inferred numbering for the 39 lines. The smallest
source-faithful design is to preserve `lnr`, `lnno` and `collabel` unchanged and configure
Text-Fabric sections with separate deterministic address features for column/line
headings. Existing valid headings should be mirrored value-for-value in those address
features; only missing or colliding section headings should receive an explicitly
synthetic value from a reserved namespace. Generation must be deterministic and guarded
by exhaustive uniqueness/round-trip checks.
