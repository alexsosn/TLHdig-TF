"""Adversarial RED: ignored bytecode must not bypass release-v6 freshness."""
from __future__ import annotations

import importlib
import importlib.util
import marshal
from pathlib import Path
import struct
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


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.name", "Forged Pycache Fixture")
    _git(root, "config", "user.email", "forged-pycache@example.invalid")
    for rel, text in (
        ("programs/checker.py", "VALUE = 1\n"),
        ("corpus/a.xml", "<a/>\n"),
        ("app/config.yaml", "version: one\n"),
        ("requirements.txt", "text-fabric==13.1.0\n"),
        (".github/workflows/certify-dataset.yml", "name: certify\n"),
        (".gitignore", "__pycache__/\n*.py[cod]\n"),
    ):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf8")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "fixture")
    return root


def _forge_timestamp_cache(source: Path) -> Path:
    """Write importable bytecode whose code differs while source metadata still matches."""
    cache = Path(importlib.util.cache_from_source(str(source)))
    cache.parent.mkdir(parents=True, exist_ok=True)
    stat = source.stat()
    # Keep the replacement source text the same byte length as the tracked source so a
    # normal timestamp/size cache validation accepts it.
    forged = compile(
        "VALUE = 9\n",
        str(source),
        "exec",
        dont_inherit=True,
        optimize=0,
    )
    cache.write_bytes(
        importlib.util.MAGIC_NUMBER
        + struct.pack("<I", 0)
        + struct.pack("<II", int(stat.st_mtime), stat.st_size)
        + marshal.dumps(forged)
    )
    return cache


def test_importable_forged_pycache_makes_protected_identity_fail_closed(tmp_path):
    root = _repo(tmp_path)
    baseline = protected_tree.identity(root)
    source = root / "programs" / "checker.py"
    cache = _forge_timestamp_cache(source)
    assert _git(root, "check-ignore", cache.relative_to(root).as_posix())

    sys.path.insert(0, str(root / "programs"))
    sys.modules.pop("checker", None)
    try:
        module = importlib.import_module("checker")
        assert module.VALUE == 9, "fixture must prove CPython executed the forged cache"
    finally:
        sys.modules.pop("checker", None)
        sys.path.pop(0)

    # The tracked tree has not moved. Accepting the same identity now would mean ignored
    # executable bytes can alter certification without altering its recorded trust root.
    with pytest.raises(protected_tree.ProtectedTreeError, match="dirty|protected|cache"):
        protected_tree.identity(root)

    assert baseline["digest"].startswith("sha256:")
