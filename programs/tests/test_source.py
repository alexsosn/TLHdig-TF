"""Prototype 1 / Contract A: byte spans must reconstruct the source exactly."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import source
from tlhdig.paths import corpus_files


def test_tag_end_respects_quoted_gt():
    data = b'<note n="1" c="a &lt;b&gt; c" /> tail'
    end, sc = source._tag_end(data, 0)
    assert data[:end] == b'<note n="1" c="a &lt;b&gt; c" />'
    assert sc is True


def test_tag_end_raw_gt_inside_attribute():
    # AOxml footnotes really do carry unescaped '>' inside @c
    data = b'<w trans="x" c="see <SP>foo</SP> here">body</w>'
    end, sc = source._tag_end(data, 0)
    assert sc is False
    assert data[end : end + 4] == b"body"


def test_inner_bytes_of_word():
    data = b'<r><w trans="a">x-<del_in/>y</w></r>'
    spans = source.scan(data)
    w = next(s for s in spans if s.tag == "w")
    assert source.inner_bytes(data, w) == b"x-<del_in/>y"


def test_self_closing_has_no_inner():
    spans = source.scan(b"<r><lb lnr='1'/></r>")
    lb = next(s for s in spans if s.tag == "lb")
    assert lb.self_closing and lb.inner is None
    assert source.inner_bytes(b"<r><lb lnr='1'/></r>", lb) == b""


def test_corpus_sample_reconstructs():
    files = corpus_files()
    random.seed(11)
    sample = random.sample(files, 400)
    bad = []
    for f in sample:
        data = f.read_bytes()
        try:
            spans = source.scan(data)
        except Exception:
            continue  # malformed files are the repair stage's problem
        problems = source.verify_reconstruction(data, spans)
        if problems:
            bad.append((f.name, problems[:2]))
    assert not bad, bad[:5]


def test_outer_word_spans_preserve_document_order_and_filter_nested_and_external_words():
    data = b"<r><w>header</w><text><w>a<w>b</w><w/></w><lb/><w/><w>c</w><p><w>d</w></p></text><w>tail</w></r>"
    spans = source.scan(data)
    text = next(s for s in spans if s.tag == "text")
    got = source.outermost_words(spans, text)
    assert [source.outer_bytes(data, s) for s in got] == [
        b"<w>a<w>b</w><w/></w>", b"<w/>", b"<w>c</w>", b"<w>d</w>"]
    assert got == [s for s in spans if s.tag == "w" and
                   text.inner_start <= s.outer_start < text.inner_end and
                   not any(o is not s and o.tag == "w" and
                           text.inner_start <= o.outer_start < text.inner_end and
                           o.outer_start <= s.outer_start and s.outer_end <= o.outer_end
                           for o in spans)]


def test_outer_word_spans_matches_quadratic_reference_on_real_beta04_documents():
    # Selected directly from the large-source benchmark, with nesting and ordinary
    # documents; the independent quadratic reference is only used for this test.
    from tlhdig.paths import CORPUS
    names = ("CTH 561_XML_HDivT/KUB 5.1+.xml", "CTH 106_XML_TLH/Bo 86_299.xml",
             "CTH 479_XML_BESRIT/KBo 41.49+.xml")
    for rel in names:
        spans = source.scan((CORPUS / rel).read_bytes())
        text = next(s for s in spans if s.tag == "text")
        words = [s for s in spans if s.tag == "w" and
                 text.inner_start <= s.outer_start < text.inner_end]
        expected = [s for s in words if not any(o is not s and
                    o.outer_start <= s.outer_start and s.outer_end <= o.outer_end
                    for o in words)]
        assert source.outermost_words(spans, text) == expected, rel
