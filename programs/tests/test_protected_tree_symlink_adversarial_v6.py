"""Adversarial release-v6 boundary: protected tracked paths must be regular files."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import protected_tree


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def _base_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.name", "Protected Entry Fixture")
    _git(root, "config", "user.email", "protected-entry@example.invalid")
    for rel, text in (
        ("corpus/a.xml", "<a/>\n"),
        ("app/config.yaml", "version: one\n"),
        ("requirements.txt", "text-fabric==13.1.0\n"),
        (".github/workflows/certify-dataset.yml", "name: certify\n"),
    ):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf8")
    return root


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="platform has no symlink support")
def test_protected_tracked_symlink_fails_closed(tmp_path):
    root = _base_repo(tmp_path)
    outside = tmp_path / "outside.py"
    outside.write_text("VALUE = 1\n", encoding="utf8")
    programs = root / "programs"
    programs.mkdir()
    (programs / "checker.py").symlink_to(outside)
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "fixture with protected external symlink")

    mode = _git(root, "ls-tree", "HEAD", "programs/checker.py").split()[0]
    assert mode == "120000", "fixture must exercise a real Git symlink"

    # Hashing the link target string is not enough: the target bytes live outside the
    # protected Git tree and can change without changing HEAD.
    with pytest.raises(protected_tree.ProtectedTreeError, match="regular|symlink|mode"):
        protected_tree.identity(root)


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="platform has no symlink support")
def test_protected_root_directory_replaced_by_symlink_fails_closed(tmp_path):
    """The profile root itself is a trust boundary, not only its descendants.

    If ``programs`` is a tracked symlink to an external directory, Git has no
    ``programs/...`` child entries to hash.  Certification must reject the root symlink
    rather than execute mutable bytes outside the recorded protected tree.
    """
    root = _base_repo(tmp_path)
    outside = tmp_path / "outside-programs"
    outside.mkdir()
    (outside / "release_check.py").write_text("VALUE = 1\n", encoding="utf8")
    (root / "programs").symlink_to(outside, target_is_directory=True)
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "fixture with protected root symlink")

    mode = _git(root, "ls-tree", "HEAD", "programs").split()[0]
    assert mode == "120000", "fixture must exercise a tracked protected-root symlink"

    with pytest.raises(protected_tree.ProtectedTreeError, match="regular|symlink|mode"):
        protected_tree.identity(root)


@pytest.mark.skipif(os.name == "nt", reason="executable-bit fixture is POSIX-specific")
def test_protected_regular_executable_file_remains_valid(tmp_path):
    root = _base_repo(tmp_path)
    checker = root / "programs" / "checker.py"
    checker.parent.mkdir()
    checker.write_text("VALUE = 1\n", encoding="utf8")
    checker.chmod(0o755)
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "fixture with regular executable")

    mode = _git(root, "ls-tree", "HEAD", "programs/checker.py").split()[0]
    assert mode == "100755"
    assert protected_tree.identity(root)["digest"].startswith("sha256:")
