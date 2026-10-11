"""Historical release-certificate machinery is not active pre-alpha infrastructure (#116)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_historical_certification_entrypoints_and_modules_are_retired():
    retired = (
        "programs/release_check.py",
        "programs/check_stamp.py",
        "programs/release-delta.json",
        "programs/tlhdig/certification.py",
        "programs/tlhdig/certification_ref.py",
        "programs/tlhdig/release_delta.py",
        "programs/tlhdig/release_policy.py",
        "programs/tlhdig/stamp.py",
    )
    survivors = [path for path in retired if (ROOT / path).exists()]
    assert survivors == []


def test_current_artifact_has_no_historical_certificate_pair():
    current = ROOT / "tf" / "0.4.0"
    assert not (current / "BUILD-COMPLETE").exists()
    assert not (current / "RELEASE-CERTIFICATION.json").exists()
