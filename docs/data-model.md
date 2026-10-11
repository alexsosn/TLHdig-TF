# Data model

<!-- tf-node-types: sign analysis word cluster line layout edit paragraph colon column surface lex fragment document docgroup note joinstmt -->

The Text-Fabric slot type is `sign`. Slots preserve textual order and allow editorial spans to begin or end inside words. Other node types cover textual structure, analyses, editorial ranges and manuscript relations.

## Textual structure

The main reading hierarchy is approximately:

```text
sign → word → line → column → surface → document
```

`paragraph` and `colon` provide additional source structure. `layout` nodes retain non-lexical layout material that needs graph presence without pretending it is a readable word.

Text-Fabric containment is slot-based: a node covers the sign slots in its `oslots` extent. Zero-width or technical structures need special care and should not be inferred merely from an empty-looking display.

## Analytical nodes

`analysis` nodes represent source morphological candidates. A word can have several candidates; the `analyses` edge exposes them without collapsing ambiguity. `lex` nodes provide a lexical grouping layer connected from analyses.

Analytical nodes should be queried as annotations over the textual graph. Their node numbers are implementation identities, not stable scholarly citations.

## Editorial nodes

`cluster` nodes represent source editorial/damage spans such as deletion, lacuna, restoration and related constructs. `note` and `edit` nodes preserve other source annotations and editorial-history events where the current model supports them.

See [Editorial markup](editorial.md) for interpretation rules.

## Manuscript and apparatus relations

`fragment` nodes represent source fragment occurrences and `joinstmt` nodes preserve source join statements, including unresolved or uncertain cases. Edges such as `joinLeft`, `joinRight`, `joined`, `witness`, `edition` and related features expose recoverable relations without silently adding reverse or transitive scholarly claims.

`docgroup` groups records associated with the same manuscript identity while preserving separate `document` records. This matters because source `docid` is not globally unique.

## Sections and navigation

The configured section levels are document / column / line. A typical address therefore looks like:

```text
KUB 21.8 / Vs. II / 1′
```

Not every current line has a complete section address, and duplicate `docid` values can make an apparently complete address ambiguous. See [Identifiers and navigation](identifiers.md).

## Features

The complete shipped feature list is generated from the current artifact rather than maintained here. Use the [feature reference](features/0_home.md) for node/edge feature definitions and [`../reports/census.md`](../reports/census.md) for the current graph inventory.
