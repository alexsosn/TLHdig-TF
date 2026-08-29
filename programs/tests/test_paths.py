"""Path identity across platforms.

macOS presents filenames in NFD (decomposed); git stores the bytes it was given, which
for this corpus is NFC. A manifest key generated on macOS therefore did not match the
same file checked out on Linux, and CI failed on `Çorum 6-1-96.xml` with
FileNotFoundError. Every recorded path is normalised to NFC, which is what git holds.
"""
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import paths


def test_rel_returns_nfc(tmp_path):
    d = tmp_path / "sub"
    d.mkdir()
    f = d / unicodedata.normalize("NFD", "Çorum.xml")
    f.write_text("<r/>", encoding="utf8")
    got = paths.rel(f, root=tmp_path)
    assert unicodedata.is_normalized("NFC", got), repr(got)
    assert got == "sub/Çorum.xml"


def test_rel_is_stable_whichever_form_the_filesystem_reports(tmp_path):
    for form in ("NFC", "NFD"):
        d = tmp_path / form
        d.mkdir()
        f = d / unicodedata.normalize(form, "Çorum.xml")
        f.write_text("<r/>", encoding="utf8")
        assert paths.rel(f, root=tmp_path).endswith("/Çorum.xml")


def test_manifest_keys_are_nfc():
    """The three checked-in manifests must all be NFC, or they break on Linux."""
    import yaml

    from tlhdig import corpusid

    bad = []
    doc = yaml.safe_load(paths.PATCHES.read_text(encoding="utf8")) or {}
    bad += [k for k in doc if not unicodedata.is_normalized("NFC", k)]
    bad += [
        k
        for k in corpusid.read_manifest(paths.PROGRAMS / "corpus.sha256")
        if not unicodedata.is_normalized("NFC", k)
    ]
    for ln in (paths.PROGRAMS / "excluded.txt").read_text(encoding="utf8").splitlines():
        if ln.strip() and not ln.startswith("#"):
            p = ln.split("\t")[0]
            if not unicodedata.is_normalized("NFC", p):
                bad.append(p)
    assert not bad, bad[:5]
