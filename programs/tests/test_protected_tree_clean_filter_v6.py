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


def _clean_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for rel, text in (
        ("programs/checker.py", "VALUE = 1\n"),
        ("corpus/a.xml", "<a/>\n"),
        ("app/config.yaml", "version: one\n"),
        ("requirements.txt", "text-fabric==13.1.0\n"),
        (".github/workflows/certify-dataset.yml", "name: certify\n"),
    ):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf8")
    _git(root, "init")
    _git(root, "config", "user.name", "Clean Filter Fixture")
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "initial protected tree")
    return root


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

    with pytest.raises(protected_tree.ProtectedTreeError, match="protected|filter|attribute|worktree"):
        protected_tree.identity(root)

    target.write_text("VALUE = 2\n", encoding="utf8")

    # Git's configured clean filter deliberately masks this content change.
    assert _git(root, "status", "--porcelain") == ""
    assert _git(root, "diff", "--name-only", "HEAD", "--") == ""

    with pytest.raises(protected_tree.ProtectedTreeError, match="protected|filter|attribute|worktree"):
        protected_tree.identity(root)


@pytest.mark.parametrize("driver", ["unspecified", "unset"])
def test_reserved_filter_names_cannot_masquerade_as_inactive_attributes(tmp_path, driver):
    """`check-attr` sentinel-looking values must not become an allow-list escape."""
    root = tmp_path / f"repo-{driver}"
    (root / "programs").mkdir(parents=True)
    _git(root, "init")
    _git(root, "config", "user.name", "Reserved Attribute Fixture")
    _git(root, "config", "user.email", "fixture@example.invalid")

    target = root / "programs" / "checker.py"
    target.write_text("VALUE = 1\n", encoding="utf8")
    (root / ".gitattributes").write_text(
        f"programs/checker.py filter={driver}\n", encoding="utf8"
    )
    _git(root, "config", f"filter.{driver}.clean", "sed 's/VALUE = 2/VALUE = 1/'")
    _git(root, "config", f"filter.{driver}.smudge", "cat")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "initial protected tree")
    target.write_text("VALUE = 2\n", encoding="utf8")

    assert _git(root, "status", "--porcelain") == ""
    assert _git(root, "diff", "--name-only", "HEAD", "--") == ""
    with pytest.raises(protected_tree.ProtectedTreeError, match="protected|filter|attribute"):
        protected_tree.identity(root)


def test_core_autocrlf_input_fails_closed_without_attributes(tmp_path):
    """Global/local Git conversion config is another content-transform channel.

    A release checkout must not rely only on path attributes: ``core.autocrlf=input``
    can normalize CRLF to LF on comparison/check-in even when no ``.gitattributes``
    rule applies. Reject the ambiguous Git view before trusting metadata-only
    cleanliness.
    """
    root = _clean_repo(tmp_path)
    _git(root, "config", "core.autocrlf", "input")
    assert _git(root, "config", "--get", "core.autocrlf") == "input"

    with pytest.raises(protected_tree.ProtectedTreeError, match="autocrlf|conversion|transform"):
        protected_tree.identity(root)


def test_clean_identity_does_not_rehash_protected_payload_bytes(tmp_path, monkeypatch):
    """Freshness stays cheap even when the protected corpus itself is large.

    Git object identities are the committed-content boundary. Ordinary clean-tree
    verification may inspect metadata/attributes, but must not reread every corpus,
    app, and program payload merely to rediscover the blob OIDs Git already records.
    """
    root = _clean_repo(tmp_path)
    protected_payloads = {
        root / "programs" / "checker.py",
        root / "corpus" / "a.xml",
        root / "app" / "config.yaml",
        root / "requirements.txt",
    }
    original = Path.read_bytes

    def refuse_payload_rehash(path: Path):
        if path in protected_payloads:
            raise AssertionError(f"identity reread protected payload: {path}")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", refuse_payload_rehash)
    assert protected_tree.identity(root)["digest"].startswith("sha256:")
