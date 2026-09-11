from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def test_issue_local_release_automation_does_not_survive_final_pr():
    forbidden = [
        WORKFLOWS / "build-final-19.yml",
        WORKFLOWS / "finalize-issue19.yml",
        WORKFLOWS / "sync-main-sign-lang.yml",
        ROOT / "programs" / "tests" / "test_issue19_release_staging.py",
        ROOT / "programs" / "tests" / "test_issue19_release_finalization.py",
    ]
    assert not [str(path.relative_to(ROOT)) for path in forbidden if path.exists()]


def test_current_tools_fail_closed_instead_of_falling_back_to_old_artifact():
    text = (ROOT / "programs" / "research_weblink_ids.py").read_text(encoding="utf8")
    assert 'default=ROOT / "tf" / TF_VERSION' in text
    assert "def default_tf_dir" not in text
    assert "args.tf_dir or default_tf_dir()" not in text


def test_web_link_identity_test_requires_the_current_artifact():
    text = (ROOT / "programs" / "tests" / "test_tlhdig_weblink.py").read_text(encoding="utf8")
    assert "_identity_census_tf_dir" not in text
    assert 'ROOT / "tf" / "0.3.0"' not in text
    assert 'ROOT / "tf" / TF_VERSION' in text
