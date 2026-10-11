"""#150 RED: a consumer independently audits source events against loaded TF.

Unlike the converter's internal emitted-openings ledger, these tests read
serialized TF nodes after building the four source-SHA-reviewed pilot files.
Source authority comes from immutable AOxml + mechanical-only lexical edits.
"""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from tlhdig import convert, prepared_source, recovery, repair
from tlhdig.paths import CORPUS, PATCHES

PILOTS = (
    ("CTH 209_XML_TLH/KBo 12.55.xml", 14),
    ("CTH 448_XML_BESRIT/KBo 10.36.xml", 160),
    ("CTH 820_XML_TLH/KUB 48.15.xml", 37),
    ("CTH 832_XML_TLH/UBT 70.xml", 5),
)


def _loaded(tmp_path, rel):
    prep = prepared_source.prepare(rel)
    api = convert.build(
        CORPUS, tmp_path / "tf", files=[CORPUS / rel],
        patches=repair.read_manifest(PATCHES), terminal_recovery_paths=(rel,),
    )
    assert api is not None
    return prep, api


@pytest.mark.parametrize("rel,nwords", PILOTS)
def test_external_recovery_gate_checks_original_source_and_loaded_graph(
    tmp_path, rel, nwords,
):
    from tlhdig import recovery_audit

    prep, api = _loaded(tmp_path, rel)
    report = recovery_audit.verify(prep, api)
    assert report.words == nwords
    assert report.lines == len(recovery.original_opening_sequences(prep)[1])
    assert report.analyses >= 0


def test_external_gate_rejects_substitution_of_word_line_and_sign_provenance(
    tmp_path,
):
    from tlhdig import recovery_audit

    rel = "CTH 832_XML_TLH/UBT 70.xml"
    prep, api = _loaded(tmp_path, rel)
    assert recovery_audit.verify(prep, api).words == 5
    words = sorted(
        n for n in (*api.F.otype.s("word"), *api.F.otype.s("layout"))
        if api.F.source_word_open.v(n) is not None
    )
    lines = tuple(api.F.otype.s("line"))
    assert len(words) == len(lines) == 5

    def spoof(feature, node, value):
        class FakeV:
            def v(self, n):
                return value if n == node else getattr(api.F, feature).v(n)

        class FakeF:
            def __getattr__(self, key):
                return FakeV() if key == feature else getattr(api.F, key)

        return SimpleNamespace(F=FakeF(), E=api.E, L=api.L, Fall=api.Fall)

    # Equal aggregate counts do not prevent a fake/duplicated opening.
    wrong_word = spoof(
        "source_word_open", words[0], api.F.source_word_open.v(words[1]),
    )
    with pytest.raises(recovery_audit.AuditError, match="word|opening|duplicate"):
        recovery_audit.verify(prep, wrong_word)

    wrong_line = spoof(
        "source_line_open", lines[0], api.F.source_line_open.v(lines[1]),
    )
    with pytest.raises(recovery_audit.AuditError, match="line|opening|duplicate"):
        recovery_audit.verify(prep, wrong_line)

    readable = next(w for w in words if api.F.otype.v(w) == "word")
    sign = api.L.d(readable, otype="sign")[0]
    corrupted_body = spoof("srcxml", sign, "FORGED" + (api.F.srcxml.v(sign) or ""))
    with pytest.raises(recovery_audit.AuditError, match="source|body|sign"):
        recovery_audit.verify(prep, corrupted_body)


def test_external_gate_requires_authenticated_and_reviewed_source(tmp_path):
    from tlhdig import recovery_audit

    rel = "CTH 820_XML_TLH/KUB 48.15.xml"
    prep, api = _loaded(tmp_path, rel)
    tampered = replace(
        prep, original_bytes=prep.original_bytes + b"source drift",
    )
    with pytest.raises((recovery.SignatureDrift, recovery_audit.AuditError)):
        recovery_audit.verify(tampered, api)
    # The corpus contains many documents outside the reviewed structural
    # recovery allowlist. Choose one by policy membership rather than assuming
    # a particular real XML file is unreviewed (CTH 394 is in fact reviewed).
    reviewed = set(prepared_source.reviewed_paths())
    unreviewed = next(
        p.relative_to(CORPUS).as_posix()
        for p in CORPUS.rglob("*.xml")
        if p.relative_to(CORPUS).as_posix() not in reviewed
    )
    assert (CORPUS / unreviewed).is_file()
    with pytest.raises(prepared_source.NotReviewed):
        prepared_source.prepare(unreviewed)
