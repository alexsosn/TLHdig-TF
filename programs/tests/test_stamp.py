"""The BUILD-COMPLETE stamp.

The release gate used to ask "does a stamp file exist?".  build.py rebuilds in place, so
a stamp written for build A survived an unverified build B and publish accepted it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import stamp


def dataset(tmp_path: Path, body: str = "1\ta\n") -> Path:
    d = tmp_path / "tf"
    d.mkdir()
    (d / "otype.tf").write_text("@node\n\n1\tsign\n", encoding="utf8")
    (d / "sym.tf").write_text("@node\n\n" + body, encoding="utf8")
    return d


def test_missing_stamp_is_a_problem(tmp_path):
    d = dataset(tmp_path)
    assert "missing" in stamp.check(d)


def test_fresh_stamp_verifies(tmp_path):
    d = dataset(tmp_path)
    stamp.write(d, "0.3", "0.1.0")
    assert stamp.check(d) is None


def test_stamp_does_not_certify_a_later_rebuild(tmp_path):
    """The actual bug: verify build A, rebuild as B, publish accepts the stale stamp."""
    d = dataset(tmp_path, "1\ta\n")
    stamp.write(d, "0.3", "0.1.0")
    (d / "sym.tf").write_text("@node\n\n1\tCHANGED\n", encoding="utf8")   # build B
    problem = stamp.check(d)
    assert problem and "rebuilt after it was verified" in problem


def test_added_feature_file_invalidates_the_stamp(tmp_path):
    d = dataset(tmp_path)
    stamp.write(d, "0.3", "0.1.0")
    (d / "extra.tf").write_text("@node\n\n1\tx\n", encoding="utf8")
    assert stamp.check(d) is not None


def test_legacy_stamp_without_a_digest_is_refused(tmp_path):
    d = dataset(tmp_path)
    (d / stamp.STAMP).write_text("sourceVersion=0.3\ntfVersion=0.1.0\n", encoding="utf8")
    assert "predates content binding" in stamp.check(d)
