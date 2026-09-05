#!/usr/bin/env python
"""Full conversion: corpus -> tf/<tfVersion>/."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import (PROVENANCE_DIR, PROVENANCE_FEATURES, TF_VERSION, compact,
                    convert, corpusid, repair, stamp)
from tlhdig.paths import CORPUS, PATCHES, ROOT, corpus_files


DATASET_LICENSE = """\
Thesaurus Linguarum Hethaeorum digitalis -- Text-Fabric conversion
SPDX-License-Identifier: CC-BY-4.0

This dataset is an ADAPTATION of TLHdig 0.3 (Hethitologie-Portal Mainz), which is
licensed CC-BY-4.0.  An adaptation inherits that licence: it is CC-BY-4.0, not the MIT
licence that covers the converter source code.

Attribution is required.  Cite the source dataset, not this conversion:

  Mueller, Gerfrid; Prechel, Doris; Rieken, Elisabeth; Schwemer, Daniel.
  Thesaurus Linguarum Hethaeorum digitalis (TLHdig) Beta Version 0.3.
  Zenodo, 2026.  https://doi.org/10.5281/zenodo.20328284

Licence text: https://creativecommons.org/licenses/by/4.0/
Conversion:   https://github.com/alexsosn/TLHdig-TF

This build is an integration prototype and is not suitable for research conclusions.
See KNOWN-ISSUES.md in the conversion repository.
"""


def split_provenance(out) -> list[str]:
    """Move the provenance features into their own TF module.

    They are 56 MB of 412 and serve validation rather than query, so a caller who only
    wants to read or search the corpus should not compile them. Everything inside
    `srcxml` is modelled elsewhere -- wrappers as flags, damage as cluster nodes -- so
    moving it removes no linguistic fact from the main dataset. `check_tags.py` is what
    holds that true: an element with no declared destination fails the build.
    """
    prov = ROOT / PROVENANCE_DIR / TF_VERSION
    prov.mkdir(parents=True, exist_ok=True)
    (prov / "README.md").write_text(
        "# TLHdig-TF provenance module\n\n"
        "`srcxml` (the verbatim source fragment of each sign, editorial markers in\n"
        "place) and `src_span` (its byte range in the file `src_file` names).\n\n"
        "Not needed to read or query the corpus: every tag inside `srcxml` is modelled\n"
        "in the main dataset -- wrappers as `sgr`/`agr`/`det`/`num`, damage as `cluster`\n"
        "nodes with offsets, `corr` and `note` as their own features. What these two add\n"
        "is the byte-exact round trip, which is what Contract A verifies.\n\n"
        "Load it alongside the dataset:\n\n"
        f"    Fabric(locations=['tf/{TF_VERSION}', 'tf-provenance/{TF_VERSION}'])\n\n"
        "or as a Text-Fabric module: `alexsosn/TLHdig-TF/tf-provenance`.\n\n"
        "With it loaded you can define the source-faithful text format that the main\n"
        "dataset can no longer declare on its own:\n\n"
        "    A.dm('{srcxml}{after}')\n",
        encoding="utf8",
    )
    moved = []
    for name in PROVENANCE_FEATURES:
        src = out / f"{name}.tf"
        if src.is_file():
            src.replace(prov / f"{name}.tf")
            moved.append(name)
    return moved


def write_dataset_license(out) -> None:
    """Ship the licence inside the dataset directory.

    Consumers do not necessarily get the repository.  Agora sparse-checkouts only
    `tf/<version>/`, so a licence that lives at the repository root never reaches the
    people actually redistributing the data.
    """
    (out / "LICENSE").write_text(DATASET_LICENSE, encoding="utf8")


def main() -> int:
    out = ROOT / "tf" / TF_VERSION
    patches = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    files = corpus_files()
    print(f"files: {len(files):,}   patches: {len(patches):,}   -> {out}")
    t0 = time.time()
    # The corpus is an immutable release: pin its identity rather than re-deriving the
    # input list, or deleting a source file just lowers every count in step.
    id_file = ROOT / "programs" / "corpus.sha256"
    if id_file.exists():
        problems = corpusid.verify(CORPUS, corpusid.read_manifest(id_file))
        if problems:
            print(f"BUILD FAILED: corpus does not match {id_file.name}")
            for p_ in problems[:10]:
                print("  " + p_)
            return 1
        print(f"corpus identity verified against {id_file.name}")

    allow_file = ROOT / "programs" / "excluded.txt"
    allow = {}
    if allow_file.exists():
        for ln in allow_file.read_text(encoding="utf8").splitlines():
            if not ln.strip() or ln.startswith("#"):
                continue
            path, _, reason = ln.partition("\t")
            allow[path] = reason.strip() or None
    # Clear any stamp from a previous build before the first write.  census.py writes it
    # only after the dataset verifies, but build.py rebuilds in place, so an unverified
    # rebuild used to inherit the old stamp and publish_dataset.sh would accept it.
    stale = out / stamp.STAMP
    if stale.exists():
        stale.unlink()

    ledger = convert.Ledger(allow=allow)
    # load=False: compaction below rewrites every feature file, so any cache TF
    # compiles here is stale before it is used.  census.py does the one load.
    api = convert.build(
        CORPUS, out, keep_empty=False, files=files, patches=patches, ledger=ledger,
        load=False,
    )
    if api is None:
        print("BUILD FAILED")
        return 1
    print("\n" + ledger.report())
    print("\n" + ledger.marker_report())
    if ledger.marker_src != ledger.marker_fed or ledger.marker_fed != ledger.marker_out:
        print("BUILD FAILED: damage markers not conserved (see above)")
        return 1
    if not ledger.allowed():
        print("BUILD FAILED: exclusions do not match programs/excluded.txt")
        return 1
    dt = time.time() - t0

    # TF writes one line per node; grouping nodes that share a value is legal in the
    # format (a node spec denotes a set) and takes morph.tf from 130 MB to 10 MB,
    # keeping every file under GitHub's 100 MB limit.
    write_dataset_license(out)
    res = compact.compact_dir(out)
    saved = sum(b - a for _, b, a in res)
    print(f"compacted {len(res)} features, saved {saved/1e6:.0f} MB")

    moved = split_provenance(out)
    if moved:
        prov = ROOT / PROVENANCE_DIR / TF_VERSION
        size = sum(f.stat().st_size for f in prov.glob("*.tf")) / 1e6
        print(f"provenance module: {', '.join(moved)} -> {prov} ({size:.0f} MB)")

    # Reloading the compacted dataset here used to be part of the build, and it cost a
    # 22-minute failure with the traceback on stderr where nobody saw it: this process
    # already holds the whole graph it just wrote, so a second full load is both the
    # heaviest thing in the run and a self-check on the writer's own output.
    # census.py loads the shipped files in a fresh process and probes section
    # addressing there, which is the check that was actually wanted.
    size = sum(f.stat().st_size for f in out.rglob("*.tf") if f.is_file())
    print(f"\nbuilt in {dt/60:.1f} min   {size/1e6:.0f} MB   -> {out}")
    print("not marked complete yet: run programs/census.py to verify and stamp it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
