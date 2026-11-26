"""One-time branch migration. No source XML changes, no relaxed validation gates.

Run only from the isolated migration branch; commit inputs before building.
Keep old source temporarily for adapting historically source-bound tests.
"""
from pathlib import Path
import shutil
import json

from lxml import etree
from tlhdig import corpusid, repair

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "programs"
C = ROOT / "corpus" / "TLHdig-0.4"
REL = "CTH 581_XML_HDivT/KBo 18.142.xml"
SHA = "2fb700b7b6ed4df543d271d6c2c57cc1ee6832ef1fd6fa5178b31444aaa71677"


def replace(path, changes):
    s = path.read_text(encoding="utf8")
    for old, new in changes:
        if old not in s:
            raise ValueError(f"{path}: missing expected text {old!r}")
        s = s.replace(old, new)
    path.write_text(s, encoding="utf8")


def main():
    old_pin = corpusid.read_manifest(P / "corpus.sha256")
    pin = corpusid.read_manifest(P / "corpus-beta04.sha256")
    assert len(pin) == 24324 and not corpusid.verify(C, pin)
    patches = repair.read_manifest(P / "patches-beta04-candidate.yaml")
    assert len(patches) == 13
    data = (C / REL).read_bytes()
    assert pin[REL] == SHA == repair.sha256(data)
    p = repair.Patch(b"DA.BI</sGr>-&lt;/SP_f_AO_3a_SumGRAM&gt;",
                     b"DA.BI&lt;/sGr>-&lt;/SP_f_AO_3a_SumGRAM&gt;",
                     "escape literal closing tag inside footnote attribute")
    fixed = repair.apply(data, [p], expect_sha=SHA)
    root = etree.fromstring(fixed)
    assert len(root.xpath(".//note[contains(@c, 'DA.BI</sGr>')]")) == 1
    patches[REL] = (SHA, [p])
    for rel, (sha, ps) in patches.items():
        raw = (C / rel).read_bytes()
        assert sha == pin[rel]
        fixed = repair.apply(raw, ps, expect_sha=sha)
        assert repair.parses(fixed)
        etree.fromstring(fixed)
    audit = json.loads((ROOT / "reports" / "beta04-repair-audit.json").read_text(encoding="utf8"))
    exclusions = {p: ("encrypted" if row["disposition"] == "encrypted" else "unparseable")
                  for p, row in audit["files"].items() if p not in patches}
    assert len(exclusions) == 9
    for rel, reason in exclusions.items():
        assert not repair.parses((C / rel).read_bytes())
    # No stale path/hash-based exception applies to changed source. Retain the
    # exact-byte old cases only; new deficits must be measured and reviewed.
    for name in ("known_lossy.txt", "contract_a_known.txt"):
        path = P / name
        rows = [line for line in path.read_text(encoding="utf8").splitlines()
                if line and not line.startswith("#")]
        keep = [line for line in rows if (rel := line.split("\t")[0]) in pin
                and pin[rel] == old_pin.get(rel)]
        path.write_text("# Beta 0.4 candidate: retained only byte-identical prior exceptions.\n"
                        "# Re-measure every retained exception before release.\n"
                        + "\n".join(keep) + "\n", encoding="utf8")
        print(name, len(rows), "->", len(keep))
    repair.write_manifest(P / "patches.yaml", patches)
    (P / "excluded.txt").write_text(
        "# Beta 0.4 candidate: unresolved malformed XML; source bytes retained.\n" +
        "".join(f"{rel}\t{why}\n" for rel, why in sorted(exclusions.items())), encoding="utf8")
    corpusid.write_manifest(P / "corpus.sha256", pin,
        "# TLHdig Beta 0.4, Zenodo 10.5281/zenodo.24373727; archive members only.\n")
    replace(P / "tlhdig" / "__init__.py", [
        ("Beta 0.3, Zenodo 10.5281/zenodo.20328284", "Beta 0.4, Zenodo 10.5281/zenodo.24373727"),
        ('SOURCE_VERSION = "0.3"', 'SOURCE_VERSION = "0.4"')])
    replace(P / "tlhdig" / "paths.py", [
        ("TLHdig-0.3", "TLHdig-0.4"),
        ("10.5281/zenodo.20328284", "10.5281/zenodo.24373727"),
        ("f9acbc8db3111cc7dd88d82f7819a912", "a31a1ac9808ac77432466a910ed85969")])
    replace(P / "tlhdig" / "convert.py", [
        ("10.5281/zenodo.20328284", "10.5281/zenodo.24373727"),
        ("Derived from TLHdig 0.3", "Derived from TLHdig 0.4")])
    replace(P / "build.py", [
        ("TLHdig 0.3", "TLHdig 0.4"),
        ("Beta Version 0.3", "Beta Version 0.4"),
        ("10.5281/zenodo.20328284", "10.5281/zenodo.24373727")])
    # Attribution beside, not inside, the archive-identity directory.
    (ROOT / "corpus" / "ATTRIBUTION.md").write_text(
        "# TLHdig Beta 0.4 source attribution\n\n"
        "The Beta 0.4 archive is redistributed under CC-BY-4.0, not the root MIT licence. "
        "Müller, Gerfrid; Prechel, Doris; Rieken, Elisabeth; Schwemer, Daniel. "
        "Thesaurus Linguarum Hethaeorum digitalis (TLHdig) Beta Version 0.4. Zenodo, 2026. "
        "https://doi.org/10.5281/zenodo.24373727. "
        "Licence: https://creativecommons.org/licenses/by/4.0/.\n\n"
        "Source files are byte-preserved. macOS metadata is omitted; 14 unflagged UTF-8 "
        "ZIP filenames are decoded correctly and filenames are NFC-normalized. "
        "Repairs in programs/patches.yaml are applied only in memory.\n",
        encoding="utf8")
    print("Candidate source pin:", len(pin), "members;", len(patches), "repaired files;",
          len(exclusions), "exclusions; TF version unchanged for first build.")


if __name__ == "__main__":
    main()
