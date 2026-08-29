#!/usr/bin/env python
"""Verify programs/patches.yaml: hashes match, every patch applies, results parse.

Also reports how many bytes the repairs touch, so the scope stays auditable -- these
are syntax fixes, not editorial changes.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import repair, source
from tlhdig.paths import CORPUS, PATCHES


def main() -> int:
    manifest = repair.read_manifest(PATCHES)
    stats = Counter()
    reasons = Counter()
    bad = []

    for rel_path, (sha, patches) in manifest.items():
        f = CORPUS / rel_path
        data = f.read_bytes()
        if repair.sha256(data) != sha:
            stats["hash_mismatch"] += 1
            bad.append((rel_path, "hash mismatch"))
            continue
        try:
            out = repair.apply(data, patches, expect_sha=sha)
        except repair.PatchError as e:
            stats["apply_failed"] += 1
            bad.append((rel_path, str(e)[:100]))
            continue
        if not repair.parses(out):
            stats["still_broken"] += 1
            bad.append((rel_path, "does not parse after repair"))
            continue
        try:
            spans = source.scan(out)
            if source.verify_reconstruction(out, spans):
                stats["span_problem"] += 1
                bad.append((rel_path, "span problem after repair"))
                continue
        except Exception as e:
            stats["scan_failed"] += 1
            bad.append((rel_path, f"scan: {e}"))
            continue

        stats["ok"] += 1
        stats["patches"] += len(patches)
        stats["bytes_before"] += sum(len(p.old) for p in patches)
        stats["bytes_after"] += sum(len(p.new) for p in patches)
        stats["file_bytes"] += len(data)
        for p in patches:
            reasons[p.reason] += 1

    print(f"files in manifest : {len(manifest):,}")
    print(f"  verified OK     : {stats['ok']:,}")
    for k in ("hash_mismatch", "apply_failed", "still_broken", "span_problem", "scan_failed"):
        if stats[k]:
            print(f"  {k:<15} : {stats[k]:,}")
    print(f"patches applied   : {stats['patches']:,}")
    pct = stats["bytes_before"] / max(stats["file_bytes"], 1) * 100
    print(f"bytes touched     : {stats['bytes_before']:,} of {stats['file_bytes']:,} ({pct:.3f}%)")
    print("\npatch reasons:")
    for r, n in reasons.most_common():
        print(f"  {n:>5}  {r}")
    for r, why in bad[:10]:
        print(f"  FAIL {r}: {why}")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
