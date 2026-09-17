#!/usr/bin/env python
"""Full conversion: pinned TLHdig source -> the current tf/<tfVersion>/ build."""
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import (
    PROVENANCE_DIR,
    PROVENANCE_FEATURES,
    TF_VERSION,
    compact,
    convert,
    corpusid,
    cuneiform,
    repair,
)
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
    """Ship the licence inside the dataset directory."""
    (out / "LICENSE").write_text(DATASET_LICENSE, encoding="utf8")


def _validate_current_output_target(target: Path, parent: Path) -> None:
    """Fail closed unless *target* is the active-version direct child of *parent*."""
    if parent.is_symlink():
        raise ValueError(f"current output parent must not be a symlink: {parent}")
    if target.is_symlink():
        raise ValueError(f"current output target must not be a symlink: {target}")
    if target.parent != parent:
        raise ValueError(f"current output must be a direct child of expected parent: {target}")
    if target.name in {"", ".", ".."}:
        raise ValueError(f"invalid current output directory name: {target}")
    if target.name != TF_VERSION:
        raise ValueError(
            f"current output target must use active TF version {TF_VERSION}: {target}"
        )

    resolved_parent = parent.resolve(strict=False)
    resolved_target = target.resolve(strict=False)
    if resolved_target.parent != resolved_parent:
        raise ValueError(f"current output escapes expected parent: {target}")
    if target.exists() and not target.is_dir():
        raise ValueError(f"current output target is not a directory: {target}")


def reset_current_output(
    main_dir: Path,
    provenance_dir: Path,
    *,
    main_parent: Path,
    provenance_parent: Path,
) -> None:
    """Replace exactly the two converter-owned current-version output trees.

    Both paths are validated before either is removed so a suspicious provenance path,
    for example, cannot delete a valid main artifact as a partial side effect.
    """
    _validate_current_output_target(main_dir, main_parent)
    _validate_current_output_target(provenance_dir, provenance_parent)

    for target in (main_dir, provenance_dir):
        if target.exists():
            shutil.rmtree(target)

    main_dir.mkdir(parents=True, exist_ok=False)


def main() -> int:
    main_parent = ROOT / "tf"
    provenance_parent = ROOT / PROVENANCE_DIR
    out = main_parent / TF_VERSION
    provenance = provenance_parent / TF_VERSION

    id_file = ROOT / "programs" / "corpus.sha256"
    allow_file = ROOT / "programs" / "excluded.txt"
    signmap_multi_file = ROOT / "programs" / "signmap-multi.tsv"
    required_inputs = (PATCHES, id_file, allow_file, signmap_multi_file)
    missing_inputs = [path for path in required_inputs if not path.is_file()]
    if missing_inputs:
        print("BUILD FAILED: required preflight input missing")
        for path in missing_inputs:
            print(f"  {path}")
        return 1

    signmap_problems = cuneiform.validate_multi(signmap_multi_file)
    if signmap_problems:
        print("BUILD FAILED: compound sign map is unusable")
        for problem in signmap_problems[:10]:
            print(f"  {problem}")
        return 1

    patches = repair.read_manifest(PATCHES)
    files = corpus_files()
    print(f"files: {len(files):,}   patches: {len(patches):,}   -> {out}")
    t0 = time.time()

    problems = corpusid.verify(CORPUS, corpusid.read_manifest(id_file))
    if problems:
        print(f"BUILD FAILED: corpus does not match {id_file.name}")
        for p_ in problems[:10]:
            print("  " + p_)
        return 1
    print(f"corpus identity verified against {id_file.name}")

    allow = {}
    for ln in allow_file.read_text(encoding="utf8").splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        path, _, reason = ln.partition("\t")
        allow[path] = reason.strip() or None

    reset_current_output(
        out,
        provenance,
        main_parent=main_parent,
        provenance_parent=provenance_parent,
    )

    ledger = convert.Ledger(allow=allow)
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

    write_dataset_license(out)
    res = compact.compact_dir(out)
    saved = sum(b - a for _, b, a in res)
    print(f"compacted {len(res)} features, saved {saved/1e6:.0f} MB")

    moved = split_provenance(out)
    if moved:
        prov = ROOT / PROVENANCE_DIR / TF_VERSION
        size = sum(f.stat().st_size for f in prov.glob("*.tf")) / 1e6
        print(f"provenance module: {', '.join(moved)} -> {prov} ({size:.0f} MB)")

    size = sum(f.stat().st_size for f in out.rglob("*.tf") if f.is_file())
    print(f"\nbuilt in {dt/60:.1f} min   {size/1e6:.0f} MB   -> {out}")
    print("not validated yet: run programs/validate_current.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
