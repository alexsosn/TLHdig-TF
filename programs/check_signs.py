#!/usr/bin/env python
"""Sign tokeniser gate: srcxml + after must reproduce every <w>'s source bytes.

This is the Contract A test that the earlier prototype could not perform, because it
compared serialised output against itself.  Here the comparison is against the actual
bytes of the file, sliced by source.py.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import repair, signs, source
from tlhdig.paths import PATCHES, PROGRAMS, REPORTS, corpus_files, rel


def known_lossy() -> dict[str, str]:
    """Files that cannot round-trip, with the reason, checked in alongside the code.

    The gate demands 100% everywhere else; this list means a *new* lossy file fails
    rather than disappearing into a percentage tolerance.
    """
    f = PROGRAMS / "known_lossy.txt"
    if not f.exists():
        return {}
    out = {}
    for ln in f.read_text(encoding="utf8").splitlines():
        if ln.strip() and not ln.startswith("#"):
            path, _, reason = ln.partition("\t")
            out[path] = reason.strip()
    return out


def main() -> int:
    stats = Counter()
    failures = []
    types = Counter()
    allowed = known_lossy()
    unexpected: set[str] = set()

    # The converter applies programs/patches.yaml before it reads a file, and 173 files
    # convert only because of that. Scanning raw bytes here skipped exactly those
    # documents, so a tokenisation defect living only in repaired content was outside
    # this gate entirely.
    man = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    for f in corpus_files():
        data = f.read_bytes()
        entry = man.get(rel(f))
        if entry:
            try:
                data = repair.apply(data, entry[1], expect_sha=entry[0])
                stats["file_repaired"] += 1
            except repair.PatchError:
                stats["patch_failed"] += 1
                continue
        try:
            spans = source.scan(data)
        except Exception:
            stats["file_unparseable"] += 1
            continue
        stats["file_ok"] += 1

        for sp in spans:
            if sp.tag != "w":
                continue
            inner = source.inner_bytes(data, sp)
            stats["words"] += 1
            try:
                got = signs.tokenise_word(inner)
            except Exception as e:
                stats["tokenise_error"] += 1
                if len(failures) < 5000:
                    failures.append((rel(f), "error", type(e).__name__, inner[:100].decode("utf8", "replace")))
                continue
            stats["signs"] += len(got)
            for s in got:
                types[s.type] += 1
            rebuilt = "".join(s.srcxml + s.after for s in got).encode("utf8")
            # The filtered round-trip is the one that matters: the converter keeps
            # only non-empty tokens as slots, so anything an empty token still holds
            # would be lost from the dataset.
            kept = "".join(
                s.srcxml + s.after for s in got if s.type != "empty"
            ).encode("utf8")
            all_empty = all(s.type == "empty" for s in got)
            if all_empty or kept == inner:
                stats["filtered_ok"] += 1
            else:
                stats["filtered_fail"] += 1
                stats["filtered_lost_bytes"] += max(len(inner) - len(kept), 0)
                if rel(f) not in allowed:
                    unexpected.add(rel(f))
            if rebuilt == inner:
                stats["roundtrip_ok"] += 1
            else:
                stats["roundtrip_fail"] += 1
                if len(failures) < 5000:
                    failures.append(
                        (rel(f), "mismatch",
                         inner[:110].decode("utf8", "replace"),
                         rebuilt[:110].decode("utf8", "replace"))
                    )

    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / "signs_roundtrip.tsv"
    with out.open("w", encoding="utf8") as fh:
        fh.write("file\tkind\toriginal\trebuilt\n")
        for r in failures:
            fh.write("\t".join(str(x) for x in r) + "\n")

    w = stats["words"]
    ok = stats["roundtrip_ok"]
    print(f"files            : {stats['file_ok']:,}  (unparseable {stats['file_unparseable']:,})")
    print(f"<w> tokenised    : {w:,}")
    print(f"signs produced   : {stats['signs']:,}  (avg {stats['signs']/max(w,1):.2f} per word)")
    print(f"round-trip OK    : {ok:,}  ({ok/max(w,1)*100:.4f}%)")
    print(f"round-trip FAIL  : {stats['roundtrip_fail']:,}")
    print(f"filtered OK      : {stats['filtered_ok']:,}  "
          f"({stats['filtered_ok']/max(w,1)*100:.4f}%)")
    print(f"filtered FAIL    : {stats['filtered_fail']:,}"
          f"  ({stats['filtered_lost_bytes']:,} bytes would be lost)")
    print(f"  in known-lossy list: {stats['filtered_fail'] - len(unexpected):,}")
    if unexpected:
        print(f"  NOT on the list  : {len(unexpected):,}")
        for r in sorted(unexpected)[:10]:
            print(f"     {r}")
    print(f"tokenise errors  : {stats['tokenise_error']:,}")
    print(f"\nsign types: {dict(types.most_common())}")
    print(f"report -> {out}")
    return 0 if not (
        stats["roundtrip_fail"] or stats["tokenise_error"] or unexpected
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
