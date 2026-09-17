"""#126 RED contract: reject unusable compound maps before destructive reset."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build as build_program
from tlhdig import cuneiform


def _write(path: Path, text: str = "old\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf8")
    return path


def _configure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, map_text: str
) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    programs = root / "programs"
    corpus = root / "corpus"
    corpus.mkdir(parents=True)

    patches = _write(programs / "patches.yaml", "{}\n")
    _write(programs / "corpus.sha256", "synthetic\n")
    _write(programs / "excluded.txt", "# none\n")
    _write(programs / "signmap-multi.tsv", map_text)

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
            "converter must not run when signmap-multi.tsv is unusable"
        ),
    )
    return old_manifest, programs / "signmap-multi.tsv"


@pytest.mark.parametrize(
    "map_text",
    [
        "# comments only\n",
        "a\tX\n",  # row load_multi() silently ignores: not a multi-codepoint cuneiform sequence
        "a\t𒀀𒀀\na\t𒀁𒀁\n",  # duplicate reading currently overwrites silently
    ],
    ids=["comment-only", "unusable-row", "duplicate-reading"],
)
def test_unusable_present_map_fails_before_reset_and_preserves_previous_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, map_text: str
) -> None:
    old_manifest, _map = _configure(monkeypatch, tmp_path, map_text)

    assert build_program.main() == 1
    assert old_manifest.read_text(encoding="utf8") == "old validated artifact\n"


def test_validate_multi_exposes_loader_facing_diagnostics(tmp_path: Path) -> None:
    validator = getattr(cuneiform, "validate_multi", None)
    assert callable(validator), "#126 requires a strict diagnostic helper beside load_multi()"

    valid = _write(tmp_path / "valid.tsv", "a\t𒀀𒀀\n")
    assert validator(valid) == []

    empty = _write(tmp_path / "empty.tsv", "# comment\n")
    unusable = _write(tmp_path / "unusable.tsv", "a\tX\n")
    duplicate = _write(tmp_path / "duplicate.tsv", "a\t𒀀𒀀\na\t𒀁𒀁\n")
    leading_space_comment = _write(tmp_path / "leading-space-comment.tsv", "  # not a loader comment\n")

    assert validator(empty), "comment-only map must be unusable"
    assert validator(unusable), "silently ignored loader row must be diagnosed"
    assert validator(duplicate), "duplicate reading must be diagnosed"
    assert validator(leading_space_comment), (
        "strict preflight must match current loader semantics: only leading '#' is a comment"
    )
