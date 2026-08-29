#!/usr/bin/env python
"""Full conversion: corpus -> tf/<tfVersion>/."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import SOURCE_VERSION, TF_VERSION, compact, convert, corpusid, repair
from tlhdig.paths import CORPUS, PATCHES, ROOT, corpus_files


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
    ledger = convert.Ledger(allow=allow)
    api = convert.build(
        CORPUS, out, keep_empty=False, files=files, patches=patches, ledger=ledger
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
    res = compact.compact_dir(out)
    saved = sum(b - a for _, b, a in res)
    print(f"compacted {len(res)} features, saved {saved/1e6:.0f} MB")

    # The compactor rewrites every node feature in place, so the files that ship are
    # not the ones convert.build() loaded.  Reload and re-query before reporting.
    from tf.fabric import Fabric

    TF = Fabric(locations=str(out), silent="deep")
    api = TF.loadAll(silent="deep") or TF.api
    if api is None:
        print("BUILD FAILED: compacted dataset does not load")
        return 1
    probe = api.T.nodeFromSection(("KUB 21.8", "Vs. II", "1\u2032"))
    if probe is None:
        print("BUILD FAILED: section addressing broken after compaction")
        return 1
    print("compacted dataset reloads and answers a section query")

    # Mark the build complete. Committing tf/ while a build is still running captured
    # an uncompacted 124 MB morph.tf once and GitHub rejected the push; the marker
    # makes "is this dataset finished?" answerable without watching the log.
    (out / "BUILD-COMPLETE").write_text(
        f"sourceVersion={SOURCE_VERSION}\ntfVersion={TF_VERSION}\n", encoding="utf8"
    )
    counts = {t: len(api.F.otype.s(t)) for t in api.F.otype.all}
    size = sum(f.stat().st_size for f in out.rglob("*.tf") if f.is_file())
    print(f"\nbuilt in {dt/60:.1f} min   {size/1e6:.0f} MB   {sum(counts.values()):,} nodes")
    for t, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {t:<10}{n:>12,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
