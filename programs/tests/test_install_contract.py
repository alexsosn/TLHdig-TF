"""One coherent install story, mechanically enforced (#47).

The repository must not accumulate competing or stale instructions for something as basic
as installing the corpus. These tests keep three properties true:

1. install commands live in exactly one place;
2. current-facing files never name a non-current artifact version unless the line marks
   it as history;
3. the release asset name stays the one Text-Fabric actually looks for.
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "programs"))

from tlhdig import SOURCE_VERSION, TF_VERSION  # noqa: E402

CANONICAL = ROOT / "docs" / "install.md"

#: Files that describe the corpus as it is now. Research notes, frozen plans, the wiki
#: and the explicitly historical applications report are deliberately excluded: they
#: record what was true when written.
CURRENT_FACING = (
    "README.md",
    "KNOWN-ISSUES.md",
    "CITATION.cff",
    "app/config.yaml",
    "docs/index.md",
    "docs/install.md",
    "docs/about.md",
    "docs/querying.md",
    "docs/AGORA-INTEGRATION.md",
    "docs/RELEASE.md",
    "docs/data-model.md",
    "docs/identifiers.md",
    "docs/morphology.md",
    "docs/cuneiform.md",
    "docs/provenance.md",
    "docs/quality.md",
    "docs/editorial.md",
    "docs/text-formats.md",
    "docs/references.md",
    ".github/workflows/ci.yml",
    ".github/workflows/dataset.yml",
)

#: A line may name an older artifact when it is openly presented as history.
#: Stems, matched as prefixes so inflections ("historically", "previously") count.
HISTORICAL = re.compile(
    r"\b(histor|old\b|earlier|former|previous|retired|supersed|predecessor|migration|"
    r"was\b|used to|no longer|before\b|until\b|up to\b)",
    re.IGNORECASE,
)

VERSIONED_PATH = re.compile(r"tf[/-](\d+\.\d+\.\d+)")


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf8")


def test_every_current_facing_file_exists():
    missing = [name for name in CURRENT_FACING if not (ROOT / name).exists()]
    assert missing == []


def _paragraphs(text: str):
    """Yield (first line number, paragraph text). Prose wraps, so a marker can sit on a
    different physical line than the version it qualifies."""
    start = 1
    buffer: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if line.strip():
            if not buffer:
                start = number
            buffer.append(line)
        elif buffer:
            yield start, "\n".join(buffer)
            buffer = []
    if buffer:
        yield start, "\n".join(buffer)


def test_current_facing_files_name_only_the_current_artifact_version():
    offenders = []
    for name in CURRENT_FACING:
        for number, paragraph in _paragraphs(_read(name)):
            for found in VERSIONED_PATH.findall(paragraph):
                if found == TF_VERSION or HISTORICAL.search(paragraph):
                    continue
                offenders.append(f"{name}:{number}: tf/{found}")
    assert offenders == [], (
        "a current-facing file names a non-current artifact version without marking it "
        "as history: " + "; ".join(offenders)
    )


def test_install_commands_live_only_in_the_canonical_page():
    """Any other file that wants to explain installing must link here instead."""
    offenders = []
    for path in sorted(ROOT.glob("*.md")) + sorted((ROOT / "docs").glob("*.md")):
        if path == CANONICAL:
            continue
        if path.name.startswith(("research-", "plan-", "doc-", "review-")):
            continue
        if path.name == "applications-deep-research-report.md":
            continue  # explicitly historical, and says so
        for number, line in enumerate(path.read_text(encoding="utf8").splitlines(), 1):
            if "pip install" in line and "text-fabric" in line:
                offenders.append(f"{path.relative_to(ROOT)}:{number}")
    assert offenders == [], (
        "install instructions must live only in docs/install.md; found duplicates at "
        + ", ".join(offenders)
    )


def test_canonical_page_documents_the_github_backend_and_the_pygithub_pin():
    text = _read("docs/install.md")

    assert "text-fabric[github]==13.1.0" in text, "the [github] extra is required"
    assert "PyGithub<2.7" in text, (
        "TF 13.1.0 calls get_rate_limit().core, which PyGithub 2.7.0 removed"
    )
    assert "RateLimitOverview" in text, "explain why the pin exists, not just that it does"


def test_readme_and_index_point_at_the_canonical_page():
    assert "docs/install.md" in _read("README.md")
    assert "install.md" in _read("docs/index.md")


def test_release_asset_name_matches_what_text_fabric_looks_for():
    """TF builds the name from app config `relative`, flattened, plus the version.

    See tf/advanced/repo.py::downloadRelease -- a mismatch silently degrades every clean
    user to the slow file-by-file contents-API path.
    """
    import publish_release

    config = yaml.safe_load(_read("app/config.yaml"))
    relative = config["provenanceSpec"]["relative"]
    expected = f"{relative.removeprefix('/').replace('/', '-')}-{TF_VERSION}.zip"

    assert publish_release.ASSET == expected


def test_release_tag_tracks_both_source_and_tf_versions():
    import publish_release

    assert publish_release.TAG == f"tlhdig-{SOURCE_VERSION}_tf-{TF_VERSION}"


def test_app_config_declares_the_current_artifact_version():
    config = yaml.safe_load(_read("app/config.yaml"))

    assert config["provenanceSpec"]["version"] == TF_VERSION


def test_release_procedure_is_documented_as_a_single_command():
    text = _read("docs/RELEASE.md")

    assert "publish_release.py" in text
    assert "check_distribution.py" in text


# --- publishing guards --------------------------------------------------------------


def test_publisher_refuses_a_target_outside_the_default_branch(monkeypatch, capsys):
    """Bare acquisition reads app/config.yaml from the release's own commit, so a
    release must never point at an unpushed or side-branch commit."""
    import subprocess

    import publish_release

    monkeypatch.setattr(
        publish_release.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a[0] if a else [], 1, "", ""),
    )
    monkeypatch.setattr(publish_release, "_run", lambda *a, **k: "deadbeef")

    try:
        publish_release.main([])
    except SystemExit as exc:
        assert "not an ancestor" in str(exc.code)
    else:  # pragma: no cover - the guard must fire
        raise AssertionError("publisher accepted a target off the default branch")


def test_publisher_builds_a_flat_archive_including_the_manifest(tmp_path):
    """Text-Fabric extracts the asset straight into tf/<version>/ with extractall(),
    so members must sit at the zip root."""
    from zipfile import ZipFile

    import publish_release

    asset, count, raw = publish_release.build_asset(tmp_path)

    with ZipFile(asset) as zf:
        names = zf.namelist()

    assert count == len(names)
    assert raw > 0
    assert all("/" not in name for name in names), "archive must be flat"
    assert "BUILD-MANIFEST.json" in names, "a downloaded dataset must verify itself"
    assert "otype.tf" in names
