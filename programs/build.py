#!/usr/bin/env python
"""Full conversion: corpus -> tf/<tfVersion>/."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import TF_VERSION, compact, convert, repair
from tlhdig.paths import CORPUS, PATCHES, ROOT, corpus_files


def main() -> int:
    out = ROOT / "tf" / TF_VERSION
    patches = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    files = corpus_files()
    print(f"files: {len(files):,}   patches: {len(patches):,}   -> {out}")
    t0 = time.time()
    api = convert.build(CORPUS, out, keep_empty=False, files=files, patches=patches)
    if api is None:
        print("BUILD FAILED")
        return 1
    dt = time.time() - t0

    # TF writes one line per node; grouping nodes that share a value is legal in the
    # format (a node spec denotes a set) and takes morph.tf from 130 MB to 10 MB,
    # keeping every file under GitHub's 100 MB limit.
    res = compact.compact_dir(out)
    saved = sum(b - a for _, b, a in res)
    print(f"compacted {len(res)} features, saved {saved/1e6:.0f} MB")
    counts = {t: len(api.F.otype.s(t)) for t in api.F.otype.all}
    size = sum(f.stat().st_size for f in out.rglob("*.tf"))
    print(f"\nbuilt in {dt/60:.1f} min   {size/1e6:.0f} MB   {sum(counts.values()):,} nodes")
    for t, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {t:<10}{n:>12,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
