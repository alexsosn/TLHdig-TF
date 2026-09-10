"""Adversarial workflow-family coverage for release-v6 protected identity."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import protected_tree

ROOT = Path(__file__).resolve().parents[2]
CERTIFY_WORKFLOW = ROOT / ".github" / "workflows" / "certify-dataset.yml"


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


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.name", "YAML Workflow Fixture")
    _git(root, "config", "user.email", "yaml@example.invalid")
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
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "fixture")
    return root


def test_release_workflow_families_change_protected_identity(tmp_path):
    """All write-capable temporary release workflow families must be cryptographically bound."""
    root = _repo(tmp_path)
    before = protected_tree.identity(root)

    for name in (
        "build-final-99.yaml",
        "finalize-issue99.yaml",
        "materialize-release-99.yaml",
        "sync-release-99.yaml",
    ):
        path = root / ".github" / "workflows" / name
        path.write_text("name: release mutation\n", encoding="utf8")
        _git(root, "add", path.relative_to(root).as_posix())
        _git(root, "commit", "-m", f"add {name}")
        after = protected_tree.identity(root)
        assert after["digest"] != before["digest"], name
        before = after


def test_canonical_certifier_retriggers_for_release_workflow_families():
    text = CERTIFY_WORKFLOW.read_text(encoding="utf8")
    for stem in (
        "build-final-*",
        "finalize-issue*",
        "materialize-*",
        "sync-*",
    ):
        for suffix in (".yml", ".yaml"):
            pattern = f'.github/workflows/{stem}{suffix}'
            assert pattern in text, pattern
