"""Integration boundary for repository-aware release-v6 stamp verification (#69)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_stamp
from tlhdig import stamp


def test_check_stamp_passes_repository_root_to_full_verifier(monkeypatch, tmp_path):
    """The canonical CLI must supply the Git checkout used by release-v6 freshness."""
    root = tmp_path / "repo"
    out = root / "tf" / "9.9.9"
    out.mkdir(parents=True)

    monkeypatch.setattr(check_stamp, "ROOT", root)
    monkeypatch.setattr(check_stamp, "TF_VERSION", "9.9.9")

    seen = {}

    def fake_check(path, *, require_full=False, repo_root=None):
        seen.update(path=path, require_full=require_full, repo_root=repo_root)
        return None

    monkeypatch.setattr(stamp, "check", fake_check)
    monkeypatch.setattr(
        stamp,
        "read",
        lambda _path: {"certification": "sha256:test", "features": "1", "digest": "sha256:test"},
    )

    assert check_stamp.main(["--require-full"]) == 0
    assert seen == {"path": out, "require_full": True, "repo_root": root}
