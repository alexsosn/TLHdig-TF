"""Independent source-to-repaired-XML regression for Beta 0.4 gap-word damage."""
import re
import sys
from pathlib import Path
from xml.parsers import expat

from lxml import etree
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
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


@pytest.mark.parametrize("rel", CASES)
def test_gap_repairs_keep_exact_source_coordinates_for_literal_tag_starts(rel):
    from beta04_gap_repairs import propose
    raw = (CORPUS / rel).read_bytes()
    patches = propose(rel, raw)
    fixed = repair.apply(raw, patches, expect_sha=repair.sha256(raw))
    mapped = repair.OffsetMap(raw, patches)
    # Independent ordinal alignment: no literal tag starts are inserted or removed.
    pattern = rb"<(?:w|lb|gap|note)(?=[\s/>])"
    before = list(re.finditer(pattern, raw))
    after = list(re.finditer(pattern, fixed))
    assert len(before) == len(after)
    for a, b in zip(before, after):
        assert a.group() == b.group()
        assert mapped.is_exact(b.start()), (rel, b.start(), b.group())
        assert mapped.to_original(b.start()) == a.start()


def test_gap_repairs_convert_all_five_documents_without_structural_or_marker_loss(tmp_path):
    from collections import Counter
    from beta04_gap_repairs import propose
    from tlhdig import convert, structure
    from tf.fabric import Fabric

    manifest = {}
    expected = Counter()
    for rel in CASES:
        raw = (CORPUS / rel).read_bytes()
        patches = propose(rel, raw)
        sha = repair.sha256(raw)
        manifest[rel] = (sha, patches)
        expected.update(structure.count_document(repair.apply(raw, patches, expect_sha=sha)))
    assert expected["word"] == 772 and expected["line"] == 199
    target = tmp_path / "tf"
    ledger = convert.Ledger()
    result = convert.build(CORPUS, target, files=[CORPUS / rel for rel in sorted(CASES)],
                           patches=manifest, ledger=ledger, load=False)
    assert result is not None
    assert ledger.converted == 5 and ledger.balances()
    assert ledger.marker_src and ledger.marker_src == ledger.marker_fed == ledger.marker_out
    actual = structure.graph_counts(target)
    for key in ("line", "colon", "note"):
        assert expected[key] == actual[key], (key, expected[key], actual[key])
    assert expected["word"] == actual["word"] + actual["layout"], (expected, actual)
    api = Fabric(locations=str(target), silent="deep").load("otype oslots src_file sym lnr", silent="deep")
    assert api
    assert {api.F.src_file.v(d) for d in api.F.otype.s("document")} == set(CASES)
    assert api.F.otype.s("sign") and api.F.otype.s("line")
