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
