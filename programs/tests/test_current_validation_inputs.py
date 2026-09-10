"""Non-code inputs that can change current build bytes or validation semantics (#116)."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import validate_current
from tlhdig.paths import PROGRAMS, ROOT


def test_current_manifest_binds_all_known_validation_allowlists_and_sign_maps():
    inputs = validate_current.current_inputs()
    assert inputs == {
        "corpusManifest": PROGRAMS / "corpus.sha256",
        "repairManifest": PROGRAMS / "patches.yaml",
        "exclusions": PROGRAMS / "excluded.txt",
        "knownLossy": PROGRAMS / "known_lossy.txt",
        "contractAKnown": PROGRAMS / "contract_a_known.txt",
        "signMap": PROGRAMS / "signmap.tsv",
        "signMapMulti": PROGRAMS / "signmap-multi.tsv",
        "signrefLock": PROGRAMS / "signrefs.lock.json",
        "dependencies": ROOT / "requirements.txt",
    }


def test_manifest_inputs_cover_each_checked_in_validation_exception_list():
    bound = set(validate_current.current_inputs().values())
    for name in ("excluded.txt", "known_lossy.txt", "contract_a_known.txt"):
        assert PROGRAMS / name in bound


def test_manifest_inputs_cover_pinned_cuneiform_tables_used_by_build_or_gate():
    bound = set(validate_current.current_inputs().values())
    assert PROGRAMS / "signmap-multi.tsv" in bound  # converter input
    assert PROGRAMS / "signmap.tsv" in bound        # alignment regression witness
