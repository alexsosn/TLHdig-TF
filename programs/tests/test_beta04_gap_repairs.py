"""Independent source-to-repaired-XML regression for Beta 0.4 gap-word damage."""
import re
from pathlib import Path
from xml.parsers import expat

from lxml import etree
import pytest
from tlhdig import repair

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus" / "TLHdig-0.4"
CASES = {
    "CTH 570_XML_HDivT/KBo 58.79+.xml": (267, 48, 19, 6),
    "CTH 580_XML_HDivT/KUB 22.17.xml": (44, 23, 8, 1),
    "CTH 580_XML_HDivT/KUB 50.29.xml": (82, 37, 4, 2),
    "CTH 580_XML_HDivT/KUB 50.117.xml": (178, 56, 8, 2),
    "CTH 585_XML_HDivT/585_u+.xml": (201, 35, 4, 1),
}

@pytest.mark.parametrize("rel,counts", CASES.items())
def test_gap_repairs_preserve_source_structure(rel, counts):
    from beta04_gap_repairs import propose
    raw = (CORPUS / rel).read_bytes()
    assert not repair.parses(raw)
    patches = propose(rel, raw)
    fixed = repair.apply(raw, patches, expect_sha=repair.sha256(raw))
    expat.ParserCreate(namespace_separator="}").Parse(fixed, True)
    tree = etree.fromstring(fixed)
    words, lines, gaps, closures = counts
    assert (len(tree.findall(".//w")), len(tree.findall(".//lb")), len(tree.findall(".//gap"))) == (words, lines, gaps)
    assert not tree.xpath("//w//w | //w//lb")
    assert len(patches) == 2 * closures
    assert fixed.count(b"</w>") - raw.count(b"</w>") == closures
    # Compare independently: literal word, line, gap, note and sign-wrapper starts
    # must all survive, and only the malformed trans attributes may be rewritten.
    pattern = rb"<(?:w|lb|gap|note|d|sGr|aGr|del_in|del_fin)(?=[\s/>])"
    assert re.findall(pattern, raw) == re.findall(pattern, fixed)
    # Strip the only authorized transformations from the result and compare to
    # the original at the same positions, not by comparing reserialized XML.
    current = raw
    edits = []
    for p in patches:
        assert current.count(p.old) == 1
        pos = current.index(p.old)
        edits.append((pos,p))
        if p.new.startswith(b"</w>") and p.new[4:] == p.old:
            pass
        else:
            assert p.new.replace(b"&lt;", b"<").replace(b"&quot;", b'"') == p.old
        current = current[:pos] + p.new + current[pos+len(p.old):]
    assert current == fixed
    for pos,p in reversed(edits):
        assert current[pos:pos+len(p.new)] == p.new
        current = current[:pos] + p.old + current[pos+len(p.new):]
    assert current == raw

def test_changed_source_is_rejected():
    from beta04_gap_repairs import propose
    rel = next(iter(CASES))
    with pytest.raises(ValueError, match="SHA-256"):
        propose(rel, (CORPUS / rel).read_bytes() + b" ")
