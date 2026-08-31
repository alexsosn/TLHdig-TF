#!/usr/bin/env python
"""Gate: is the cuneiform laid out per sign, and is each assignment *permitted*?

Reads the `.tf` files directly, so it runs in seconds and can sit in CI beside
check_structure.py rather than waiting on a Text-Fabric load.

Coverage alone cannot fail a wrong build. An earlier version of this gate checked two
floors -- how many signs carry `cu_sign` and how many lines aligned exactly -- and a
build could have preserved every one of them while corrupting what they pointed at.
It did: 14.1% of the level-2 assignments in the previous release put a legible sign on
a damage placeholder or the reverse, and the gate stayed green throughout.

So the checks here are of two kinds.

**Invariants** are properties the aligner is supposed to guarantee, and any violation is
a defect in it, not a judgement call:

* every `cu_sign` is cuneiform, a Private Use codepoint, or the placeholder;
* no multi-codepoint value contains the placeholder -- a hole in the tablet is not part
  of the spelling of a word;
* `x` and the placeholder correspond exactly, in both directions.

**Agreement** is measured against `signmap.tsv`, which the aligner never reads. It is
learned from level-1 lines only, so for levels 2, 3 and 4 it is an independent witness
and its ceiling is enforced. For level 1 it is partly the same evidence twice, and the
independent check there is Oracc's sign list (docs/research-cuneiform-alignment.md §3).
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import TF_VERSION, appcheck, compact, cuneiform
from tlhdig.paths import PROGRAMS, REPORTS, ROOT

PH = cuneiform.PLACEHOLDER

# Coverage. Raise these when coverage improves. Lowering one is a decision to publish
# less than the last build did, so it needs a reason in the commit message -- never
# "the gate went red".
#
# Lowered once, deliberately, from 3,017,385. Constraining absorption to the measured
# `x` <-> placeholder correspondence withdrew 220,049 assignments and took level 2 from
# 16.65% disagreement with the independent table to 1.14%. Counting only the assignments
# the table can judge: 156,579 disagreed before and 7,830 after, so 148,749 of the
# 253,547 withdrawn were disagreements -- 58.7% of what was given up was wrong.
# Coverage bought at that price was not coverage.
FLOOR_SIGNS = 2_840_000
FLOOR_EXACT = 190_000          # cu_aligned == 1

# Agreement with the independent table, per level. These are ceilings: a mechanism may
# not get less accurate than it was measured to be. Set just above what the current
# build measures (1.15%, 0.25%, 0.00%), so a regression trips them rather than being
# absorbed. Level 1 is reported but not enforced, being learned from the same lines.
CEILING = {2: 0.015, 3: 0.005, 4: 0.005}

LABEL = {
    0: "not aligned",
    1: "counts matched, zipped",
    2: "damage placeholders absorbed",
    3: "compound logogram expanded",
    4: "numeral derived",
}


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


def _confident():
    """The learned one-to-one table, at the thresholds the learner itself uses."""
    out = {}
    p = PROGRAMS / "signmap.tsv"
    if not p.is_file():
        return out
    for line in p.read_text(encoding="utf8").splitlines():
        if not line or line.startswith("#"):
            continue
        f = line.split("\t")
        if len(f) >= 5 and int(f[3]) >= 5 and float(f[2]) >= 0.95 and cuneiform.is_sign(f[1]):
            out[f[0]] = f[1]
    return out


def main() -> int:
    d = ROOT / "tf" / TF_VERSION
    if not (d / "cu_aligned.tf").is_file():
        print("no alignment in this dataset; build first")
        return 1
    r = appcheck.node_ranges(d)
    llo, lhi = r["line"]
    slo, shi = r["sign"]

    levels = Counter()
    for nodes, v in compact._parse(compact._split(d / "cu_aligned.tf")[1]):
        levels[int(v or 0)] += sum(1 for n in nodes if llo <= n <= lhi)

    methods = Counter()
    if (d / "cu_method.tf").is_file():
        for nodes, v in compact._parse(compact._split(d / "cu_method.tf")[1]):
            if v:
                methods[v] += sum(1 for n in nodes if llo <= n <= lhi)

    cu_sign = _feat(d, "cu_sign", slo, shi)
    sym = _feat(d, "sym", slo, shi)
    anchor = _feat(d, "anchor", slo, shi)

    line_of = {}
    implicit = 1
    for raw in compact._split(d / "oslots.tf")[1]:
        if "\t" in raw:
            spec, _, val = raw.partition("\t")
            nodes = compact._nodes_of(spec)
            if not nodes:
                continue
        else:
            nodes, val = [implicit], raw
        implicit = max(nodes) + 1
        for n in nodes:
            if llo <= n <= lhi:
                for s in compact._nodes_of(val):
                    if not anchor.get(s):
                        line_of[s] = n
    lvl_of = {}
    for nodes, v in compact._parse(compact._split(d / "cu_aligned.tf")[1]):
        for n in nodes:
            if llo <= n <= lhi:
                lvl_of[n] = int(v or 0)

    conf = _confident()
    broken = Counter()
    examples = defaultdict(list)
    checked = Counter()
    disagree = Counter()

    for s, v in cu_sign.items():
        if not v:
            continue
        k = (sym.get(s) or "").strip()
        lv = lvl_of.get(line_of.get(s), 0)
        if not cuneiform.is_sign(v):
            broken["not a sign"] += 1
            if len(examples["not a sign"]) < 5:
                examples["not a sign"].append((k, v))
        if len(v) > 1 and PH in v:
            broken["damage inside a spelling"] += 1
            if len(examples["damage inside a spelling"]) < 5:
                examples["damage inside a spelling"].append((k, v))
        if (v == PH) != (k == cuneiform.ILLEGIBLE):
            broken["`x` and the placeholder disagree"] += 1
            if len(examples["`x` and the placeholder disagree"]) < 5:
                examples["`x` and the placeholder disagree"].append((k, v))
        want = conf.get(k)
        if want is not None and len(v) == 1:
            checked[lv] += 1
            if v != want:
                disagree[lv] += 1

    signs = len(cu_sign)
    total_lines = sum(levels.values())
    total_signs = shi - slo + 1

    out = [
        "# Cuneiform alignment coverage",
        "",
        "Generated by `programs/check_alignment.py`. How much of the line-level `cu`",
        "is laid out per sign, by which mechanism, and how far each mechanism agrees",
        "with the independently learned reading -> sign table.",
        "",
        "| level | meaning | lines | | disagrees with `signmap.tsv` |",
        "|---:|---|---:|---:|---:|",
    ]
    for lv in sorted(levels):
        n = levels[lv]
        rate = (
            f"{disagree[lv] / checked[lv] * 100:.2f}% of {checked[lv]:,}"
            if checked[lv] else "--"
        )
        note = " (same evidence)" if lv == 1 else ""
        out.append(
            f"| {lv} | {LABEL.get(lv, '?')} | {n:,} | {n / total_lines * 100:.1f}% | {rate}{note} |"
        )
    out += ["", "Mechanisms actually run, which the level alone cannot say:", ""]
    for m, n in methods.most_common():
        out.append(f"- `{m}`: {n:,} lines")
    out += [
        "",
        f"- signs carrying `cu_sign`: **{signs:,}** of {total_signs:,} "
        f"({signs / total_signs * 100:.1f}%)",
        "",
        "Level 1 is checked against a table learned from level-1 lines, so that column",
        "is the same evidence twice and is reported, not enforced; its independent",
        "check is Oracc's sign list (research §3). Levels 2-4 the table never saw.",
        "",
    ]
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "alignment.md").write_text("\n".join(out) + "\n", encoding="utf8")
    print("\n".join(out))

    problems = []
    for what, n in broken.items():
        problems.append(f"{n:,} assignments the aligner should never make: {what} "
                        f"-- e.g. {examples[what][:3]}")
    if signs < FLOOR_SIGNS:
        problems.append(f"signs with cu_sign fell: {signs:,} < {FLOOR_SIGNS:,}")
    if levels[1] < FLOOR_EXACT:
        problems.append(f"exact alignments fell: {levels[1]:,} < {FLOOR_EXACT:,}")
    for lv, ceil in CEILING.items():
        if checked[lv] and disagree[lv] / checked[lv] > ceil:
            problems.append(
                f"level {lv} disagrees with the independent table on "
                f"{disagree[lv] / checked[lv] * 100:.2f}% of {checked[lv]:,} "
                f"assignments, over the {ceil * 100:.1f}% ceiling"
            )
    if problems:
        print("ALIGNMENT GATE FAILED:")
        for p in problems:
            print("  " + p)
        return 1
    print("alignment holds: coverage above the floors, every assignment permitted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
