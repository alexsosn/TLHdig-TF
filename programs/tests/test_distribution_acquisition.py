"""Clean-user acquisition must resolve the one current pre-alpha artifact (#47).

Hermetic. The live-repository assertion is the job of ``programs/check_distribution.py``;
these tests pin the resolution contract, the policy, and the documentation that tells a
clean user what to run.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "programs"))

from tlhdig import TF_VERSION  # noqa: E402
import distribution  # noqa: E402

import check_distribution  # noqa: E402


def _release(tag="tlhdig-0.3_tf-0.2.0", version="0.1.0", dirs=("0.1.0", "0.2.0"), output_digest=None):
    return distribution.LatestRelease(
        tag=tag,
        commit="4309cf3318c682282c1480b233786362a3083471",
        declared_tf_version=version,
        version_dirs=tuple(dirs),
        output_digest=output_digest,
    )


# --- the pinned dependency's own semantics ------------------------------------------


def test_installed_text_fabric_resolves_bare_to_release_then_commit():
    """If upstream ever changes this, every conclusion in #47 has to be re-derived."""
    from tf.advanced.repo import fromString

    assert distribution.bare_resolution_order(fromString) == distribution.RELEASE_FIRST


def test_bare_resolution_order_rejects_a_changed_upstream_contract():
    assert distribution.bare_resolution_order(lambda _: ("", "", None))

    with pytest.raises(ValueError):
        distribution.bare_resolution_order(lambda _: (None, "", None))
    with pytest.raises(ValueError):
        distribution.bare_resolution_order(lambda _: ("", None, None))
    with pytest.raises(ValueError):
        distribution.bare_resolution_order(lambda _: (None, None, "clone"))


# --- the resolution contract ---------------------------------------------------------


def test_no_published_latest_release_tracks_the_default_branch_head():
    result = distribution.evaluate(None, tf_version=TF_VERSION)

    assert result.state == distribution.PASSED
    assert result.resolves_to == "default-branch-head"


def test_a_stale_latest_release_is_a_failure_not_a_skip():
    """The measured 2026-10-11 state: declares 0.1.0, carries 0.1.0 and 0.2.0."""
    result = distribution.evaluate(_release(), tf_version=TF_VERSION)

    assert result.state == distribution.FAILED
    assert "tlhdig-0.3_tf-0.2.0" in result.detail
    assert "0.1.0" in result.detail
    assert TF_VERSION in result.detail


def test_a_release_declaring_the_current_version_but_missing_it_fails():
    result = distribution.evaluate(
        _release(version=TF_VERSION, dirs=("0.2.0",)), tf_version=TF_VERSION
    )

    assert result.state == distribution.FAILED
    assert f"no tf/{TF_VERSION} directory" in result.detail


def test_a_release_carrying_the_current_version_but_declaring_another_fails():
    result = distribution.evaluate(
        _release(version="0.2.0", dirs=(TF_VERSION,)), tf_version=TF_VERSION
    )

    assert result.state == distribution.FAILED
    assert "provenanceSpec.version" in result.detail


def test_a_deliberate_current_snapshot_release_is_allowed():
    digest = "sha256:" + "a" * 64
    result = distribution.evaluate(
        _release(tag="snapshot", version=TF_VERSION, dirs=(TF_VERSION, "0.2.0"),
                 output_digest=digest),
        tf_version=TF_VERSION, current_output_digest=digest,
    )

    assert result.state == distribution.PASSED


# --- execution policy ----------------------------------------------------------------


def test_ordinary_mode_may_skip_an_unreachable_backend_but_release_mode_may_not():
    skip = distribution.unavailable("no network")

    assert skip.state == distribution.SKIPPED_UNAVAILABLE
    assert distribution.exit_code(skip.state, mode="ordinary") == 0
    assert distribution.exit_code(skip.state, mode="release") == 2


def test_a_wrong_version_fails_in_both_modes():
    for mode in ("ordinary", "release"):
        assert distribution.exit_code(distribution.FAILED, mode=mode) == 1


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError):
        distribution.exit_code(distribution.PASSED, mode="whatever")


def test_status_file_records_mode_and_resolution(tmp_path):
    path = tmp_path / "distribution-status.json"
    distribution.write_status(
        path, distribution.evaluate(_release(), tf_version=TF_VERSION), mode="release"
    )

    written = json.loads(path.read_text(encoding="utf8"))
    assert written["mode"] == "release"
    assert written["state"] == distribution.FAILED
    assert written["latest_release"]["tag"] == "tlhdig-0.3_tf-0.2.0"


def test_gate_reports_failure_without_network(monkeypatch, tmp_path):
    monkeypatch.setattr(
        check_distribution, "latest_release", lambda org, repo: _release()
    )

    code = check_distribution.main(
        ["--mode", "release", "--status", str(tmp_path / "status.json")]
    )

    assert code == 1


def test_gate_passes_when_no_release_is_published(monkeypatch, tmp_path):
    monkeypatch.setattr(check_distribution, "latest_release", lambda org, repo: None)

    code = check_distribution.main(
        ["--mode", "release", "--status", str(tmp_path / "status.json")]
    )

    assert code == 0


def test_gate_skips_ordinary_and_fails_release_when_backend_is_unreachable(
    monkeypatch, tmp_path
):
    def unreachable(org, repo):
        raise distribution.BackendUnavailable("no network")

    monkeypatch.setattr(check_distribution, "latest_release", unreachable)

    assert (
        check_distribution.main(
            ["--mode", "ordinary", "--status", str(tmp_path / "a.json")]
        )
        == 0
    )
    assert (
        check_distribution.main(
            ["--mode", "release", "--status", str(tmp_path / "b.json")]
        )
        == 2
    )


# --- what a clean user is told to run ------------------------------------------------


def test_online_acquisition_install_instructions_include_the_github_backend():
    """Pinned text-fabric 13.1.0 cannot reach GitHub without the [github] extra."""
    readme = (ROOT / "README.md").read_text(encoding="utf8")

    assert "pip install text-fabric==13.1.0" not in readme or (
        "text-fabric[github]==13.1.0" in readme
    ), "README documents an install that cannot perform online acquisition"


def test_the_distribution_gate_runs_in_ordinary_ci():
    workflows = ROOT / ".github" / "workflows"
    texts = [
        path.read_text(encoding="utf8") for path in workflows.glob("*.yml")
    ]

    assert any("check_distribution.py" in text for text in texts)


def test_research_record_exists_for_the_acquisition_contract():
    doc = ROOT / "docs" / "research-distribution-acquisition.md"

    assert doc.exists()
    text = doc.read_text(encoding="utf8")
    assert "get_latest_release" in text
    assert "tlhdig-0.3_tf-0.2.0" in text


# --- same-version current-artifact identity regression (post #20) ---------------------

def test_live_same_version_stale_release_is_a_hard_failure():
    """Live measured release from 2026-10-11: both claim 0.4.0 but output differs."""
    tagged = "sha256:a91ec01059387282c75c741f2d6d588ca95314c8e7333a7f4f93c13ac398e843"
    current = "sha256:1a4cb36fa5512bf400fce45bf02eeee960849dea0ac2fc0c8afddbe64c61036d"
    release = _release(tag="tlhdig-0.3_tf-0.4.0", version=TF_VERSION,
                       dirs=(TF_VERSION,), output_digest=tagged)
    result = distribution.evaluate(release, tf_version=TF_VERSION,
                                   current_output_digest=current)
    assert result.state == distribution.FAILED
    assert "artifact" in result.detail.lower() or "digest" in result.detail.lower()
    assert result.latest_release.output_digest == tagged


def test_missing_or_invalid_identity_cannot_pass_with_matching_version():
    good = "sha256:" + "a" * 64
    for observed, current in ((None, good), (good, None),
                              ("not-a-digest", good), (good, "invalid")):
        result = distribution.evaluate(
            _release(tag="snapshot", version=TF_VERSION, dirs=(TF_VERSION,),
                     output_digest=observed),
            tf_version=TF_VERSION, current_output_digest=current,
        )
        assert result.state == distribution.FAILED


def test_current_snapshot_requires_equal_output_identities():
    a = "sha256:" + "a" * 64
    b = "sha256:" + "b" * 64
    current = _release(tag="latest", version=TF_VERSION, dirs=(TF_VERSION,),
                       output_digest=a)
    assert distribution.evaluate(current, tf_version=TF_VERSION,
                                 current_output_digest=a).state == distribution.PASSED
    assert distribution.evaluate(current, tf_version=TF_VERSION,
                                 current_output_digest=b).state == distribution.FAILED


def test_manifest_output_digest_rejects_missing_or_corrupt_manifest():
    import json
    good = {"outputs": {"algorithm": "tlhdig-current-tree-v2",
                        "digest": "sha256:" + "a" * 64}}
    assert check_distribution.manifest_output_digest(json.dumps(good).encode()) == good["outputs"]["digest"]
    for payload in (b"{}", b"not-json", b'{"outputs": {"digest": "oops"}}'):
        with pytest.raises(ValueError):
            check_distribution.manifest_output_digest(payload)
