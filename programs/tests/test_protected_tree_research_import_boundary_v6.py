"""Review-driven RED: imported research-named programs are certification inputs."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

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


def _commit(root: Path, message: str) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-m", message)


def test_imported_research_named_program_cannot_escape_protected_identity(tmp_path):
    """A filename convention must not let executable imported code escape freshness."""
    root = tmp_path / "repo"
    (root / "programs").mkdir(parents=True)
    _git(root, "init")
    _git(root, "config", "user.name", "Import Boundary Fixture")
    _git(root, "config", "user.email", "fixture@example.invalid")

    (root / "programs" / "checker.py").write_text(
        "import research_probe\nVALUE = research_probe.VALUE\n", encoding="utf8"
    )
    probe = root / "programs" / "research_probe.py"
    probe.write_text("VALUE = 1\n", encoding="utf8")
    _commit(root, "initial protected executable tree")

    before = protected_tree.identity(root)["digest"]
    probe.write_text("VALUE = 2\n", encoding="utf8")
    _commit(root, "change imported research-named executable")
    after = protected_tree.identity(root)["digest"]

    assert after != before, (
        "an executable module imported by protected code must not escape release "
        "freshness merely because its filename starts with research_"
    )
