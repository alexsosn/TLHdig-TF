"""The source-construct census.

The census compared the graph against itself, so it reported "all invariants hold" while
15,434 `line`, 6,802 `colon` and 3,848 `note` nodes were being deleted as unlinked. This
module is the independent count: what the XML contains, read from the repaired bytes.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import structure

DOC = b"""<?xml version="1.0" encoding="UTF-8"?>
<AOxml xmlns:AO="http://hethiter.net/ns/AO/1.0">
<body><div1 type="transliteration"><text xml:lang="Hit">
<lb lnr="Vs. I 1"/><clb id="1"/><w>pa-it<note n="1" c="x"/></w>
<lb lnr="Vs. I 2"/><w><del_in/></w>
<note n="2" c="outside any word"/>
</text></div1></body></AOxml>
"""


def test_counts_every_structural_element():
    c = structure.count_document(DOC)
    assert c["line"] == 2
    assert c["colon"] == 1
    assert c["note"] == 2      # one inside <w>, one directly under <text>


def test_only_top_level_words_are_counted():
    """A nested <w> is deliberately covered by its parent, so counting it would make
    the gate demand nodes the converter never intends to emit."""
    doc = DOC.replace(b"<w>pa-it<note n=\"1\" c=\"x\"/></w>",
                      b"<w>pa-it<w>nested</w></w>")
    assert structure.count_document(doc)["word"] == 2   # the outer one, plus <w><del_in/></w>


def test_namespaced_and_bare_tags_are_not_double_counted():
    """`{*}tag` already matches the no-namespace case; searching both counted twice and
    reported 825,274 lines against a real 412,637."""
    assert structure.count_document(DOC)["line"] == 2


def test_unparseable_document_is_skipped():
    assert structure.count_document(b"<AOxml><text>") is None


def test_document_without_a_text_element_is_skipped():
    assert structure.count_document(b"<AOxml><body/></AOxml>") is None


def test_graph_counts_read_otype_directly(tmp_path):
    """Reading otype.tf keeps the gate at seconds instead of a 12-minute TF load."""
    d = tmp_path / "tf"
    d.mkdir()
    (d / "otype.tf").write_text(
        "@node\n@valueType=str\n\n1-10\tsign\n11-12\tword\n13\tline\n", encoding="utf8"
    )
    c = structure.graph_counts(d)
    assert c["sign"] == 10 and c["word"] == 2 and c["line"] == 1
