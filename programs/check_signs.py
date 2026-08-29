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

from tlhdig import signs, source
from tlhdig.paths import REPORTS, corpus_files, rel


def main() -> int:
    stats = Counter()
    failures = []
    types = Counter()

    for f in corpus_files():
        data = f.read_bytes()
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
    print(f"tokenise errors  : {stats['tokenise_error']:,}")
    print(f"\nsign types: {dict(types.most_common())}")
    print(f"report -> {out}")
    return 0 if stats["roundtrip_fail"] == 0 and stats["tokenise_error"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
