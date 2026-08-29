#!/usr/bin/env python
"""Milestone 0 (plan §8.0): build a shard under both slot policies and compare.

Decides from measurement whether contentless tokens become slots.
"""
import resource
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import convert, repair
from tlhdig.paths import CORPUS, PATCHES, REPORTS, corpus_files


def rss_mb() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / (1024 * 1024) if sys.platform == "darwin" else r / 1024


def run(files, out, keep_empty, patches):
    t0 = time.time()
    api = convert.build(CORPUS, out, keep_empty=keep_empty, files=files, patches=patches)
    build_s = time.time() - t0
    if api is None:
        return None
    counts = {t: len(api.F.otype.s(t)) for t in api.F.otype.all}
    total = sum(counts.values())
    t1 = time.time()
    _ = [api.F.sym.v(n) for n in api.F.otype.s("sign")[:20000]]
    scan_s = time.time() - t1
    size = sum(f.stat().st_size for f in out.rglob("*.tf"))
    return dict(build_s=build_s, scan_s=scan_s, counts=counts, total=total, size=size)


def main() -> int:
    files = corpus_files()
    shard = files[::20]           # 5% deterministic shard
    patches = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    print(f"shard: {len(shard):,} of {len(files):,} files\n")

    results = {}
    for keep in (False, True):
        out = Path("/tmp/tlhdig-bench") / ("keep" if keep else "drop")
        r = run(shard, out, keep, patches)
        if r is None:
            print(f"keep_empty={keep}: BUILD FAILED")
            continue
        results[keep] = r
        label = "slots include empty" if keep else "empty excluded"
        print(f"--- {label} ---")
        print(f"  build      : {r['build_s']:6.1f}s")
        print(f"  feature scan (20k signs): {r['scan_s']*1000:6.1f}ms")
        print(f"  .tf on disk: {r['size']/1e6:6.1f} MB")
        print(f"  nodes      : {r['total']:,}")
        for t, n in sorted(r["counts"].items(), key=lambda x: -x[1]):
            print(f"     {t:<10}{n:>10,}")
        print()

    if len(results) == 2:
        d, k = results[False], results[True]
        scale = len(files) / len(shard)
        print("=== projected to the full corpus ===")
        print(f"{'':<22}{'empty excluded':>18}{'empty as slots':>18}")
        for key, fmt in (("total", "{:,.0f}"), ("size", "{:,.0f}")):
            a, b = d[key] * scale, k[key] * scale
            unit = " nodes" if key == "total" else " bytes"
            print(f"  {key+unit:<20}{fmt.format(a):>18}{fmt.format(b):>18}")
        print(f"  {'slots':<20}{d['counts']['sign']*scale:>18,.0f}{k['counts']['sign']*scale:>18,.0f}")
        print(f"  {'build time':<20}{d['build_s']*scale:>17.0f}s{k['build_s']*scale:>17.0f}s")
        growth = (k["counts"]["sign"] - d["counts"]["sign"]) / d["counts"]["sign"] * 100
        print(f"\n  keeping empty tokens grows the slot count by {growth:.1f}%")
    print(f"\npeak RSS: {rss_mb():.0f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
