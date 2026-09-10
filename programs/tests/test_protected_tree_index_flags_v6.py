"""Review-driven RED: Git index flags must not hide protected working bytes."""
from __future__ import annotations

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


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    (root / "programs").mkdir(parents=True)
    _git(root, "init")
    _git(root, "config", "user.name", "Index Flag Fixture")
    _git(root, "config", "user.email", "fixture@example.invalid")
    target = root / "programs" / "checker.py"
    target.write_text("VALUE = 1\n", encoding="utf8")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "initial protected tree")
    return root, target


@pytest.mark.parametrize(
    "flag",
    ("--assume-unchanged", "--skip-worktree"),
)
def test_index_flags_cannot_hide_modified_protected_working_bytes(tmp_path, flag):
    root, target = _repo(tmp_path)
    protected_tree.identity(root)

    _git(root, "update-index", flag, "programs/checker.py")
    target.write_text("VALUE = 2\n", encoding="utf8")

    # Both flags can make ordinary `git status` / `git diff` report a clean tree.
    assert _git(root, "status", "--porcelain") == ""
    assert _git(root, "diff", "--name-only", "HEAD", "--") == ""

    with pytest.raises(protected_tree.ProtectedTreeError, match="index|flag|protected"):
        protected_tree.identity(root)
