"""Repair of syntactically corrupt source files (plan §7.2).

Repairs are declarative: a detector proposes exact old->new byte replacements, the
manifest records them with the file's SHA-256, and application asserts that the hash
matches and each `old` occurs exactly once.  Scope is restricted to syntactic
corruption -- the converter must not become an uncredited critical edition.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import repair


def prop(src: str):
    return repair.propose(src.encode("utf8"))


def fixed(src: str) -> str:
    data = src.encode("utf8")
    return repair.apply(data, repair.propose(data)).decode("utf8")


# ------------------------------------------------------------------- detectors

def test_corrupted_gap_tag():
    """A bad find-replace turned <gap c="Text bricht ab"/> into <kap c-"Te%t pricht ap"."""
    src = '<w trans="x"><kap c-"Te%t pricḫt ap" mrp0sel=" 1 ">y</w>'
    out = fixed(src)
    assert "<kap" not in out
    assert '<gap c="Text bricht ab"/>' in out


def test_unescaped_quote_in_attribute_value():
    src = '<lb lnr=" {€1+2} Rs. IV 4"/1′" lg="Hit"/>'
    out = fixed(src)
    assert out.count('"') % 2 == 0
    assert "&quot;" in out or '4/1′' in out


def test_trailing_quote_after_attribute():
    src = '<w trans="ṣuppu"\' mrp0sel="AKK">x</w>'
    out = fixed(src)
    assert repair.parses(out.encode("utf8"))


def test_unclosed_odf_line_break():
    src = '<w mrp0sel="DEL"><text:line-break</w>'
    out = fixed(src)
    assert repair.parses(('<r xmlns:text="urn:t">' + out + "</r>").encode("utf8"))


def test_parser_error_element_in_attribute():
    src = '<lb cu="𒅆𒇽<parser_error>kúrḫa</parser_error>𒄩▒"/>'
    out = fixed(src)
    assert "parser_error" not in out
    assert "kúrḫa" in out          # the reading is kept, only the wrapper goes


def test_duplicate_identical_attribute():
    src = '<lb cu="AB" txtid="x" cu="AB"/>'
    out = fixed(src)
    assert out.count("cu=") == 1
    assert repair.parses(out.encode("utf8"))


def test_detector_is_a_no_op_on_clean_input():
    src = '<AOxml><w trans="a">x-y</w></AOxml>'
    assert prop(src) == []
    assert fixed(src) == src


# ------------------------------------------------------------- safety assertions

def test_apply_rejects_patch_whose_old_is_absent():
    data = b"<r>hello</r>"
    p = repair.Patch(old=b"missing", new=b"x", reason="test")
    try:
        repair.apply(data, [p])
    except repair.PatchError as e:
        assert "not found" in str(e)
    else:
        raise AssertionError("expected PatchError")


def test_apply_rejects_ambiguous_patch():
    data = b"<r>aa</r>"
    p = repair.Patch(old=b"a", new=b"b", reason="test")
    try:
        repair.apply(data, [p])
    except repair.PatchError as e:
        assert "2 times" in str(e)
    else:
        raise AssertionError("expected PatchError")


def test_manifest_roundtrip(tmp_path):
    data = b'<r><kap c-"Te%t pricht ap"></r>'
    patches = repair.propose(data)
    m = tmp_path / "patches.yaml"
    repair.write_manifest(m, {"a/b.xml": (repair.sha256(data), patches)})
    loaded = repair.read_manifest(m)
    assert loaded["a/b.xml"][0] == repair.sha256(data)
    assert loaded["a/b.xml"][1][0].old == patches[0].old


def test_manifest_rejects_hash_mismatch():
    data = b"<r>x</r>"
    try:
        repair.apply(data, [], expect_sha=repair.sha256(b"different"))
    except repair.PatchError as e:
        assert "sha256" in str(e)
    else:
        raise AssertionError("expected PatchError")


def test_stray_unterminated_w_tag_is_removed():
    """`<w <w trans=...>` -- a duplicated, never-terminated <w>.  81 of the broken
    files carry one; the leading fragment is spurious and is dropped."""
    src = '<r><w <w trans="na~" mrp0sel="DEL">a</w></r>'
    out = fixed(src)
    assert out == '<r><w trans="na~" mrp0sel="DEL">a</w></r>'
    assert repair.parses(out.encode("utf8"))


def test_stray_w_before_another_element():
    src = '<r><w \n<lb lnr="4"/><w lg="Lin"><space c="14"/></w></r>'
    out = fixed(src)
    assert "<w \n<lb" not in out
    assert repair.parses(out.encode("utf8"))


def test_stray_w_patch_is_unambiguous():
    """`<w ` occurs thousands of times per file, so the patch must carry enough
    context to identify exactly one site."""
    src = '<r><w a="1">x</w><w b="2">y</w><w <w c="3">z</w></r>'
    patches = prop(src)
    assert len(patches) == 1
    assert src.encode("utf8").count(patches[0].old) == 1
    assert repair.parses(fixed(src).encode("utf8"))


def test_bare_lt_inside_attribute_value():
    src = '<r><w trans="pan- <parse" mrp0sel="???">x</w></r>'
    out = fixed(src)
    assert repair.parses(out.encode("utf8"))
    assert "&lt;parse" in out


def test_iterative_proposal_fixes_layered_corruption():
    """One corruption can hide the next, so proposal re-runs until the file parses."""
    src = (
        '<r><w <w trans="a">x</w>'
        '<lb cu="AB" cu="AB"/>'
        '<w trans="b"><text:line-break</w></r>'
    )
    data = src.encode("utf8")
    assert not repair.parses(data)
    patches = repair.propose_iteratively(data)
    out = repair.apply(data, patches)
    assert repair.parses(b'<r xmlns:text="urn:t">' + out[3:-4] + b"</r>")
    assert len(patches) >= 3


def _iterfix(src: str) -> str:
    data = src.encode("utf8")
    return repair.apply(data, repair.propose_iteratively(data)).decode("utf8")


def test_crossing_tags_are_closed_in_order():
    """`<w><X>...</w>...</X>` -- X opened inside <w> and closed outside it.

    Repair takes two rounds: close the inner element in place, then drop the now
    orphaned close.  That is why proposal iterates.
    """
    src = '<r><w><AO:K><gap c="a"/></w> </AO:K></r>'
    out = _iterfix(src)
    assert "</AO:K></w>" in out
    assert out.count("</AO:K>") == 1


def test_wrong_closing_tag_name():
    """`<AO:TxtPubl>x</AO:Manuscripts>` -- the inner element is closed by its parent."""
    src = '<r><AO:M><AO:T>KBo 38.169</AO:M></r>'
    out = _iterfix(src)
    assert repair.parses(('<r xmlns:AO="urn:a">' + out[3:]).encode("utf8"))


def test_stray_close_with_nothing_open_is_dropped():
    src = "<r><w>x</SP___Page></w></r>"
    out = _iterfix(src)
    assert "SP___Page" not in out
    assert repair.parses(out.encode("utf8"))


# ------------------------------------------------- original <-> repaired coordinates

def test_offset_map_identity_when_no_patches():
    data = b"<r>abc</r>"
    m = repair.OffsetMap(data, [])
    assert [m.to_original(i) for i in range(len(data))] == list(range(len(data)))


def test_offset_map_after_a_deletion():
    """`old` is longer than `new`: repaired offsets run ahead of original ones."""
    data = b"<r>XXhello</r>"
    p = repair.Patch(old=b"XX", new=b"", reason="t")
    out = repair.apply(data, [p])
    m = repair.OffsetMap(data, [p])
    assert out == b"<r>hello</r>"
    # 'hello' starts at 3 in the repaired stream, at 5 in the original
    assert out[3:8] == b"hello"
    assert data[m.to_original(3) : m.to_original(3) + 5] == b"hello"


def test_offset_map_after_an_insertion():
    data = b"<r>ab</r>"
    p = repair.Patch(old=b"ab", new=b"a&lt;b", reason="t")
    out = repair.apply(data, [p])
    m = repair.OffsetMap(data, [p])
    i = out.index(b"</r>")
    assert data[m.to_original(i) :].startswith(b"</r>")


def test_offset_map_with_several_patches():
    data = b"<r>AA one BB two CC three</r>"
    ps = [
        repair.Patch(old=b"AA ", new=b"", reason="t"),
        repair.Patch(old=b"BB ", new=b"X ", reason="t"),
        repair.Patch(old=b"CC ", new=b"YYYY ", reason="t"),
    ]
    out = repair.apply(data, ps)
    m = repair.OffsetMap(data, ps)
    for token in (b"one", b"two", b"three"):
        i = out.index(token)
        assert data[m.to_original(i) :].startswith(token), token


def test_offset_map_span_helper():
    data = b"<r>XX<w>ab</w></r>"
    p = repair.Patch(old=b"XX", new=b"", reason="t")
    out = repair.apply(data, [p])
    m = repair.OffsetMap(data, [p])
    a = out.index(b"<w>")
    b = out.index(b"</w>") + 4
    oa, ob = m.span_to_original(a, b)
    assert data[oa:ob] == b"<w>ab</w>"


def test_offset_map_with_non_monotonic_patches():
    """Patches are proposed iteratively and can revisit an earlier site after a later
    one -- KBo 31.47.xml does exactly this. A left-hand edit applied after a right-hand
    one shifts the right-hand edit's final position, which a single cumulative shift
    recorded at application time never revises."""
    data = b"<r>AAA one BBB two</r>"
    ps = [
        repair.Patch(old=b"BBB ", new=b"Y ", reason="right first"),
        repair.Patch(old=b"AAA ", new=b"", reason="then left"),
    ]
    out = repair.apply(data, ps)
    assert out == b"<r>one Y two</r>"
    m = repair.OffsetMap(data, ps)
    for token in (b"one", b"two"):
        i = out.index(token)
        assert data[m.to_original(i) :].startswith(token), token


def test_offset_map_interleaved_left_right_left():
    data = b"<r>L1 mid R1 tail L2 end</r>"
    ps = [
        repair.Patch(old=b"R1 ", new=b"RR1 ", reason="right"),
        repair.Patch(old=b"L1 ", new=b"", reason="left"),
        repair.Patch(old=b"L2 ", new=b"LLL2 ", reason="left again"),
    ]
    out = repair.apply(data, ps)
    m = repair.OffsetMap(data, ps)
    for token in (b"mid", b"tail", b"end"):
        i = out.index(token)
        assert data[m.to_original(i) :].startswith(token), token


def test_offset_map_against_the_real_manifest():
    """Every `<w>` in every repaired file must map back to a `<w>` in the original.

    Word spans are what `src_span` actually records, so this is the property that
    matters.  Offsets that land inside a rewritten region are excluded: those bytes
    have no one-to-one counterpart by construction, which `is_exact` reports.
    """
    import re

    from tlhdig.paths import CORPUS, PATCHES

    man = repair.read_manifest(PATCHES)
    checked = 0
    for rel, (sha, patches) in man.items():
        data = (CORPUS / rel).read_bytes()
        out = repair.apply(data, patches, expect_sha=sha)
        m = repair.OffsetMap(data, patches)
        for hit in re.finditer(rb"<w[ >]", out):
            i = hit.start()
            if not m.is_exact(i):
                continue
            o = m.to_original(i)
            assert data[o : o + 2] == b"<w", (rel, i, o, data[o : o + 12])
            checked += 1
    assert checked > 20_000, checked   # ~22k <w> across the 173 repaired files


def test_offsets_inside_a_rewritten_region_are_reported_as_inexact():
    data = b"<r>keep AAAA keep</r>"
    p = repair.Patch(old=b"AAAA", new=b"B", reason="t")
    m = repair.OffsetMap(data, [p])
    out = repair.apply(data, [p])
    i = out.index(b"B")
    assert not m.is_exact(i)
    assert m.is_exact(out.index(b"</r>"))
