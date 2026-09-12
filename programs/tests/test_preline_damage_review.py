"""Adversarial #52 probe: readable pre-line damage crossing the first real line."""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import convert


DOC = '''<?xml version="1.0" encoding="UTF-8"?>
<AOxml xmlns:AO="http://hethiter.net/ns/AO/1.0">
<AOHeader><docID>PRE DAMAGE</docID><meta/></AOHeader>
<body><div1 type="transliteration"><text xml:lang="Hit">
<w trans="pre">pa<del_in/>-it</w>
<lb txtid="PRE DAMAGE" lnr="Vs. I 1" lg="Hit" cu="&#x12000;"/>
<w trans="line"><del_fin/>nu</w>
</text></div1></body></AOxml>'''


def test_preline_damage_can_close_at_start_of_first_real_line_without_extent_bleed(tmp_path: Path) -> None:
    src = tmp_path / "corpus" / "CTH 999_XML_TLH"
    src.mkdir(parents=True)
    (src / "PRE DAMAGE.xml").write_text(DOC, encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None

    pre = next(w for w in api.F.otype.s("word") if api.F.trans.v(w) == "pre")
    line_word = next(w for w in api.F.otype.s("word") if api.F.trans.v(w) == "line")
    pre_signs = list(api.L.d(pre, otype="sign"))
    line_signs = list(api.L.d(line_word, otype="sign"))

    assert [api.F.sym.v(s) for s in pre_signs] == ["pa", "it"]
    assert [api.F.sym.v(s) for s in line_signs] == ["nu"]
    assert all(not api.L.u(s, otype="line") for s in pre_signs)

    line = api.F.otype.s("line")[0]
    assert list(api.L.d(line, otype="sign")) == line_signs

    # del_in sits after `pa`, so only `it` is inside the carried range.  The first
    # real line begins with del_fin at offset 0, so its `nu` sign is outside it.
    missing = getattr(api.F, "missing", None)
    assert missing is not None
    assert missing.v(pre_signs[0]) is None
    assert missing.v(pre_signs[1]) == 1
    assert missing.v(line_signs[0]) is None

    clusters = [c for c in api.F.otype.s("cluster") if api.F.type.v(c) == "del"]
    assert len(clusters) == 1
    cluster_signs = set(api.L.d(clusters[0], otype="sign"))
    assert pre_signs[1] in cluster_signs
    assert pre_signs[0] not in cluster_signs
    assert line_signs[0] not in cluster_signs
