#!/usr/bin/env python
from pathlib import Path

path = Path("docs/TF-CONVERSION-PLAN.md")
text = path.read_text(encoding="utf8")
replacements = {
'''tfVersion     = 0.2.0      # this ontology + converter''': '''tfVersion     = 0.3.0      # current manuscript-graph ontology + converter''',
'''tf/0.2.0/        generated features''': '''tf/0.3.0/        generated features''',
'''checked against `tf/0.1.0`.''': '''checked against the current `tf/0.3.0` schema and its release gates.''',
'''| manuscript witnesses | `fragment` nodes + `witness` edges | done — extent is the union of the witness's lines |''': '''| manuscript witnesses | `fragment` nodes + `witness` / `witness_resolution` edges | done — block-scoped; resolved witnesses span their cited lines, otherwise the fragment uses a documented technical anchor |''',
'''| manuscript joins | `joins` edges | **not implemented** — flattened to `document.directjoin` / `indirectjoin` strings |''': '''| manuscript joins | `joinstmt` + `joinLeft` / `joinRight` / `joinDocument`; valued `joined` convenience edge | done in `tf/0.3.0` — every repaired/strict source statement is ledgered; `check_manuscript_joins.py` independently conserves source occurrences and forbids unsupported reverse/transitive edges |''',
'''| lexical layer | `lex` nodes + `lexeme` edges | **not implemented** (KNOWN-ISSUES 2) |''': '''| lexical layer | `lex` nodes + `lexeme` edges | done — occurrence analyses link to shared `(lemma, gloss)` lexical nodes |''',
}
for old, new in replacements.items():
    assert old in text, f"missing expected plan text: {old!r}"
    text = text.replace(old, new, 1)

anchor = '''Where upstream documentation settles a meaning, the derived feature carries it **and**
the raw value.'''
insert = '''`fragment` and `joinstmt` are manuscript-apparatus metadata/relationship overlays, not
independently positioned transliteration units. Under ADR-0001 their fallback `oslots`
are documented technical connectivity anchors only; they must not be interpreted as a
physical sign, textual extent, or invented source content. A fragment with resolved line
witnesses instead spans those cited line slots.

Where upstream documentation settles a meaning, the derived feature carries it **and**
the raw value.'''
assert anchor in text, "preservation-map tail drifted"
text = text.replace(anchor, insert, 1)
path.write_text(text, encoding="utf8")
