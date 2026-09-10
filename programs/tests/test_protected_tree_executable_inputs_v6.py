"""Adversarial RED for executable inputs accidentally excluded by release-v6."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import protected_tree

ROOT = Path(__file__).resolve().parents[2]
CERTIFY_WORKFLOW = ROOT / ".github" / "workflows" / "certify-dataset.yml"
PLAN = ROOT / "docs" / "plan-release-certification-freshness.md"


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.name", "Executable Input Fixture")
    _git(root, "config", "user.email", "exec-input@example.invalid")
    for rel, text in (
        ("programs/checker.py", "VALUE = 1\n"),
        ("programs/shard.txt", "a.xml\trepaired\n"),
        ("programs/research_weblink_ids.py", "VALUE = 1\n"),
        ("programs/tests/test_shard.py", "# reads shard.txt\n"),
        ("programs/tests/test_tlhdig_weblink.py", "# imports research_weblink_ids\n"),
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


def test_shard_manifest_changes_protected_identity(tmp_path):
    """The 91-document adversarial shard is executable test input, not research metadata."""
    root = _repo(tmp_path)
    before = protected_tree.identity(root)
    path = root / "programs" / "shard.txt"
    path.write_text("a.xml\tchanged-coverage\n", encoding="utf8")
    _git(root, "add", "programs/shard.txt")
    _git(root, "commit", "-m", "change integration shard")
    after = protected_tree.identity(root)
    assert after["digest"] != before["digest"]


def test_weblink_safety_program_changes_protected_identity(tmp_path):
    """A research-named module imported/executed by protected CI must remain protected."""
    root = _repo(tmp_path)
    before = protected_tree.identity(root)
    path = root / "programs" / "research_weblink_ids.py"
    path.write_text("VALUE = 2\n", encoding="utf8")
    _git(root, "add", "programs/research_weblink_ids.py")
    _git(root, "commit", "-m", "change weblink safety gate")
    after = protected_tree.identity(root)
    assert after["digest"] != before["digest"]


def test_certifier_retriggers_for_executable_inputs_hidden_by_broad_exclusions():
    text = CERTIFY_WORKFLOW.read_text(encoding="utf8")
    # The hardened workflow now includes every programs/** path, so the old
    # exclusion/re-inclusion ordering assertion is obsolete.  Assert the stronger
    # invariant directly: no filename convention can suppress a program input.
    assert 'programs/**' in text
    assert '!programs/shard.txt' not in text
    assert '!programs/research_*.py' not in text


def test_plan_records_shard_manifest_as_protected_executable_input():
    text = PLAN.read_text(encoding="utf8")
    assert "`programs/shard.txt` retain narrow development-evidence exclusions" not in text
    assert "`programs/shard.txt` if retained solely as research sampling metadata" not in text
    assert "`programs/shard.txt` is protected" in text
