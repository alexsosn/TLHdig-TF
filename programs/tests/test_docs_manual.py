from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "programs"))

import check_docs


def _write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf8")


def _minimal_root(tmp_path: Path) -> Path:
    root = tmp_path
    _write(root / "README.md", "See [documentation](docs/index.md).\n")
    _write(
        root / "tf" / "9.9.9" / "otype.tf",
        "@node\n@valueType=str\n\n1\tsign\n2\tword\n",
    )
    _write(root / "tf" / "9.9.9" / "sym.tf", "@node\n@valueType=str\n\n1\ta\n")
    for page in check_docs.PUBLIC_PAGES:
        _write(root / "docs" / page, f"# {page}\n")
    nav = "\n".join(
        f"- [{target}]({target})" for target in check_docs.NAV_TARGETS
    )
    _write(root / "docs" / "features" / "0_home.md", "# Features\n")
    _write(root / "docs" / "index.md", "# Docs\n" + nav + "\n")
    _write(
        root / "docs" / "data-model.md",
        "# Data model\n<!-- tf-node-types: sign word -->\n",
    )
    _write(
        root / "docs" / "querying.md",
        "# Querying\n<!-- tf-features: sym -->\n",
    )
    return root


def test_checker_accepts_minimal_consistent_manual(tmp_path):
    root = _minimal_root(tmp_path)
    assert check_docs.check_manual(root, tf_version="9.9.9", run_feature_check=False) == []


def test_checker_rejects_broken_internal_link(tmp_path):
    root = _minimal_root(tmp_path)
    with (root / "docs" / "about.md").open("a", encoding="utf8") as fh:
        fh.write("[missing](does-not-exist.md)\n")
    problems = check_docs.check_manual(root, tf_version="9.9.9", run_feature_check=False)
    assert any("broken internal link 'does-not-exist.md'" in problem for problem in problems)


def test_checker_rejects_stale_current_version_claim(tmp_path):
    root = _minimal_root(tmp_path)
    with (root / "docs" / "about.md").open("a", encoding="utf8") as fh:
        fh.write("Current TF version: `1.2.3`\n")
    problems = check_docs.check_manual(root, tf_version="9.9.9", run_feature_check=False)
    assert any("current TF version 1.2.3 != 9.9.9" in problem for problem in problems)


def test_checker_rejects_unknown_schema_markers(tmp_path):
    root = _minimal_root(tmp_path)
    _write(
        root / "docs" / "data-model.md",
        "# Data model\n<!-- tf-node-types: sign imaginary -->\n",
    )
    _write(
        root / "docs" / "querying.md",
        "# Querying\n<!-- tf-features: sym imaginary_feature -->\n",
    )
    problems = check_docs.check_manual(root, tf_version="9.9.9", run_feature_check=False)
    assert any("unknown TF node types: imaginary" in problem for problem in problems)
    assert any("unknown TF features: imaginary_feature" in problem for problem in problems)


def test_repository_manual_contract_is_green():
    problems = check_docs.check_manual(ROOT)
    assert problems == [], "\n".join(problems)


def test_morphology_manual_documents_selector_state_contract():
    text = (ROOT / "docs" / "morphology.md").read_text(encoding="utf8")
    selector = text.split("## Selector state", 1)[1].split("\n## ", 1)[0]
    required = (
        "empty/missing",
        "`none`",
        "numeric",
        "`analysis`",
        "`???`",
        "`unknown`",
        "fallback",
        "`DEL`",
        "`AKK`",
        "`HURR`",
        "`HAT`",
        "`SUM`",
        "`LUW`",
        "validation",
        "<annot>",
    )
    missing = [term for term in required if term not in selector]
    assert missing == [], "selector-state documentation is missing: " + ", ".join(missing)


def test_readme_corpus_snapshot_matches_generated_reports():
    """Public headline metrics must follow the validated current TF artifact.

    This is a regression for #159: the README carried earlier sign, word,
    aligned-reading and feature counts even when reports/census.md and
    reports/alignment.md were updated by a full successful rebuild.
    """
    import re

    readme = (ROOT / "README.md").read_text(encoding="utf8")
    census = (ROOT / "reports" / "census.md").read_text(encoding="utf8")
    alignment = (ROOT / "reports" / "alignment.md").read_text(encoding="utf8")

    counts = dict(re.findall(r"^\\| `([a-z]+)` \\| ([\\d,]+) \\|$", census, re.M))
    for node_type, row_name in (
        ("sign", "signs (slots)"),
        ("word", "words"),
        ("analysis", "morphological analyses"),
        ("cluster", "damage/editorial clusters"),
        ("line", "lines"),
        ("lex", "lexical nodes"),
        ("document", "documents"),
    ):
        assert node_type in counts
        assert f"| {row_name} | {counts[node_type]} |" in readme, row_name

    total = re.search(r"\\*\\*total\\*\\* ([\\d,]+)", census)
    features = re.search(r"(\\d+) node features", census)
    aligned = re.search(
        r"signs carrying `cu_sign`: \\*\\*([\\d,]+)\\*\\* of ([\\d,]+) \\(([\\d.]+%)\\)",
        alignment,
    )
    assert total and features and aligned
    assert f"| **all nodes** | **{total.group(1)}** |" in readme
    assert f"{features.group(1)} node features" in readme

    have, all_signs, percentage = aligned.groups()
    assert all_signs == counts["sign"]
    assert f"**{have} of {all_signs} signs ({percentage})**" in readme
    assert f"on {percentage} of sign slots" in readme
