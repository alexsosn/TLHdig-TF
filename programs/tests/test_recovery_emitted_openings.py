"""TDD #150: independent immutable-source tag opening identity in emitted TF.

Count parity can conceal one omitted and another duplicated/fabricated word or
line. This test maps EVERY real original <w>/<lb> opening into the *loaded*
word/layout/line TF graph in four SHA-reviewed opt-in source documents.
"""
from __future__ import annotations

import re

import pytest

from tlhdig import convert, prepared_source, recovery, repair
from tlhdig.paths import CORPUS, PATCHES

REVIEWED = (
    ("CTH 209_XML_TLH/KBo 12.55.xml", 14, 7),
    ("CTH 448_XML_BESRIT/KBo 10.36.xml", 160, 59),
    ("CTH 820_XML_TLH/KUB 48.15.xml", 37, 17),
    ("CTH 832_XML_TLH/UBT 70.xml", 5, 5),
)


def _raw_openers(data: bytes, tag: bytes) -> tuple[int, ...]:
    # Independently locate original literal opening tag names. This does not
    # read the repaired XML, a build ledger, or the TF converter's features.
    # The four reviewed source files contain no comment/CDATA false positives.
    return tuple(m.start() for m in re.finditer(
        rb"<" + tag + rb"(?=[ \t\r\n/>])", data
    ))


@pytest.mark.parametrize("rel,word_count,line_count", REVIEWED)
def test_complete_tf_graph_has_one_literal_source_opening_per_word_and_line(
    tmp_path, rel, word_count, line_count,
):
    prep = prepared_source.prepare(rel)
    raw_words = _raw_openers(prep.original_bytes, b"w")
    raw_lines = _raw_openers(prep.original_bytes, b"lb")
    assert len(raw_words) == word_count
    assert len(raw_lines) == line_count

    api = convert.build(
        CORPUS, tmp_path / "reviewed",
        files=[CORPUS / rel], patches=repair.read_manifest(PATCHES),
        terminal_recovery_paths=(rel,),
    )
    assert api is not None
    F = api.F
    words = F.otype.s("word")
    layouts = F.otype.s("layout")
    lines = F.otype.s("line")
    # A source <w> with no linguistic sign is a layout node. Other layout
    # or point-annotation nodes must not falsely claim a source <w> opener.
    emitted_words = [
        F.source_word_open.v(n) for n in (*words, *layouts)
        if F.source_word_open.v(n) is not None
    ]
    emitted_lines = [F.source_line_open.v(n) for n in lines]
    assert len(emitted_words) == len(raw_words)
    assert len(emitted_lines) == len(raw_lines)
    assert len(set(emitted_words)) == len(emitted_words)
    assert len(set(emitted_lines)) == len(emitted_lines)
    assert sorted(emitted_words) == list(raw_words)
    assert emitted_lines == list(raw_lines)
    assert all(
        prep.original_bytes[pos:pos + 2] == b"<w" for pos in emitted_words
    )
    assert all(
        prep.original_bytes[pos:pos + 3] == b"<lb" for pos in emitted_lines
    )
    recovered = [
        w for w in words if F.recovery_open.v(w) is not None
    ]
    assert len(recovered) == 1
    assert F.source_word_open.v(recovered[0]) == F.recovery_open.v(recovered[0])
    assert F.src_span.v(recovered[0]) is None, (
        "a real opening does not justify a fabricated literal closing span"
    )


def test_source_opening_emission_audit_rejects_compensating_and_reordered_nodes():
    prep = prepared_source.prepare("CTH 832_XML_TLH/UBT 70.xml")
    words = _raw_openers(prep.original_bytes, b"w")
    lines = _raw_openers(prep.original_bytes, b"lb")
    recovery.verify_emitted_openings(prep, words, lines)

    broken_cases = (
        (words[:-1] + (words[-2],), lines, "duplicate"),
        (words[:-1], lines, "missing"),
        (words + (words[-1],), lines, "duplicate"),
        ((words[1], words[0], *words[2:]), lines, "order"),
        (words, (lines[1], lines[0], *lines[2:]), "order"),
        (words, lines[:-1] + (words[-1],), "source"),
    )
    for emitted_words, emitted_lines, reason in broken_cases:
        with pytest.raises(recovery.SignatureDrift, match=reason):
            recovery.verify_emitted_openings(
                prep, emitted_words, emitted_lines,
            )


def test_default_nonrecovery_output_does_not_claim_source_opening_mapping(tmp_path):
    rel = "CTH 832_XML_TLH/UBT 70.xml"
    api = convert.build(
        CORPUS, tmp_path / "default",
        files=[CORPUS / rel], patches=repair.read_manifest(PATCHES),
    )
    assert api is not None
    assert "source_word_open" not in api.Fall()
    assert "source_line_open" not in api.Fall()
