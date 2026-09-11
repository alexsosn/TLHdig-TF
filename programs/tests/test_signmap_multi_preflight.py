"""Regression contract for destructive build preflight (#124)."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build as build_program


def _write(path: Path, text: str = "old\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf8")
    return path


def test_missing_signmap_multi_fails_before_current_output_reset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "repo"
    programs = root / "programs"
    corpus = root / "corpus"
    corpus.mkdir(parents=True)

    patches = _write(programs / "patches.yaml", "{}\n")
    _write(programs / "corpus.sha256", "synthetic\n")
    _write(programs / "excluded.txt", "# none\n")
    # Deliberately do not create programs/signmap-multi.tsv.

    version = "9.9.9"
    main = root / "tf" / version
    old_manifest = _write(main / "BUILD-MANIFEST.json", "old validated artifact\n")

    monkeypatch.setattr(build_program, "ROOT", root)
    monkeypatch.setattr(build_program, "CORPUS", corpus)
    monkeypatch.setattr(build_program, "PATCHES", patches)
    monkeypatch.setattr(build_program, "TF_VERSION", version)
    monkeypatch.setattr(build_program, "PROVENANCE_DIR", "tf-provenance")
    monkeypatch.setattr(build_program, "corpus_files", lambda: [])
    monkeypatch.setattr(build_program.corpusid, "read_manifest", lambda _path: {})
    monkeypatch.setattr(build_program.corpusid, "verify", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        build_program.convert,
        "build",
        lambda *_args, **_kwargs: pytest.fail(
            "converter must not run when signmap-multi.tsv is missing"
        ),
    )

    assert build_program.main() == 1
    assert old_manifest.read_text(encoding="utf8") == "old validated artifact\n"
