"""Primary-source RED integration gate for #158's genuinely unwrapped AOxml.

This pilot deliberately builds only the real immutable KBo 31.40 record into
a throwaway Text-Fabric dataset; no release or shared corpus is modified.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import convert, source
from tlhdig.paths import CORPUS

REL = "CTH 170_XML_TLH/KBo 31.40.xml"


def test_primary_source_has_readable_unwrapped_lines_without_word_tags():
    data = (CORPUS / REL).read_bytes()
    spans = source.scan(data)
    assert not any(sp.tag == "w" for sp in spans)
    lines = {sp.attrs.get("lnr"): sp for sp in spans if sp.tag == "lb"}
    assert {"Vs. 2", "Vs. 3"}.issubset(lines)
    assert all("cu" in lines[label].attrs for label in ("Vs. 2", "Vs. 3"))
    assert b"<P___Standard>" in data
    assert b"<sGr>" in data and b"<aGr>" in data and b"<d>" in data


def test_primary_source_unwrapped_readings_are_queryable_in_actual_tf(tmp_path):
    """RED: now fails because converter processes only literal <w> elements."""
    from tf.fabric import Fabric

    out = tmp_path / "tf"
    result = convert.build(
        CORPUS, out,
        files=[CORPUS / REL],
        patches={},
        ledger=convert.Ledger(),
        load=False,
    )
    assert result, "single-file source-to-TF conversion must succeed"
    tf = Fabric(locations=str(out), silent="deep")
    # Load only features known to exist in the broken baseline. Asking
    # for det/sgr/agr here would return False before the test could observe
    # the substantive missing-readings failure: no lexical signs means
    # those sparse wrapper features do not exist in this one-file shard.
    api = tf.load("lnr sym")
    assert api is not None and api is not False

    F, L = api.F, api.L
    lines = {F.lnr.v(node): node for node in F.otype.s("line")}
    assert "Vs. 2" in lines and "Vs. 3" in lines

    def slots(label):
        return list(L.d(lines[label], otype="sign"))

    sign2 = slots("Vs. 2")
    sign3 = slots("Vs. 3")
    text2 = [F.sym.v(sign) for sign in sign2 if F.sym.v(sign)]
    text3 = [F.sym.v(sign) for sign in sign3 if F.sym.v(sign)]

    # Source-derived readings only: NEVER synthesize from lb@cu.
    for required in ("URU", "ŠEŠ", "QÍ", "BÍ", "MA"):
        assert required in text2, (required, text2)
    for required in ("DAM", "MEŠ"):
        assert required in text3, (required, text3)

    api = tf.load("lnr sym det sgr agr")
    assert api is not None and api is not False, "recovered wrapper flags must exist"
    F = api.F
    assert any(F.sym.v(sign) == "URU" and F.det.v(sign)
               for sign in sign2)
    assert any(F.sym.v(sign) == "ŠEŠ" and F.sgr.v(sign)
               for sign in sign2)
    assert any(F.sym.v(sign) == "QÍ" and F.agr.v(sign)
               for sign in sign2)
    assert any(F.sym.v(sign) == "MEŠ" and F.det.v(sign)
               for sign in sign3)
