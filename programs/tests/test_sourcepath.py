"""Contract tests for TLHdig source-path parsing.

The source path is provenance and a release-scoped record identifier. Parsing must
extract structure demonstrated by the path itself without rewriting that identifier or
inventing semantic labels from project codes or intermediate directory names.
"""
import sys
from dataclasses import fields
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import paths as corpus_paths
from tlhdig import sourcepath


BETA03_PROJECT_CODES = {
    "ARINNA", "BESRIT", "GEBET", "HAnn", "HDivT", "HFR", "KULTINV",
    "LUWGR", "MYTH", "PTAC", "SVH", "TLH", "luw",
}


def test_beta03_path_extracts_cth_project_and_filename():
    raw = "CTH 18_XML_HAnn/KUB 26.71.xml"
    got = sourcepath.parse(raw)

    assert got.parse_ok
    assert got.src_file == raw
    assert got.cth == "18"
    assert got.project == "HAnn"
    assert got.source_subdir == ""
    assert got.source_stem == "KUB 26.71"
    assert got.parse_error == ""


def test_nested_shard_is_preserved_verbatim():
    raw = "CTH 670_XML_HFR/CTH 670-0076-0100/11_c.xml"
    got = sourcepath.parse(raw)

    assert got.parse_ok
    assert got.cth == "670"
    assert got.project == "HFR"
    assert got.source_subdir == "CTH 670-0076-0100"
    assert got.source_stem == "11_c"


def test_beta02_legacy_grammar_does_not_infer_project_from_subdir():
    raw = "CTH 241_XML/CTH 241.I_PTAC/KUB 1.1.xml"
    got = sourcepath.parse(raw)

    assert got.parse_ok
    assert got.cth == "241"
    assert got.project == ""
    assert got.source_subdir == "CTH 241.I_PTAC"
    assert got.source_stem == "KUB 1.1"


def test_unknown_future_project_is_structurally_valid():
    got = sourcepath.parse("CTH 1_XML_FUTURE/Foo.xml")

    assert got.parse_ok
    assert got.project == "FUTURE"


def test_parser_contract_contains_only_path_derived_fields():
    assert {field.name for field in fields(sourcepath.SourcePath)} == {
        "src_file", "cth", "project", "source_subdir", "source_stem",
        "parse_ok", "parse_error",
    }
    assert not hasattr(sourcepath, "PROJECT_NAMES")


def test_malformed_beta02_cth_directory_is_an_explicit_parse_failure():
    raw = "CTH 473_XM/KBo 27.130.xml"
    got = sourcepath.parse(raw)

    assert not got.parse_ok
    assert got.src_file == raw
    assert got.cth == ""
    assert got.project == ""
    assert got.source_stem == "KBo 27.130"
    assert got.parse_error == "invalid_top_directory"


def test_path_shape_failures_are_named_not_silently_normalized():
    cases = {
        "/CTH 1_XML_TLH/Foo.xml": "absolute_path",
        "CTH 1_XML_TLH/../Foo.xml": "path_traversal",
        r"CTH 1_XML_TLH\\Foo.xml": "non_posix_separator",
        "CTH 1_XML_TLH//Foo.xml": "empty_path_component",
        "CTH foo_XML_TLH/Foo.xml": "invalid_top_directory",
        "CTH 1_XML_TLH/Foo.txt": "not_xml",
        "Foo.xml": "missing_top_directory",
        "CTH 1_XML_TLH/": "missing_filename",
    }
    for raw, reason in cases.items():
        got = sourcepath.parse(raw)
        assert not got.parse_ok, raw
        assert got.src_file == raw
        assert got.parse_error == reason, raw


def test_every_beta03_corpus_path_matches_the_parser_contract():
    bad = []
    projects = set()
    for path in corpus_paths.corpus_files():
        raw = corpus_paths.rel(path)
        got = sourcepath.parse(raw)
        if not got.parse_ok:
            bad.append((raw, got.parse_error))
            continue
        assert got.src_file == raw
        projects.add(got.project)

    assert not bad, bad[:10]
    assert projects == BETA03_PROJECT_CODES
