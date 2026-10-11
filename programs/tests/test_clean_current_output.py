"""RED contract for clean current-artifact rebuilds (#118)."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build as build_program


def _write(path: Path, text: str = "old\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf8")
    return path


def _reset(main: Path, provenance: Path, main_parent: Path, provenance_parent: Path) -> None:
    helper = getattr(build_program, "reset_current_output", None)
    assert callable(helper), "build.py must expose the focused current-output reset helper"
    helper(
        main,
        provenance,
        main_parent=main_parent,
        provenance_parent=provenance_parent,
    )


def test_reset_removes_complete_current_trees_but_not_sibling_versions(tmp_path: Path) -> None:
    main_parent = tmp_path / "tf"
    provenance_parent = tmp_path / "tf-provenance"
    main = main_parent / "0.4.0"
    provenance = provenance_parent / "0.4.0"

    _write(main / "obsolete.tf")
    _write(main / "BUILD-MANIFEST.json", "{}\n")
    _write(main / "BUILD-COMPLETE")
    _write(main / "RELEASE-CERTIFICATION.json", "{}\n")
    _write(main / "LICENSE", "stale license\n")
    _write(main / ".tf" / "otype.tfx", "cache\n")
    _write(provenance / "obsolete.tf")
    _write(provenance / "README.md", "stale provenance readme\n")
    _write(provenance / ".tf" / "srcxml.tfx", "cache\n")

    main_sibling = _write(main_parent / "0.3.0" / "keep.tf", "historic main\n")
    provenance_sibling = _write(
        provenance_parent / "0.3.0" / "keep.tf", "historic provenance\n"
    )

    _reset(main, provenance, main_parent, provenance_parent)

    assert main.is_dir()
    assert list(main.iterdir()) == []
    assert not provenance.exists()
    assert main_sibling.read_text(encoding="utf8") == "historic main\n"
    assert provenance_sibling.read_text(encoding="utf8") == "historic provenance\n"


def test_reset_rejects_a_sibling_version_even_when_paths_are_direct_children(tmp_path: Path) -> None:
    main_parent = tmp_path / "tf"
    provenance_parent = tmp_path / "tf-provenance"
    sibling_main = main_parent / "0.3.0"
    sibling_provenance = provenance_parent / "0.3.0"
    main_sentinel = _write(sibling_main / "must-survive.tf", "historic main\n")
    provenance_sentinel = _write(
        sibling_provenance / "must-survive.tf", "historic provenance\n"
    )

    with pytest.raises((ValueError, OSError), match="version|current output"):
        _reset(sibling_main, sibling_provenance, main_parent, provenance_parent)

    assert main_sentinel.read_text(encoding="utf8") == "historic main\n"
    assert provenance_sentinel.read_text(encoding="utf8") == "historic provenance\n"


def test_reset_validates_both_targets_before_deleting_either(tmp_path: Path) -> None:
    main_parent = tmp_path / "tf"
    provenance_parent = tmp_path / "tf-provenance"
    main = main_parent / "0.4.0"
    provenance = provenance_parent / "0.4.0"
    main_sentinel = _write(main / "keep-until-validation-completes.tf")

    external = tmp_path / "outside-provenance"
    outside_sentinel = _write(external / "must-survive.tf")
    provenance_parent.mkdir(parents=True, exist_ok=True)
    try:
        provenance.symlink_to(external, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks unavailable on this platform")

    with pytest.raises((ValueError, OSError), match="symlink|current output|direct child"):
        _reset(main, provenance, main_parent, provenance_parent)

    assert main_sentinel.is_file(), "main must not be deleted before provenance validation"
    assert outside_sentinel.read_text(encoding="utf8") == "old\n"
    assert provenance.is_symlink()


@pytest.mark.parametrize("case", ["nested", "wrong-parent", "parent-itself"])
def test_reset_rejects_targets_outside_exact_current_version_slot(
    tmp_path: Path, case: str
) -> None:
    main_parent = tmp_path / "tf"
    provenance_parent = tmp_path / "tf-provenance"
    valid_main = main_parent / "0.4.0"
    valid_provenance = provenance_parent / "0.4.0"
    sentinel = _write(valid_main / "must-survive.tf")

    if case == "nested":
        main = valid_main / "nested"
    elif case == "wrong-parent":
        main = tmp_path / "other" / "0.4.0"
    else:
        main = main_parent

    with pytest.raises((ValueError, OSError), match="direct child|current output|parent"):
        _reset(main, valid_provenance, main_parent, provenance_parent)

    assert sentinel.is_file()


def test_reset_rejects_symlinked_parent_without_following_it(tmp_path: Path) -> None:
    real_main_parent = tmp_path / "real-main"
    real_main = real_main_parent / "0.4.0"
    outside_sentinel = _write(real_main / "must-survive.tf")
    main_parent = tmp_path / "tf"
    try:
        main_parent.symlink_to(real_main_parent, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks unavailable on this platform")

    provenance_parent = tmp_path / "tf-provenance"
    provenance = provenance_parent / "0.4.0"

    with pytest.raises((ValueError, OSError), match="symlink|parent"):
        _reset(main_parent / "0.4.0", provenance, main_parent, provenance_parent)

    assert outside_sentinel.is_file()


class _Ledger:
    marker_src = 0
    marker_fed = 0
    marker_out = 0

    def __init__(self, *, allow: dict[str, str | None]) -> None:
        self.allow = allow

    def report(self) -> str:
        return "ledger"

    def marker_report(self) -> str:
        return "markers"

    def allowed(self) -> bool:
        return True


def _configure_synthetic_build(monkeypatch: pytest.MonkeyPatch, root: Path) -> tuple[Path, Path]:
    version = "9.9.9"
    main = root / "tf" / version
    provenance = root / "tf-provenance" / version
    programs = root / "programs"
    programs.mkdir(parents=True, exist_ok=True)
    corpus = root / "corpus"
    corpus.mkdir(parents=True)

    patches = _write(programs / "patches.yaml", "{}\n")
    _write(programs / "corpus.sha256", "synthetic\n")
    _write(programs / "excluded.txt", "# none\n")
    _write(programs / "signmap-multi.tsv", "a\t𒀀𒀀\n")

    monkeypatch.setattr(build_program, "ROOT", root)
    monkeypatch.setattr(build_program, "CORPUS", corpus)
    monkeypatch.setattr(build_program, "PATCHES", patches)
    monkeypatch.setattr(build_program, "TF_VERSION", version)
    monkeypatch.setattr(build_program, "PROVENANCE_DIR", "tf-provenance")
    monkeypatch.setattr(build_program, "PROVENANCE_FEATURES", ())
    monkeypatch.setattr(build_program, "corpus_files", lambda: [])
    # These older reset tests intentionally use a synthetic empty source
    # corpus. The real four-source policy has its own source-backed tests
    # below; do not let synthetic tests depend on a real production checkout.
    monkeypatch.setattr(build_program, "preflight_recovery_pilots", lambda *_args: ())
    monkeypatch.setattr(build_program.corpusid, "read_manifest", lambda _path: {})
    monkeypatch.setattr(build_program.corpusid, "verify", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(build_program.convert, "Ledger", _Ledger)
    monkeypatch.setattr(build_program.compact, "compact_dir", lambda _out: [])
    return main, provenance


def test_converter_failure_cannot_inherit_previous_generated_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    main, provenance = _configure_synthetic_build(monkeypatch, tmp_path / "repo")
    _write(main / "BUILD-MANIFEST.json", "{}\n")
    _write(main / "obsolete.tf")
    _write(provenance / "obsolete.tf")
    observed: dict[str, bool] = {}

    def fail_build(_corpus: Path, out: Path, **_kwargs: object) -> None:
        observed["old_manifest_exists"] = (out / "BUILD-MANIFEST.json").exists()
        observed["stale_main_exists"] = (out / "obsolete.tf").exists()
        observed["stale_provenance_exists"] = (provenance / "obsolete.tf").exists()
        return None

    monkeypatch.setattr(build_program.convert, "build", fail_build)

    assert build_program.main() == 1
    assert observed == {
        "old_manifest_exists": False,
        "stale_main_exists": False,
        "stale_provenance_exists": False,
    }
    assert not (main / "BUILD-MANIFEST.json").exists()


def test_source_identity_failure_happens_before_destructive_reset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "repo"
    main, _provenance = _configure_synthetic_build(monkeypatch, root)
    old_manifest = _write(main / "BUILD-MANIFEST.json", "old validated artifact\n")

    monkeypatch.setattr(build_program.corpusid, "verify", lambda *_args, **_kwargs: ["bad source"])
    monkeypatch.setattr(
        build_program.convert,
        "build",
        lambda *_args, **_kwargs: pytest.fail("converter must not run after source preflight failure"),
    )

    assert build_program.main() == 1
    assert old_manifest.read_text(encoding="utf8") == "old validated artifact\n"


@pytest.mark.parametrize("missing_name", ["patches.yaml", "corpus.sha256", "excluded.txt"])
def test_missing_required_preflight_file_fails_before_destructive_reset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, missing_name: str
) -> None:
    root = tmp_path / "repo"
    main, _provenance = _configure_synthetic_build(monkeypatch, root)
    old_manifest = _write(main / "BUILD-MANIFEST.json", "old validated artifact\n")
    (root / "programs" / missing_name).unlink()

    monkeypatch.setattr(
        build_program.convert,
        "build",
        lambda *_args, **_kwargs: pytest.fail(
            f"converter must not run when required preflight file is missing: {missing_name}"
        ),
    )

    assert build_program.main() == 1
    assert old_manifest.read_text(encoding="utf8") == "old validated artifact\n"


def test_successful_synthetic_build_does_not_retain_old_feature_or_companions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "repo"
    main, provenance = _configure_synthetic_build(monkeypatch, root)
    _write(main / "obsolete.tf")
    _write(main / "LICENSE", "old license\n")
    _write(provenance / "obsolete.tf")
    _write(provenance / "README.md", "old readme\n")

    def build_new(_corpus: Path, out: Path, **_kwargs: object) -> object:
        _write(out / "new.tf", "@node\n\n1\tnew\n")
        return object()

    monkeypatch.setattr(build_program.convert, "build", build_new)

    assert build_program.main() == 0
    assert (main / "new.tf").is_file()
    assert not (main / "obsolete.tf").exists()
    assert (main / "LICENSE").read_text(encoding="utf8") == build_program.DATASET_LICENSE
    assert not (provenance / "obsolete.tf").exists()
    assert (provenance / "README.md").read_text(encoding="utf8").startswith(
        "# TLHdig-TF provenance module"
    )


# #150: production activation of source-reviewed recovery, before artifact reset.
RECOVERY_PILOTS_EXPECTED = (
    "CTH 209_XML_TLH/KBo 12.55.xml",
    "CTH 448_XML_BESRIT/KBo 10.36.xml",
    "CTH 820_XML_TLH/KUB 48.15.xml",
    "CTH 832_XML_TLH/UBT 70.xml",
)


def test_real_source_recovery_pilots_preflight_against_signed_manifest() -> None:
    from tlhdig import repair
    from tlhdig.paths import CORPUS, PATCHES

    files = tuple(CORPUS / rel for rel in RECOVERY_PILOTS_EXPECTED)
    patches = repair.read_manifest(PATCHES)
    selected = build_program.preflight_recovery_pilots(files, patches)
    assert set(selected) == set(RECOVERY_PILOTS_EXPECTED)
    assert len(selected) == 4

    # Selecting a corpus subset lacking a mandatory pilot cannot silently
    # skip it while the build still claims to use reviewed source recovery.
    with pytest.raises(ValueError, match="pilot|source|missing"):
        build_program.preflight_recovery_pilots(files[:-1], patches)

    # The source SHA and reviewed patch policy must agree with the exact
    # in-memory manifest passed to the production converter.
    altered = dict(patches)
    altered.pop(RECOVERY_PILOTS_EXPECTED[0])
    with pytest.raises(ValueError, match="manifest|pilot|source"):
        build_program.preflight_recovery_pilots(files, altered)


def test_main_enables_exact_preflighted_recovery_pilots(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    main, _ = _configure_synthetic_build(monkeypatch, root)
    sentinel = _write(main / "old-current.tf")
    selected = RECOVERY_PILOTS_EXPECTED
    checks: list[str] = []

    def preflight(_files, _patches):
        assert sentinel.is_file(), "preflight must precede destructive reset"
        checks.append("preflight")
        return selected

    def build(_corpus, out, **kwargs):
        assert checks == ["preflight"]
        assert kwargs.get("terminal_recovery_paths") == selected
        assert not sentinel.exists(), "reset must precede the converter"
        checks.append("converted")
        _write(out / "new.tf", "@node\n\n1\tnew\n")
        return True

    monkeypatch.setattr(
        build_program, "preflight_recovery_pilots", preflight, raising=False,
    )
    monkeypatch.setattr(build_program.convert, "build", build)

    assert build_program.main() == 0
    assert checks == ["preflight", "converted"]


def test_main_keeps_current_artifact_if_recovery_preflight_rejects_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    main, provenance = _configure_synthetic_build(monkeypatch, root)
    old = _write(main / "BUILD-MANIFEST.json", "previous current corpus\n")
    old_feature = _write(main / "otype.tf", "previous TF nodes\n")
    old_provenance = _write(provenance / "srcxml.tf", "previous source\n")

    def fail_preflight(_files, _patches):
        raise ValueError("pilot source SHA and signed policy disagree")

    monkeypatch.setattr(
        build_program, "preflight_recovery_pilots", fail_preflight, raising=False,
    )
    monkeypatch.setattr(
        build_program.convert, "build",
        lambda *_a, **_kw: pytest.fail("converter must not run on pilot drift"),
    )

    assert build_program.main() == 1
    assert old.read_text(encoding="utf8") == "previous current corpus\n"
    assert old_feature.read_text(encoding="utf8") == "previous TF nodes\n"
    assert old_provenance.read_text(encoding="utf8") == "previous source\n"
