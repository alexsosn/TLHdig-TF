"""Regression tests for the TF 0.2.1 release-certification helper."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from check_docid_raw_release import assert_non_target_tf_data_unchanged


def _tf(path: Path, body: str = "1\tvalue\n") -> None:
    path.write_text("@node\n@valueType=str\n\n" + body, encoding="utf8")


def test_certifier_ignores_text_fabric_binary_cache_directory(tmp_path):
    old = tmp_path / "old"
    new = tmp_path / "new"
    old.mkdir()
    new.mkdir()
    _tf(old / "feature.tf")
    _tf(new / "feature.tf")
    (new / ".tf").mkdir()

    # Text-Fabric creates .tf/ as a derived binary cache after loading a fresh build.
    # It is not a serialized feature and must not look like schema/data drift.
    assert_non_target_tf_data_unchanged(old, new)
