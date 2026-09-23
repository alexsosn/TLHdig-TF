"""#128 RED contract: mandatory build inputs must reject symlinks before reset."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build as build_program


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf8")
    return path


def _symlink(path: Path, target: Path) -> None:
    path.unlink()
    try:
        path.symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"filesystem cannot create symlink fixture: {exc}")


def _configure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    programs = root / "programs"
    corpus = root / "corpus"
    corpus.mkdir(parents=True)

    patches = _write(programs / "patches.yaml", "{}\n")
    _write(programs / "corpus.sha256", "synthetic\n")
    _write(programs / "excluded.txt", "# none\n")
    _write(programs / "signmap-multi.tsv", "a\t𒀀𒀀\n")

    version = "9.9.9"
    old_manifest = _write(
        root / "tf" / version / "BUILD-MANIFEST.json",
        "old validated artifact\n",
    )

    monkeypatch.setattr(build_program, "ROOT", root)
    monkeypatch.setattr(build_program, "CORPUS", corpus)
    monkeypatch.setattr(build_program, "PATCHES", patches)
    monkeypatch.setattr(build_program, "TF_VERSION", version)
    monkeypatch.setattr(build_program, "PROVENANCE_DIR", "tf-provenance")
    monkeypatch.setattr(build_program, "corpus_files", lambda: [])
    monkeypatch.setattr(build_program.repair, "read_manifest", lambda _path: {})
    monkeypatch.setattr(build_program.corpusid, "read_manifest", lambda _path: {})
    monkeypatch.setattr(build_program.corpusid, "verify", lambda *_args, **_kwargs: [])
    return old_manifest, programs


@pytest.mark.parametrize(
    "name,target_text",
    [
        ("excluded.txt", "# external but syntactically valid\n"),
        ("signmap-multi.tsv", "a\t𒀀𒀀\n"),
    ],
    ids=["ordinary-build-input", "semantic-map-input"],
)
def test_symlinked_required_input_fails_before_reset_and_conversion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    name: str,
    target_text: str,
) -> None:
    old_manifest, programs = _configure(monkeypatch, tmp_path)
    target = _write(tmp_path / "outside" / name, target_text)
    _symlink(programs / name, target)

    calls = 0

    def convert_build(*_args: object, **_kwargs: object) -> None:
        nonlocal calls
        calls += 1
        return None

    monkeypatch.setattr(build_program.convert, "build", convert_build)

    assert build_program.main() == 1
    assert old_manifest.read_text(encoding="utf8") == "old validated artifact\n"
    assert calls == 0
    output = capsys.readouterr().out
    assert name in output
    assert "symlink" in output.lower()


def test_regular_input_predicate_is_platform_independent(
    tmp_path: Path,
) -> None:
    predicate = getattr(build_program, "preflight_regular_input", None)
    assert callable(predicate), "#128 requires one shared mandatory-input type predicate"

    regular = _write(tmp_path / "regular.txt", "ok\n")
    assert predicate(regular) is None

    missing = tmp_path / "missing.txt"
    assert predicate(missing), "missing path must be rejected"


def test_regular_input_predicate_rejects_symlink_without_following_target() -> None:
    predicate = getattr(build_program, "preflight_regular_input", None)
    assert callable(predicate), "#128 requires one shared mandatory-input type predicate"

    class SymlinkPath:
        def is_symlink(self) -> bool:
            return True

        def is_file(self) -> bool:
            raise AssertionError("symlink target must not be followed by regular-file check")

    problem = predicate(SymlinkPath())
    assert problem and "symlink" in problem.lower()
