"""Adversarial RED for ignored untracked files in the release-v6 trust boundary."""
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


def test_ignored_untracked_protected_source_fails_closed(tmp_path):
    """Git ignore rules must not be able to hide executable protected source.

    ``git ls-files --others --exclude-standard`` omits ignored files.  Because the
    freshness contract protects executable ``programs/**`` inputs, an ignored local
    Python file there must still make the protected identity unavailable; otherwise a
    certification run could execute bytes that are absent from its recorded Git tree.
    """
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.name", "Ignored Input Fixture")
    _git(root, "config", "user.email", "ignored@example.invalid")

    (root / "programs").mkdir()
    (root / "programs" / "checker.py").write_text("VALUE = 1\n", encoding="utf8")
    (root / "corpus").mkdir()
    (root / "corpus" / "a.xml").write_text("<a/>\n", encoding="utf8")
    (root / "app").mkdir()
    (root / "app" / "config.yaml").write_text("version: one\n", encoding="utf8")
    (root / "requirements.txt").write_text("text-fabric==13.1.0\n", encoding="utf8")
    workflows = root / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "certify-dataset.yml").write_text("name: certify\n", encoding="utf8")
    (root / ".gitignore").write_text("programs/local_override.py\n", encoding="utf8")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "fixture")

    baseline = protected_tree.identity(root)
    hidden = root / "programs" / "local_override.py"
    hidden.write_text("VALUE = 2\n", encoding="utf8")
    assert _git(root, "check-ignore", hidden.relative_to(root).as_posix())

    with pytest.raises(protected_tree.ProtectedTreeError, match="dirty|protected"):
        protected_tree.identity(root)

    # The tracked protected tree itself has not moved; accepting ``baseline`` here
    # would therefore prove the ignored local code was invisible to the freshness gate.
    assert baseline["digest"].startswith("sha256:")
