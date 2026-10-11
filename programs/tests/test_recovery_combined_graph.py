"""#150 RED: externally verify original AOxml in a multi-document loaded TF.

Four immutable, signed source-event pilots in the SAME real serialized graph.
The source opening byte offsets are local to each document, never global IDs.
"""
from types import SimpleNamespace

import pytest

from tlhdig import convert, prepared_source, recovery, repair
from tlhdig.paths import CORPUS, PATCHES

PILOTS = (
    ("CTH 209_XML_TLH/KBo 12.55.xml", 14, 7),
    ("CTH 448_XML_BESRIT/KBo 10.36.xml", 160, 59),
    ("CTH 820_XML_TLH/KUB 48.15.xml", 37, 17),
    ("CTH 832_XML_TLH/UBT 70.xml", 5, 5),
)


@pytest.fixture(scope="module")
def combined_api(tmp_path_factory):
    # The source corpus, TF API, and all negative controls are read-only.
    # Share this real combined serialization across tests rather than
    # rebuilding the identical four sources six times in every CI shard.
    temp = tmp_path_factory.mktemp("combined-tf-source")
    paths = tuple(rel for rel, _words, _lines in PILOTS)
    assert set(paths) == set(convert.VERIFIED_RECOVERY_PILOTS)
    api = convert.build(
        CORPUS, temp / "combined-tf",
        files=[CORPUS / rel for rel in paths],
        patches=repair.read_manifest(PATCHES),
        terminal_recovery_paths=paths,
    )
    assert api is not None
    return api


@pytest.mark.parametrize("rel,expected_words,expected_lines", PILOTS)
def test_original_source_verified_in_combined_loaded_graph(
    combined_api, rel, expected_words, expected_lines,
):
    from tlhdig import recovery_audit

    api = combined_api
    assert len(api.F.otype.s("document")) == 4
    prepared = prepared_source.prepare(rel)
    assert len(recovery.original_opening_sequences(prepared)[0]) == expected_words

    # Existing strict singleton checker must not silently accept a combined
    # corpus by treating local source offsets as globally unique IDs.
    with pytest.raises(recovery_audit.AuditError, match="one source document"):
        recovery_audit.verify(prepared, api)
    result = recovery_audit.verify_in_corpus(prepared, api)
    assert result.source == rel
    assert result.words == expected_words
    assert result.lines == expected_lines


def test_combined_gate_rejects_duplicate_original_source_document_identity(
    combined_api,
):
    from tlhdig import recovery_audit

    api = combined_api
    target = prepared_source.prepare(PILOTS[0][0])
    docs = tuple(api.F.otype.s("document"))
    own = next(d for d in docs if api.F.src_file.v(d) == target.path)
    other = next(d for d in docs if d != own)

    class SpoofSrcFile:
        def v(self, node):
            return target.path if node == other else api.F.src_file.v(node)

    class SpoofF:
        def __getattr__(self, feature):
            return SpoofSrcFile() if feature == "src_file" else getattr(api.F, feature)

    forged = SimpleNamespace(F=SpoofF(), E=api.E, L=api.L, Fall=api.Fall)
    with pytest.raises(recovery_audit.AuditError, match="document|duplicate|ambiguous"):
        recovery_audit.verify_in_corpus(target, forged)


def test_combined_gate_rejects_foreign_word_source_opening_in_same_document(
    combined_api,
):
    from tlhdig import recovery_audit

    api = combined_api
    target = prepared_source.prepare(PILOTS[0][0])
    docs = tuple(api.F.otype.s("document"))
    own = next(d for d in docs if api.F.src_file.v(d) == target.path)
    other = next(d for d in docs if d != own)
    own_words = tuple(api.L.d(own, otype="word"))
    foreign_words = tuple(api.L.d(other, otype="word"))
    assert own_words and foreign_words
    expected_source_openers = set(recovery.original_opening_sequences(target)[0])
    foreign_opener = next(
        api.F.source_word_open.v(w)
        for w in foreign_words
        if api.F.source_word_open.v(w) not in expected_source_openers
    )
    replace_word = own_words[0]

    class SpoofSourceWordOpen:
        def v(self, node):
            if node == replace_word:
                return foreign_opener
            return api.F.source_word_open.v(node)

    class SpoofF:
        def __getattr__(self, feature):
            return (
                SpoofSourceWordOpen() if feature == "source_word_open"
                else getattr(api.F, feature)
            )

    forged = SimpleNamespace(F=SpoofF(), E=api.E, L=api.L, Fall=api.Fall)
    with pytest.raises(recovery_audit.AuditError, match="word|opening|source"):
        recovery_audit.verify_in_corpus(target, forged)


def test_structure_census_uses_source_openers_for_real_recovered_documents(combined_api):
    """RED: UBT 70's literal fifth word must not be dropped by patched nesting."""
    from tlhdig import structure
    from tlhdig.paths import ENCRYPTED, rel

    paths = tuple(CORPUS / name for name, _words, _lines in PILOTS)
    patches = repair.read_manifest(PATCHES)
    src, nfiles = structure.count_corpus(
        paths, patches, ENCRYPTED, rel,
        terminal_recovery_paths=convert.VERIFIED_RECOVERY_PILOTS,
    )
    api = combined_api
    assert nfiles == 4
    assert src["word"] == len(api.F.otype.s("word")) + len(api.F.otype.s("layout")) == 216
    assert src["line"] == len(api.F.otype.s("line")) == 88
    for ntype in ("colon", "note"):
        assert src[ntype] == len(api.F.otype.s(ntype))

    # Historical full-repair ancestry must remain the default for callers
    # not selecting this opt-in. It should not certify the recovered graph.
    old, old_docs = structure.count_corpus(paths, patches, ENCRYPTED, rel)
    assert old_docs == 4
    assert old["word"] != src["word"]


def test_structure_census_rejects_missing_signed_source_or_patch():
    """RED: no source-selected recovery counts without exact corpus evidence."""
    from tlhdig import structure
    from tlhdig.paths import ENCRYPTED, rel

    files = tuple(CORPUS / name for name, _words, _lines in PILOTS)
    patches = repair.read_manifest(PATCHES)

    with pytest.raises((ValueError, OSError), match="pilot|source|missing"):
        structure.count_corpus(
            files[:-1], patches, ENCRYPTED, rel,
            terminal_recovery_paths=convert.VERIFIED_RECOVERY_PILOTS,
        )

    altered = dict(patches)
    altered.pop(PILOTS[0][0])
    with pytest.raises((ValueError, OSError), match="manifest|pilot|source"):
        structure.count_corpus(
            files, altered, ENCRYPTED, rel,
            terminal_recovery_paths=convert.VERIFIED_RECOVERY_PILOTS,
        )
