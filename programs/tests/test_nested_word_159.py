"""Source-grounded RED gates for #159: malformed word ancestors across <lb>.

These tests use the pinned immutable KBo 41.49+ and its checked patch manifest.
The failing TF query intentionally precedes any production repair change.
"""
from collections import Counter
from pathlib import Path
import re
import sys

import lxml.etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import convert, repair, signs, source
from tlhdig.paths import CORPUS, PATCHES

REL = "CTH 479_XML_BESRIT/KBo 41.49+.xml"
LINE = "{€1+2+3} Rs. III 2/2′"
WORD = "pé-e-da-an-zi"


def _source():
    return (CORPUS / REL).read_bytes()


def _repaired():
    original = _source()
    entry = repair.read_manifest(PATCHES)[REL]
    assert repair.sha256(original) == entry[0]
    assert len(entry[1]) == 14
    # Every change is a unique, immutable-source line label. A closure is
    # inserted before that exact <lb>; no source characters are rewritten.
    assert all(p.new == b"</w>" + p.old for p in entry[1])
    assert all(original.count(p.old) == 1 for p in entry[1])
    assert all(p.old.startswith(b'<lb txtid="KBo 41.49+" lnr="')
               for p in entry[1])
    repaired = repair.apply(original, entry[1], expect_sha=entry[0])
    assert repair.parses(repaired)
    return repaired


def test_immutable_word_imbalance_is_marker_only_and_aligned_to_source_lines():
    """Research control: exact evidence for closing a subset of *source* word opens."""
    original = _source()
    assert len(re.findall(rb"<w(?:\s|>)", original)) == 288
    assert original.count(b"</w>") == 274
    assert len(re.findall(rb"<lb(?:\s|>)", original)) == 84
    stack = []
    line_depth = Counter()
    for m in re.finditer(rb"<w(?:\s[^>]*)?>|</w>|<lb\s[^>]*?/>", original):
        raw = m.group()
        if raw.startswith(b"<w"):
            stack.append(m.start())
        elif raw.startswith(b"</w"):
            assert stack
            stack.pop()
        else:
            line_depth[len(stack)] += 1
    assert len(stack) == 14
    assert line_depth[0] == 1
    assert sum(n for depth, n in line_depth.items() if depth) == 83
    assert max(line_depth) == 14
    for p in stack:
        following = original[p:]
        assert following.startswith(b"<w><del_in/><del_fin/>")
        lb = following.index(b"<lb")
        # The crossing wrapper contains no transliteration readings before lb.
        before_line = following[:lb]
        assert not any(tok.sym and tok.type not in ("empty", "unknown", "ellipsis")
                       for tok in signs.tokenise_word(
                           before_line[len(b"<w>"):]
                       )), before_line[:100]


def test_hash_pinned_repair_recovers_source_word_parentage_without_fabrication():
    repaired = _repaired()
    root = ET.fromstring(repaired)
    lines = root.findall(".//lb")
    assert len(lines) == 84
    target = next(n for n in lines if n.get("lnr") == LINE)
    children = list(target.itersiblings())
    # The immediately following literal <w> belongs to this line. The
    # source-end-only patch incorrectly nested it under a marker-only <w>;
    # the reviewed earlier closure restores this literal word's parentage.
    word = next(n for n in children if n.tag == "w")
    assert word.text == WORD
    assert not any(a.tag == "w" for a in word.iterancestors())
    sign_sequence = [t.sym for t in signs.tokenise_word(WORD.encode("utf8"))]
    assert sign_sequence == ["pé", "e", "da", "an", "zi"]
    assert b"<w>p\xc3\xa9-e-da-an-zi</w>" in repaired
    # This test detects source drift while showing the current XML repair parses.
    assert source.scan(repaired)


def test_original_source_byte_coordinates_survive_relocated_closures():
    """Synthetic closing tags may not corrupt following literal word source spans."""
    original = _source()
    entry = repair.read_manifest(PATCHES)[REL]
    mapped = repair.OffsetMap(original, entry[1])
    rewritten = repair.apply(original, entry[1], expect_sha=entry[0])
    assert mapped.changed
    original_word = "<w>pé-e-da-an-zi</w>".encode("utf8")
    p = original.index(original_word)
    r = rewritten.index(original_word)
    assert mapped.is_exact(r) and mapped.is_exact(r + len(original_word) - 1)
    assert mapped.span_to_original(r, r + len(original_word)) == (
        p, p + len(original_word)
    )
    assert rewritten.count(original_word) == original.count(original_word) == 1


def test_recover_attested_peda_anzi_in_real_text_fabric_line(tmp_path):
    """RED: current nested-word skip loses every actual sign on this source line."""
    from tf.fabric import Fabric

    patches = repair.read_manifest(PATCHES)
    ledger = convert.Ledger()
    out = tmp_path / "tf"
    result = convert.build(
        CORPUS, out,
        files=[CORPUS / REL],
        patches={REL: patches[REL]},
        ledger=ledger,
        load=False,
    )
    assert result and ledger.converted == 1
    tf = Fabric(locations=str(out), silent="deep")
    api = tf.load("otype oslots lnr sym", silent="deep")
    assert api not in (False, None)
    F, L = api.F, api.L
    matches = [line for line in F.otype.s("line") if F.lnr.v(line) == LINE]
    assert len(matches) == 1
    got = [F.sym.v(sign) for sign in L.d(matches[0], otype="sign")]
    expected = ["pé", "e", "da", "an", "zi"]
    assert got == expected, {
        "source_file": REL,
        "line": LINE,
        "source_readings": expected,
        "actual_TF": got,
    }


def test_genuine_same_line_nested_word_is_not_repaired_as_cross_line_damage():
    xml = b"<text><lb lnr='1'/><w><sGr>LUGAL</sGr><w>ki</w></w></text>"
    root = ET.fromstring(xml)
    assert len(root.findall(".//w")) == 2
    assert root.findall(".//w")[0].find("w").text == "ki"
    assert repair.parses(xml)
    assert b"</w>" in xml
    assert b"<lb" in xml
