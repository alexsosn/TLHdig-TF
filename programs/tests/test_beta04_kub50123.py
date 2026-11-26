"""Real source regression for the changed Beta 0.4 KUB 50.123."""
import hashlib
from pathlib import Path
import re
import sys
from xml.parsers import expat

from lxml import etree
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tlhdig import repair

ROOT = Path(__file__).resolve().parents[2]
REL = "CTH 570_XML_HDivT/KUB 50.123.xml"
CORPUS = ROOT / "corpus" / "TLHdig-0.4"
SHA = "416695b2a7368d7a22b680533e9eb053858ce47068b3a3a8f1d2aa91b5590273"


def test_repair_swapped_closures():
    from beta04_kub50123 import propose
    raw = (CORPUS / REL).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SHA
    assert not repair.parses(raw)
    patches = propose(raw)
    fixed = repair.apply(raw, patches, expect_sha=SHA)
    expat.ParserCreate(namespace_separator="}").Parse(fixed, True)
    tree = etree.fromstring(fixed)
    for tag, count in {"w":91,"lb":15,"del_in":15,"del_fin":19}.items():
        assert len(re.findall(rb"<"+tag.encode()+rb"(?=[\s/>])", raw)) == count
        assert len(tree.findall(".//"+tag)) == count
    assert not tree.xpath("//w//w | //w//lb")
    assert len(tree.xpath("//*[local-name()='LineNrExpl']")) == 6
    wrapper, = tree.xpath("//*[local-name()='LineNrExpl'][del_in]")
    assert wrapper.getnext().find("space").get("c") == "14"
    following = wrapper.getnext().getnext()
    assert following.tag == "w" and following.get("mrp0sel") == "DEL"
    assert following.find("del_fin") is not None


def test_repair_rejects_source_drift():
    from beta04_kub50123 import propose
    with pytest.raises(ValueError, match="SHA-256"):
        propose((CORPUS / REL).read_bytes() + b" ")


def test_kub50123_tf_structure_and_markers(tmp_path):
    from beta04_kub50123 import propose
    from tlhdig import convert, structure
    from tf.fabric import Fabric
    raw = (CORPUS / REL).read_bytes()
    patches = propose(raw)
    manifest = {REL:(SHA,patches)}
    expected = structure.count_document(repair.apply(raw,patches,expect_sha=SHA))
    ledger = convert.Ledger()
    out = tmp_path / "tf"
    assert convert.build(CORPUS, out, files=[CORPUS/REL], patches=manifest, ledger=ledger, load=False)
    assert ledger.converted == 1
    assert ledger.marker_src and ledger.marker_src == ledger.marker_fed == ledger.marker_out
    actual = structure.graph_counts(out)
    assert actual["line"] == expected["line"] == 15
    assert actual["word"] + actual["layout"] == expected["word"] == 91
    api = Fabric(locations=str(out),silent="deep").load("otype oslots src_file lnr sym",silent="deep")
    assert api
    assert [api.F.src_file.v(n) for n in api.F.otype.s("document")] == [REL]
