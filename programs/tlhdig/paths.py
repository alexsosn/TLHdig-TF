"""Canonical paths. Everything is resolved from the repository root."""
import unicodedata
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
    """Every .xml in the corpus, in stable sorted order.

    The key is NFC-normalised because the sort order decides document order, which
    decides every node number in the dataset. macOS stores the 16 non-ASCII filenames
    decomposed (NFD) while git records them composed, so sorting the raw path put 1,727
    documents at different indices there than on Linux and changed 102 of 119 feature
    bodies. Normalising is a no-op wherever the checkout is already NFC, so it does not
    move any released artifact; it only stops the filesystem deciding node numbering.
    """
    return sorted(
        CORPUS.rglob("*.xml"),
        key=lambda p: unicodedata.normalize("NFC", str(p)).lower(),
    )


def rel(p, root=None):
    """Path relative to the corpus root, POSIX-style, for use as a stable id.

    Normalised to **NFC**.  macOS reports filenames in NFD, while git stores the bytes
    it was given -- NFC for this corpus.  A manifest generated on macOS therefore keyed
    `Çorum 6-1-96.xml` in decomposed form and failed to find the same file on a Linux
    checkout, which is how CI first broke.
    """
    base = Path(root) if root is not None else CORPUS
    return unicodedata.normalize(
        "NFC", Path(p).resolve().relative_to(Path(base).resolve()).as_posix()
    )
