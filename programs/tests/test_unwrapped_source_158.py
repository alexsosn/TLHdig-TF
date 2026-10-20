"""Primary-source RED integration gate for #158's genuinely unwrapped AOxml.

This pilot deliberately builds only the real immutable KBo 31.40 record into
a throwaway Text-Fabric dataset; no release or shared corpus is modified.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import convert, signs, source, structure, unwrapped
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


def test_existing_tokenizer_reads_verbatim_unwrapped_line_without_guessing_cu():
    """Research control: isolate byte tokenisation from the broken converter route."""
    data = (CORPUS / REL).read_bytes()
    spans = source.scan(data)
    line = next(sp for sp in spans if sp.tag == "lb"
                and sp.attrs.get("lnr") == "Vs. 2")
    owners = [sp for sp in spans if sp.tag == "P___Standard"
              and sp.inner_start <= line.outer_start < sp.inner_end]
    assert len(owners) == 1, "a mixed-content line must have one source paragraph"
    payload = data[line.outer_end:owners[0].inner_end]
    assert payload and b"<d>URU</d>" in payload and b"<sGr>" in payload

    tokens = signs.tokenise_word(payload)
    readings = [t.sym for t in tokens]
    assert {"URU", "ŠEŠ", "QÍ", "BÍ", "MA"}.issubset(readings), readings
    assert any(t.sym == "URU" and t.det for t in tokens)
    assert any(t.sym == "ŠEŠ" and t.sgr for t in tokens)
    assert any(t.sym == "QÍ" and t.agr for t in tokens)
    # Without a <w> wrapper the exact original bytes must still round-trip.
    assert "".join(t.srcxml + t.after for t in tokens) == payload.decode("utf8")


def test_verbatim_unwrapped_source_lexical_boundaries():
    """Source bytes, not reserialized XML, fix the real transliteration coordinates."""
    data = (CORPUS / REL).read_bytes()
    spans = source.scan(data)
    for label, expected in (
        ("Vs. 2", {"URU", "ŠEŠ", "QÍ", "BÍ", "MA"}),
        ("Vs. 3", {"DAM", "MEŠ"}),
    ):
        lb = next(sp for sp in spans if sp.tag == "lb"
                  and sp.attrs.get("lnr") == label)
        ps = [sp for sp in spans if sp.tag == "P___Standard"
              and sp.inner_start <= lb.outer_start < sp.inner_end]
        assert len(ps) == 1
        segments = unwrapped.groups(data, lb.outer_end, ps[0].inner_end)
        assert len(segments) >= 3
        assert b"".join(data[a:b] for a, b in segments) == data[lb.outer_end:ps[0].inner_end]
        assert all(a < b for a, b in segments)
        decoded = [t for a, b in segments
                   for t in signs.tokenise_word(data[a:b])]
        # Independent line-level source oracle for the sign-language validator.
        # Both routes use the tokenization rules, but their lexical boundaries
        # are derived differently and must agree on every nonempty sign.
        direct = signs.tokenise_word(data[lb.outer_end:ps[0].inner_end])
        def values(tokens):
            return [(t.sym, t.type, t.det, t.sgr, t.agr)
                    for t in tokens if t.type != "empty"]
        assert values(decoded) == values(direct)
        assert expected.issubset({t.sym for t in decoded})
        assert any(t.det and t.sym in {"URU", "MEŠ"} for t in decoded)
        assert all(a >= lb.outer_end and b <= ps[0].inner_end for a, b in segments)


def test_unwrapped_boundaries_fail_closed_for_ambiguous_markup():
    import pytest

    for raw in (
        b"a <w>b</w> c",
        b"<sGr>incomplete",
        b"<sGr>x</aGr>",
        b"a <parsep/> b",
        b"z <lb lnr='2'/> i",
        b"<P___Standard>a</P___Standard>",
        b"a <unknown>data</unknown>",
        b"a < b",
    ):
        with pytest.raises(unwrapped.UnwrappedBoundaryError):
            unwrapped.groups(raw, 0, len(raw))


def test_unwrapped_markers_and_truly_empty_lines_are_not_lexical_inventions():
    cases = (b"", b" \t\n", b"<del_in/><del_fin/>", b"<space c='3'/>")
    for raw in cases:
        assert unwrapped.groups(raw, 0, len(raw)) == ()
    raw = b"<del_in/> <space c='2'/> <d>URU</d>mi <sGr>GAL</sGr>"
    segments = unwrapped.groups(raw, 0, len(raw))
    assert b"".join(raw[a:b] for a, b in segments) == raw
    readings = [t.sym for a, b in segments
                for t in signs.tokenise_word(raw[a:b]) if t.sym]
    assert readings == ["URU", "mi", "GAL"]


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

    api = tf.load("lnr sym det sgr agr inferred src_span")
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

    # Every recovered lexical group comes from actual source bytes, while
    # no literal source <w> exists in this document. Do not contaminate the
    # separate structural census of source-attested words with derived groups.
    lexical = list(F.otype.s("word"))
    assert lexical
    assert all(F.inferred.v(w) == 1 for w in lexical)
    assert structure.count_document((CORPUS / REL).read_bytes())["word"] == 0
    counted = structure.graph_counts(out)
    assert counted["word"] == counted["inferred_word"] == len(lexical)
    raw = (CORPUS / REL).read_bytes()
    spans = [F.src_span.v(w) for w in lexical]
    assert all(span and "-" in span for span in spans)
    slices = []
    for span in spans:
        a, b = (int(v) for v in span.split("-", 1))
        assert 0 <= a < b <= len(raw)
        slices.append(raw[a:b])
    assert any(b"<d>URU</d>" in piece for piece in slices)
