#!/usr/bin/env python
"""Learn the reading -> cuneiform tables from a built dataset.

Writes two files, both generated and pinned:

  programs/signmap.tsv        reading -> one codepoint, from lines whose counts match
  programs/signmap-multi.tsv  reading -> a sequence, from the gaps between anchors

Neither is a guess. A reading enters only above an observation floor and a confidence
floor, and both numbers are written into the file so a reader can judge each row. The
one-to-one table was validated against Oracc's sign list at 96.2% agreement
(docs/research-cuneiform-alignment.md §3).

Re-run after a build; the tables feed the *next* build, so a change here takes two
builds to show up in the data. That is deliberate: the tables are inputs, and a table
learned from the same run it feeds would be unfalsifiable.
"""
import sys
import unicodedata as ud
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import TF_VERSION, appcheck, compact, cuneiform
from tlhdig.paths import PROGRAMS, ROOT

MIN_OBS = 5          # a reading seen four times is an anecdote
MIN_CONF = 0.95      # and one that varies is a spelling, not a mapping
MAX_SEQ = 4          # longest compound looked for


def _spellable(seq: str) -> bool:
    """May this codepoint sequence be recorded as the spelling of a reading?

    Two rejections, both measured:

    * not cuneiform at all -- for several numbers `cu` carries the Latin digits
      unrendered, and the table learned `14` -> "14" from 198 observations. Those are
      real observations of the source failing to render, not spellings.
    * containing the damage placeholder. `a+na` -> 𒀀▒𒀀 was learned at 0.986 over 146
      observations, `i+na` -> 𒄿▒𒀀 at 0.970 over 99. High agreement here says the hole
      in the tablet recurs in the same place, not that the hole spells anything. A
      lacuna is the absorption path's business; it must never become lexical.
    """
    return cuneiform.is_sign(seq) and cuneiform.PLACEHOLDER not in seq


def _feat(d, name, lo, hi):
    out = {}
    p = d / f"{name}.tf"
    if not p.is_file():
        return out
    _, body = compact._split(p)
    for nodes, v in compact._parse(body):
        for n in nodes:
            if lo <= n <= hi:
                out[n] = v
    return out


def _write(path, rows, header):
    with path.open("w", encoding="utf8") as f:
        f.write(header)
        f.write("# reading\tcuneiform\tconfidence\ttop_obs\ttotal_obs\tunicode_name\n")
        for tot, reading, seq, conf, top in rows:
            try:
                nm = ud.name(seq[0]) if len(seq) == 1 else f"{len(seq)} signs"
            except ValueError:
                nm = "(unnamed)"
            f.write(f"{reading}\t{seq}\t{conf:.3f}\t{top}\t{tot}\t{nm}\n")


def main() -> int:
    d = ROOT / "tf" / TF_VERSION
    if not (d / "otype.tf").is_file():
        print("no dataset; build first")
        return 1
    r = appcheck.node_ranges(d)
    slo, shi = r["sign"]
    llo, lhi = r["line"]
    cu = _feat(d, "cu", llo, lhi)
    sym = _feat(d, "sym", slo, shi)
    anchor = _feat(d, "anchor", slo, shi)

    line_slots = {}
    _, body = compact._split(d / "oslots.tf")
    implicit = 1
    for raw in body:
        if not raw:
            continue
        if "\t" in raw:
            spec, _, val = raw.partition("\t")
            nodes = compact._nodes_of(spec)
        else:
            nodes = [implicit]
            val = raw
        implicit = max(nodes) + 1
        for n in nodes:
            if llo <= n <= lhi:
                line_slots[n] = [s for s in compact._nodes_of(val) if not anchor.get(s)]

    # --- one to one, from lines whose counts already match
    obs = defaultdict(Counter)
    for ln, text in cu.items():
        ss = line_slots.get(ln, [])
        pts = cuneiform.split_points(text)
        if ss and len(pts) == len(ss):
            for s, ch in zip(ss, pts):
                v = (sym.get(s) or "").strip()
                if v:
                    obs[v][ch] += 1
    one_rows, one = [], {}
    for v, c in obs.items():
        ch, n = c.most_common(1)[0]
        tot = sum(c.values())
        one_rows.append((tot, v, ch, n / tot, n))
        # `one` is what the compound pass uses as anchors, so a rendering failure that
        # got over the thresholds would go on to define the gaps around it. `50` -> "5"
        # is only ever seen once, but `/` -> "°" reached 7 observations at 1.000 before
        # the editorial marks were removed from the alignment view.
        if tot >= MIN_OBS and n / tot >= MIN_CONF and cuneiform.is_sign(ch):
            one[v] = ch
    one_rows.sort(key=lambda x: -x[0])

    # --- compounds, from the gaps between anchors on the remaining lines
    multi = defaultdict(Counter)
    for ln, text in cu.items():
        ss = line_slots.get(ln, [])
        pts = cuneiform.split_points(text)
        if not ss or len(pts) == len(ss):
            continue
        i = 0
        run = []
        for s in ss:
            want = one.get((sym.get(s) or "").strip())
            j = -1
            if want:
                for k in range(i, min(i + MAX_SEQ + 1, len(pts))):
                    if pts[k] == want:
                        j = k
                        break
            if j >= 0:
                if len(run) == 1 and 2 <= j - i <= MAX_SEQ:
                    v = (sym.get(run[0]) or "").strip()
                    if v:
                        multi[v]["".join(pts[i:j])] += 1
                run = []
                i = j + 1
            else:
                run.append(s)
    multi_rows = []
    for v, c in multi.items():
        seq, n = c.most_common(1)[0]
        tot = sum(c.values())
        multi_rows.append((tot, v, seq, n / tot, n))
    multi_rows.sort(key=lambda x: -x[0])
    kept = [
        row for row in multi_rows
        if row[0] >= MIN_OBS and row[3] >= MIN_CONF and _spellable(row[2])
    ]

    _write(PROGRAMS / "signmap.tsv", one_rows,
           "# reading -> cuneiform codepoint, learned from lines where the codepoint\n"
           "# count equals the sign count. Generated by programs/learn_signmap.py.\n")
    _write(PROGRAMS / "signmap-multi.tsv", kept,
           "# reading -> a SEQUENCE of codepoints: one reading written with several\n"
           "# signs, such as MEŠ = 𒈨𒌍. Learned from the gaps between anchors on lines\n"
           f"# whose counts do not match. Kept only above {MIN_OBS} observations and\n"
           f"# {MIN_CONF:.0%} confidence. Generated by programs/learn_signmap.py.\n")
    print(f"one-to-one : {len(one_rows):,} readings, {len(one):,} confident")
    print(f"compound   : {len(multi_rows):,} candidates, {len(kept):,} kept")
    for tot, v, seq, conf, top in kept[:8]:
        print(f"   {v!r:9} -> {seq}   {conf:.2f}  {tot:,} obs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
