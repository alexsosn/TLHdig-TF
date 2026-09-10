"""Review-driven RED: Git clean filters must not hide protected working bytes."""
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


def test_clean_filter_cannot_hide_modified_protected_working_bytes(tmp_path):
    root = tmp_path / "repo"
    (root / "programs").mkdir(parents=True)
    _git(root, "init")
    _git(root, "config", "user.name", "Clean Filter Fixture")
    _git(root, "config", "user.email", "fixture@example.invalid")

    target = root / "programs" / "checker.py"
    target.write_text("VALUE = 1\n", encoding="utf8")
    (root / ".gitattributes").write_text(
        "programs/checker.py filter=mask\n", encoding="utf8"
    )
    _git(root, "config", "filter.mask.clean", "sed 's/VALUE = 2/VALUE = 1/'")
    _git(root, "config", "filter.mask.smudge", "cat")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "initial protected tree")

    protected_tree.identity(root)
    target.write_text("VALUE = 2\n", encoding="utf8")

    # Git's configured clean filter deliberately masks this content change.
    assert _git(root, "status", "--porcelain") == ""
    assert _git(root, "diff", "--name-only", "HEAD", "--") == ""

    with pytest.raises(protected_tree.ProtectedTreeError, match="protected|worktree|content"):
        protected_tree.identity(root)
