"""Compacting .tf node features (TF file format: a node spec denotes a *set*).

`1-3,5-10,15` is a legal node spec, so every node sharing a value can be written on
one line.  TF's writer emits one line per node; for this corpus that costs 124 MB on
`morph.tf` alone, where a single 300-character alternative-set string is repeated
231,131 times.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import compact

HEADER = "@node\n@valueType=str\n@description=x\n\n"


def test_groups_identical_values(tmp_path):
    f = tmp_path / "a.tf"
    f.write_text(HEADER + "1\tX\n2\tX\n3\tY\n4\tX\n", encoding="utf8")
    compact.compact_file(f)
    body = f.read_text(encoding="utf8").split("\n\n", 1)[1]
    lines = [l for l in body.strip().split("\n")]
    assert len(lines) == 2
    assert "1-2,4\tX" in lines
    assert "3\tY" in lines


def test_uses_ranges_for_runs(tmp_path):
    f = tmp_path / "a.tf"
    f.write_text(HEADER + "".join(f"{i}\tX\n" for i in range(1, 6)), encoding="utf8")
    compact.compact_file(f)
    assert "1-5\tX" in f.read_text(encoding="utf8")


def test_preserves_values_exactly(tmp_path):
    f = tmp_path / "a.tf"
    original = HEADER + "1\ta\\tb\n2\tc\n3\ta\\tb\n"
    f.write_text(original, encoding="utf8")
    before = compact.read_values(f)
    compact.compact_file(f)
    assert compact.read_values(f) == before


def test_header_is_untouched(tmp_path):
    f = tmp_path / "a.tf"
    f.write_text(HEADER + "1\tX\n", encoding="utf8")
    compact.compact_file(f)
    assert f.read_text(encoding="utf8").startswith(HEADER)


def test_edge_features_are_left_alone(tmp_path):
    """Edge lines have two node specs; grouping them is not this tool's job."""
    f = tmp_path / "e.tf"
    body = "@edge\n@valueType=str\n\n1\t2\tX\n3\t4\tX\n"
    f.write_text(body, encoding="utf8")
    assert compact.compact_file(f) is False
    assert f.read_text(encoding="utf8") == body


def test_ignores_the_tf_cache_directory(tmp_path):
    """TF keeps its binary cache in a directory named `.tf`, which the glob matches."""
    (tmp_path / ".tf").mkdir()
    (tmp_path / "a.tf").write_text(HEADER + "1\tX\n", encoding="utf8")
    got = compact.compact_dir(tmp_path)
    assert [n for n, _, _ in got] == ["a.tf"]


# ------------------------------------------------- TF's optimised (implicit) format

def test_reads_implicit_node_numbers(tmp_path):
    """A line with no tab means node = implicit_node, which advances to
    max(nodes) + 1 after every line (tf/core/data.py:_readDataTf)."""
    f = tmp_path / "a.tf"
    f.write_text(HEADER + "X\nY\n5\tZ\nW\n", encoding="utf8")
    assert compact.read_values(f) == {1: "X", 2: "Y", 5: "Z", 6: "W"}


def test_value_containing_a_dash_is_not_a_node_spec(tmp_path):
    """`after.tf` legitimately holds the value '-' on a tab-less line."""
    f = tmp_path / "a.tf"
    f.write_text(HEADER + "-\n-\n", encoding="utf8")
    assert compact.read_values(f) == {1: "-", 2: "-"}


def test_compacting_an_implicit_file_preserves_values(tmp_path):
    f = tmp_path / "a.tf"
    f.write_text(HEADER + "X\nY\nX\n9\tY\nX\n", encoding="utf8")
    before = compact.read_values(f)
    compact.compact_file(f)
    assert compact.read_values(f) == before
    assert "1,3,10\tX" in f.read_text(encoding="utf8")


def test_blank_line_is_a_value_not_a_skip(tmp_path):
    """TF writes an empty value as a blank line, and its reader advances the implicit
    node on it like any other line (tf/core/data.py:_readDataTf).

    Skipping blank lines desynchronised the counter, so every value after the first
    empty one was rewritten onto the wrong node. `<sGr>UR.SAG</sGr>` shipped as
    `<sGr>UR-SAG</sGr>`, and 5 of 6 `after` values in a six-sign document were wrong.
    """
    f = tmp_path / "after.tf"
    f.write_text("@node\n@valueType=str\n\n-\n\n-\n\n.\n\n", encoding="utf8")
    assert compact.read_values(f) == {1: "-", 2: "", 3: "-", 4: "", 5: ".", 6: ""}


def test_compaction_preserves_every_value_including_empties(tmp_path):
    f = tmp_path / "after.tf"
    f.write_text("@node\n@valueType=str\n\n-\n\n-\n\n.\n\n", encoding="utf8")
    before = compact.read_values(f)
    compact.compact_file(f)
    assert compact.read_values(f) == before


def test_trailing_newline_does_not_invent_a_node(tmp_path):
    """`for line in fh` yields no line after the final newline; split("\\n") does."""
    f = tmp_path / "x.tf"
    f.write_text("@node\n@valueType=str\n\na\nb\n", encoding="utf8")
    assert compact.read_values(f) == {1: "a", 2: "b"}


def test_leading_blank_line_is_node_one(tmp_path):
    f = tmp_path / "x.tf"
    f.write_text("@node\n@valueType=str\n\n\nb\n", encoding="utf8")
    assert compact.read_values(f) == {1: "", 2: "b"}


def test_explicit_specs_still_reset_the_implicit_node(tmp_path):
    f = tmp_path / "x.tf"
    f.write_text("@node\n@valueType=str\n\n5\tv\n\nw\n", encoding="utf8")
    # node 5 = "v", then the blank line is node 6 = "", then node 7 = "w"
    assert compact.read_values(f) == {5: "v", 6: "", 7: "w"}
