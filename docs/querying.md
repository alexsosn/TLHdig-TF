# Querying the current graph

<!-- tf-features: sym after lemma gloss morph pos analyses cu_sign cu_aligned project docid collabel lnno src_file type width joined joinLeft joinRight witness -->

These examples show graph-navigation patterns against the committed current artifact. Clean acquisition for a new external consumer is owned separately by #47; repository CI can load the committed artifact directly.

## Load selected features

Selective loading avoids the memory cost of loading every feature:

<!-- executable-example: load-selected -->
```python
from tf.fabric import Fabric

TF = Fabric(locations="tf/0.4.0")
api = TF.load(
    "sym after lemma gloss morph pos analyses "
    "cu_sign cu_aligned project docid collabel lnno src_file type width "
    "joined joinLeft joinRight witness"
)
F, E, L, S, T = api.F, api.E, api.L, api.S, api.T
```

Record the TF/repository version in reproducible work; raw node numbers may change after regeneration.

## Resolve a section and read text

<!-- executable-example: section-text -->
```python
line = T.nodeFromSection(("KUB 21.8", "Vs. II", "1′"))
if line is not None:
    print(T.text(line, fmt="text-orig-plain"))
```

A successful example does not prove every line has an address. See [Identifiers and navigation](identifiers.md) for current missing/ambiguous cases.

## Keep competing morphology candidates

<!-- executable-example: morphology-candidates -->
```python
candidates = ()
for word in F.otype.s("word"):
    candidates = E.analyses.f(word)
    if len(candidates) > 1:
        for a in candidates:
            print(F.lemma.v(a), F.morph.v(a), F.gloss.v(a))
        break
```

Do not silently replace candidate multiplicity with a preferred analysis unless the source contract for that selection is established for the question being asked.

## Query editorial extents

<!-- executable-example: editorial-extents -->
```python
hits = S.search("""
cluster type=del width>1
""")
```

This asks for positive-width deletion/lacuna clusters. Point-like editorial statements have a different interpretation; see [Editorial markup](editorial.md).

## Inspect cuneiform only where aligned

<!-- executable-example: cuneiform-alignment -->
```python
pairs = []
for line_node in F.otype.s("line"):
    if not F.cu_aligned.v(line_node):
        continue
    signs = L.d(line_node, otype="sign")
    pairs = [(F.sym.v(s), F.cu_sign.v(s)) for s in signs if F.cu_sign.v(s)]
    if pairs:
        print(pairs[:12])
        break
```

For a real study, select accepted alignment/status classes explicitly rather than treating every non-empty `cu_sign` as equivalent evidence.

## Retain source-record identity in exports

<!-- executable-example: document-identity -->
```python
documents = F.otype.s("document")[:5]
for document in documents:
    print(F.docid.v(document), F.src_file.v(document))
```

`docid` is useful scholarly metadata but is not globally unique in the current corpus. `src_file` distinguishes current source records; neither raw TF node numbers nor pre-alpha technical paths should be treated as timeless citation identifiers.

## Manuscript relations

Source-apparatus direction/order and uncertainty matter; do not manufacture reverse or transitive joins that the graph does not assert. A `joinstmt` preserves the source statement, while `joinLeft` and `joinRight` expose resolved apparatus-entry occurrences in source order where recoverable.

<!-- executable-example: manuscript-relations -->
```python
join_examples = []
for stmt in F.otype.s("joinstmt"):
    left = E.joinLeft.f(stmt)
    right = E.joinRight.f(stmt)
    if left or right:
        join_examples.append((stmt, left, right))
        if len(join_examples) == 5:
            break

for stmt, left, right in join_examples:
    print(stmt, left, right)
```

The [data model](data-model.md) describes the relation boundary. Load and inspect `joined` or `witness` as well when the research question needs those specific relations; their generated feature pages define their direction and value semantics.
