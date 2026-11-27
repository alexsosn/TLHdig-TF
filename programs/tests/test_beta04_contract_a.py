"""Independent source-span controls for the eight measured Contract A discrepancies."""
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_contract_a_graph import reviewed_inner
from tlhdig.paths import CORPUS

GAP = "CTH 570_XML_HDivT/KBo 58.79+.xml"
CASES = (
    (26188, 26294, '<sGr>SIG₅</sGr><gap c="-ru ni ši ta ke ze"/>'),
    (26295, 26363, '<sGr>GAR</sGr><gap c="-ri"/>'),
    (29562, 29645, '<sGr>SUM</sGr><gap c="-an ¬¬¬ "/>'),
    (29750, 29830, '<sGr>EGIR</sGr><gap c="-an-da-ma"/>'),
    (67136, 67261, '<d>D</d><sGr>UTU</sGr><aGr>-ŠI</aGr><gap c="-ia ka-a a-ni-ia-an-zi"/>'),
    (67388, 67491, '<d>D</d><sGr>UTU</sGr><aGr>-ŠI</aGr><gap c="-ia-kán"/>'),
)


@pytest.mark.parametrize("a,b,expected", CASES)
def test_missing_closing_tag_does_not_make_attested_reading_empty(a,b,expected):
    raw = (CORPUS/GAP).read_bytes()
    assert reviewed_inner(GAP, raw, a, b) == expected.encode()
    assert reviewed_inner(GAP, raw, a+1, b) is None
    assert reviewed_inner(GAP, raw, a, b-1) is None
    with pytest.raises(ValueError, match="SHA-256"):
        reviewed_inner(GAP, raw+b" ", a, b)


@pytest.mark.parametrize("rel,a,b,old,new", [
    ("CTH 581_XML_HDivT/KBo 18.142.xml", 8076, 8477,
     b"DA.BI</sGr>-&lt;/SP_f_AO_3a_SumGRAM&gt;",
     b"DA.BI&lt;/sGr>-&lt;/SP_f_AO_3a_SumGRAM&gt;"),
    ("CTH 585_XML_HDivT/KUB 31.54.xml", 1143, 1253,
     b'c="<laes_in/>m<laes_fin/>"', b'c="&lt;laes_in/&gt;m&lt;laes_fin/&gt;"'),
])
def test_reviewed_attribute_escape_is_exact_and_reversible(rel,a,b,old,new):
    raw = (CORPUS/rel).read_bytes()
    chunk = raw[a:b]
    inner = chunk[chunk.index(b">")+1:chunk.rindex(b"</w>")]
    assert inner.count(old) == 1
    expected = inner.replace(old,new,1)
    assert reviewed_inner(rel, raw, a, b) == expected
    assert expected.replace(new,old,1) == inner
    assert reviewed_inner(rel, raw, a+1, b) is None
    with pytest.raises(ValueError, match="SHA-256"):
        reviewed_inner(rel, raw+b" ", a, b)


def test_other_source_or_unreviewed_coordinate_never_receives_repair():
    raw = (CORPUS/GAP).read_bytes()
    assert reviewed_inner("another.xml",raw,26188,26294) is None
    assert reviewed_inner(GAP,raw,0,20) is None
