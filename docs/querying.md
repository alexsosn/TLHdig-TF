# Querying the current graph

<!-- tf-features: sym after trans lemma gloss morph pos analyses lexeme selected cu_sign cu_aligned project docid collabel lnno src_file type width joined joinLeft joinRight witness -->

These examples show graph-navigation patterns against the committed current artifact. Clean acquisition for a new external consumer is owned separately by #47; repository CI can load the committed artifact directly.

## Load selected features

Selective loading avoids the memory cost of loading every feature:

<!-- executable-example: load-selected -->
```python
from tf.fabric import Fabric

TF = Fabric(locations="tf/0.4.0")
api = TF.load(
    "sym after trans lemma gloss morph pos analyses lexeme selected "
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

## Build a lexeme concordance

Find every word whose candidate analysis has a given lemma, then recover its manuscript, line address and surrounding text. The graph path is `lex ← lexeme — analysis ← analyses — word`. A `lex` node currently groups analyses by `(lemma, gloss)`, so searching by lemma must consider **all** matching `lex` nodes. Its `oslots` contains only an anchor at the first attestation: `L.d(lex, otype="word")` is **not** a concordance lookup.

The optional `selected_only` mode retains a word only when the source's `selected` edge points to a matching analysis; it must not be interpreted as an automatic disambiguation. Some words select more than one analysis, and the lack of a selected edge is not proof that a candidate is wrong.

<!-- executable-example: lexeme-concordance -->
```python
def concordance(lemma, *, selected_only=False):
    matched_words = set()
    for lex in F.otype.s("lex"):
        if F.lemma.v(lex) != lemma:
            continue
        for analysis in E.lexeme.t(lex):
            for word in E.analyses.t(analysis):
                if not selected_only or analysis in E.selected.f(word):
                    matched_words.add(word)

    rows = []
    for word in sorted(matched_words):
        documents = L.u(word, otype="document")
        if not documents:
            continue
        document = documents[0]
        for line_node in L.u(word, otype="line"):
            columns = L.u(line_node, otype="column")
            rows.append({
                "word": word,  # node number is local to this TF build
                "line_node": line_node,
                "docid": F.docid.v(document),
                "src_file": F.src_file.v(document),
                "column": F.collabel.v(columns[0]) if columns else None,
                "line": F.lnno.v(line_node),
                "form": F.trans.v(word),
                "context": T.text(line_node, fmt="text-orig-plain"),
            })
    return rows

# Replace this example lemma with one from your corpus's lexeme inventory.
target_lemma = "wed=a-"
candidate_rows = concordance(target_lemma)
selected_rows = concordance(target_lemma, selected_only=True)
print(target_lemma, "candidate:", len(candidate_rows), "selected:", len(selected_rows))
for row in candidate_rows[:5]:
    print(row["docid"], row["column"], row["line"], row["form"], row["context"])
```

Word nodes are deduplicated across candidate analyses. A word spanning multiple lines produces one row per line, so the displayed row count is not necessarily the number of unique word attestations; count `{row["word"] for row in candidate_rows}` for that. Keep `src_file` in exported results because `docid` is not globally unique, and allow missing line addresses rather than fabricating them. This is a line-context concordance, not a fully aligned keyword-in-context formatter; a damage-aware study should also inspect the word's sign slots and editorial features. See [Morphology](morphology.md), [Identifiers](identifiers.md) and the [research applications](applications-deep-research-report.md) for related questions.

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
