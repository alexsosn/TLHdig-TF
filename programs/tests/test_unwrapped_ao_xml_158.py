"""RED / #158: legible AOxml mixed content outside <w> must be recoverable.

Anchored in the pinned KBo 31.40.xml source, Vs. 2. These tests intentionally
fail on the current converter because it only walks <w> for linguistic slots.
The scope is textual recovery; no cuneiform-based guessing is permitted.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tlhdig import convert


HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<AOxml xmlns:AO="http://hethiter.net/ns/AO/1.0">
<AOHeader><docID>KBo 31.40</docID></AOHeader>
<body><div1 type="transliteration"><text xml:lang="Hit">
<AO:Manuscripts><AO:TxtPubl>KBo 31.40</AO:TxtPubl></AO:Manuscripts>
<P___Standard>
"""
FOOTER = "</P___Standard></text></div1></body></AOxml>"


def _build(tmp_path, contents):
    source = tmp_path / "corpus" / "CTH 170_XML_TLH" / "KBo 31.40.xml"
    source.parent.mkdir(parents=True)
    raw = (HEADER + contents + FOOTER).encode("utf8")
    source.write_bytes(raw)
    api = convert.build(source.parents[1], tmp_path / "tf", silent="deep")
    assert api is not None
    assert source.read_bytes() == raw, "converter must not edit source XML"
    return api


def _line_signs(api, ref):
    target = next(
        line for line in api.F.otype.s("line") if api.F.lnr.v(line) == ref
    )
    signs = api.L.d(target, otype="sign")
    return [
        api.F.sym.v(s)
        for s in signs
        if not (getattr(api.F, "anchor", None) and api.F.anchor.v(s))
        and api.F.sym.v(s)
    ]


def test_pinned_kbo3140_unwrapped_mixed_content_becomes_queryable(tmp_path):
    """Vs. 2 currently has visible cu but zero linguistic sign slots (#158)."""
    api = _build(
        tmp_path,
        """<lb txtid="KBo 31.40" lnr="Vs. 2" lg="Hit"
cu="𒌷𒈪𒄑𒍝𒊑𒋀𒅀𒆠𒉈𒈠𒁺𒊌𒋡"/>
<del_in/><space c="16"/> <d>URU</d>mi<del_fin/>-iz-za-ri
<sGr>ŠEŠ</sGr><aGr>-IA</aGr> <aGr>QÍ-BÍ-MA</aGr>
""",
    )
    readings = _line_signs(api, "Vs. 2")
    assert "URU" in readings, readings
    assert "ŠEŠ" in readings, readings
    assert "IA" in readings, readings
    assert len(readings) >= 7, readings
    assert any(api.F.trans.v(w) for w in api.F.otype.s("word"))


def test_mixed_wrapped_and_unwrapped_never_duplicates_existing_word(tmp_path):
    """A real <w> keeps its meaning; raw tail text is additional content."""
    api = _build(
        tmp_path,
        """<lb txtid="KBo 31.40" lnr="Vs. 2" lg="Hit" cu="𒀀𒈨𒌍"/>
<w trans="a">a</w> <sGr>MEŠ</sGr>
""",
    )
    readings = _line_signs(api, "Vs. 2")
    assert readings.count("a") == 1, readings
    assert readings.count("MEŠ") == 1, readings


def test_damage_only_unwrapped_line_remains_semantically_empty(tmp_path):
    """A cuneiform line-level display or damage marks cannot invent readings."""
    api = _build(
        tmp_path,
        """<lb txtid="KBo 31.40" lnr="Vs. 2" lg="Hit" cu="▒▒▒"/>
<del_in/><space c="16"/><del_fin/>
""",
    )
    assert _line_signs(api, "Vs. 2") == []
    # ADR-0001: line survives via synthetic empty slot, not sidecar
    assert api.F.otype.s("line")


def test_visible_cu_alone_never_fabricates_transliteration(tmp_path):
    """No visible raw transliteration, even if the edition has cu glyphs."""
    api = _build(
        tmp_path,
        """<lb txtid="KBo 31.40" lnr="Vs. 2" lg="Hit" cu="𒌷𒈪𒄑"/>
<space c="16"/>
""",
    )
    assert _line_signs(api, "Vs. 2") == []
