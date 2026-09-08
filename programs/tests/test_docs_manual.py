from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"

REQUIRED_PUBLIC_PAGES = (
    "index.md",
    "about.md",
    "data-model.md",
    "text-formats.md",
    "editorial.md",
    "identifiers.md",
    "morphology.md",
    "cuneiform.md",
    "provenance.md",
    "quality.md",
    "querying.md",
    "references.md",
)


def test_required_public_manual_pages_exist():
    missing = [name for name in REQUIRED_PUBLIC_PAGES if not (DOCS / name).is_file()]
    assert missing == []


def test_readme_routes_to_canonical_documentation_index():
    text = (ROOT / "README.md").read_text(encoding="utf8")
    assert "docs/index.md" in text


def test_durable_documentation_checker_exists():
    assert (ROOT / "programs" / "check_docs.py").is_file()
