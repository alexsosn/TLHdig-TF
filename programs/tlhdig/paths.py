"""Canonical paths. Everything is resolved from the repository root."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus" / "TLHdig-0.3"
REPORTS = ROOT / "reports"
PROGRAMS = ROOT / "programs"
PATCHES = PROGRAMS / "patches.yaml"

# Upstream release identity, asserted by the inventory stage.
ZENODO_DOI = "10.5281/zenodo.20328284"
ZENODO_ZIP_MD5 = "f9acbc8db3111cc7dd88d82f7819a912"

# The one file that cannot be repaired (plan §7.2).
ENCRYPTED = "CTH 813_XML_TLH/KUB 37.25.xml"


def corpus_files():
    """Every .xml in the corpus, in stable sorted order."""
    return sorted(CORPUS.rglob("*.xml"), key=lambda p: str(p).lower())


def rel(p):
    """Path relative to the corpus root, POSIX-style, for use as a stable id."""
    return Path(p).resolve().relative_to(CORPUS).as_posix()
