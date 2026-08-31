#!/usr/bin/env python
"""Gate: judge every assigned sign against lists made outside this corpus.

`check_alignment.py` measures agreement with `programs/signmap.tsv`, which is learned
from these same texts. That is a useful regression check and a poor witness: the learned
table records `MEŠ` -> 𒈨 at 0.57 confidence over 197 observations, and those 197 are
exactly the lines where the alignment had shifted. Evidence assembled from the
defendant's testimony acquits every time.

This reads five sign lists made elsewhere, by people who never saw TLHdig, and asks of
every sign in the corpus: do they attest the glyph we assigned to this reading?

The lists disagree with each other, which is why the verdict counts votes rather than
declaring a right answer. Four houses agreeing against us is a finding. Two houses
splitting is a fact about the sign.

The lists live in `refs/`, are git-ignored, and are never redistributed -- their licences
run from MIT to AGPL. What leaves this program is agreement counts and a disagreement
list, which are facts about our data, not copies of theirs.
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import TF_VERSION, appcheck, compact, signrefs
from tlhdig.paths import REPORTS, ROOT

REFS = ROOT / "refs"

# Readings that stand for the absence of a legible sign. No sign list has an entry for
# them and none should: `x` is a trace nobody could identify, `…` is a gap.
NOT_READINGS = {"x", "…", ""}

# Of the signs the lists can judge, how many may they outvote before the build is wrong?
# Measured at 1.39%; this sits a little above it, tight enough that a regression trips
# it and loose enough that an ordinary change does not.
#
# The first run said 2.99%, and half of that was an artefact of comparing codepoints
# instead of signs -- see `signrefs.equivalents`. What is left is not a defect count
# either. Some is the lists' own indexing: they file a reading under its head sign, so
# `BANŠUR` 𒌷𒍏 reads as a disagreement with 𒌷 when it is not. Some is genuine local
# usage: this corpus writes `2` as 𒁹𒁹 seven thousand times where the lists give the
# dedicated 𒈫, and for these tablets we are right. This is a limit on how far we may
# drift from outside opinion without noticing, not a tally of mistakes.
CEILING_OUTVOTED = 0.015


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


def main() -> int:
    if not REFS.is_dir() or not any(REFS.glob("*")):
        print(f"no external sign lists in {REFS}; skipping (see programs/tlhdig/signrefs.py)")
        return 0
    refs = signrefs.load(REFS)
    present = sorted({s for v in refs.table.values() for s in v})
    lineages = sorted({signrefs.LINEAGE.get(s, s) for s in present})
    print(f"external lists loaded: {', '.join(present)}  ({len(refs):,} readings)")
    print(f"  distinct traditions behind them: {', '.join(lineages)}")

    d = ROOT / "tf" / TF_VERSION
    if not (d / "cu_sign.tf").is_file():
        print("no alignment in this dataset; build first")
        return 1
    r = appcheck.node_ranges(d)
    llo, lhi = r["line"]
    slo, shi = r["sign"]

    sym = _feat(d, "sym", slo, shi)
    cu_sign = _feat(d, "cu_sign", slo, shi)
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
                    line_of[s] = n
    level = {}
    for nodes, v in compact._parse(compact._split(d / "cu_aligned.tf")[1]):
        for n in nodes:
            if llo <= n <= lhi:
                level[n] = int(v or 0)

    judged = Counter()
    by_level = defaultdict(Counter)
    outvoted = Counter()
    contested = Counter()
    for s, glyph in cu_sign.items():
        if anchor.get(s) or not glyph:
            continue
        reading = (sym.get(s) or "").strip()
        lv = level.get(line_of.get(s), 0)
        if reading in NOT_READINGS:
            judged["placeholder, no list applies"] += 1
            continue
        v = refs.verdict(reading, glyph)
        if v.unknown:
            judged["no list knows the reading"] += 1
            by_level[lv]["unknown"] += 1
        elif v.support and not v.against:
            judged["every list that knows it agrees"] += 1
            by_level[lv]["agree"] += 1
        elif v.support:
            judged["the lists are split"] += 1
            by_level[lv]["split"] += 1
            contested[(reading, glyph)] += 1
        else:
            judged["every list that knows it disagrees"] += 1
            by_level[lv]["outvoted"] += 1
            outvoted[(reading, glyph, tuple(sorted(v.alternatives))[:2], v.against)] += 1

    total = sum(judged.values())
    lines = [
        "# The alignment judged from outside",
        "",
        "Generated by `programs/check_signrefs.py`. Every assigned sign is looked up in",
        "sign lists made elsewhere, by people who never saw this corpus, and the vote is",
        "counted. `signmap.tsv` is learned from these same texts and cannot do this.",
        "",
        f"Lists read: {', '.join(present)} — {len(refs):,} readings between them.",
        "",
        f"They stand for {len(lineages)} traditions, not {len(present)} opinions: "
        f"{', '.join(lineages)}. Enmerkar is an OGSL consumer by its own account and",
        "tfFromAtf descends from a Šašková sign list, so a count of agreeing *lists* is",
        "not a count of independent agreement.",
        "",
        "| | signs | |",
        "|---|---:|---:|",
    ]
    for k in ("every list that knows it agrees", "the lists are split",
              "every list that knows it disagrees", "no list knows the reading",
              "placeholder, no list applies"):
        n = judged[k]
        lines.append(f"| {k} | {n:,} | {n / total * 100:.1f}% |")
    lines += ["", "By how the line was aligned:", "",
              "| level | agree | split | outvoted | unknown | outvoted of judged |",
              "|---:|---:|---:|---:|---:|---:|"]
    for lv in sorted(by_level):
        c = by_level[lv]
        j = c["agree"] + c["split"] + c["outvoted"]
        rate = f"{c['outvoted'] / j * 100:.2f}%" if j else "--"
        lines.append(
            f"| {lv} | {c['agree']:,} | {c['split']:,} | {c['outvoted']:,} "
            f"| {c['unknown']:,} | {rate} |"
        )
    lines += ["", "## Where every list disagrees with us", "",
              "A reading we write one way and every list that knows it writes another.",
              "These are candidates for a bug in our conversion, a quirk of the HPM font,",
              "or a genuine Hittite usage the lists do not cover — the counts say which",
              "deserve looking at first.", "",
              "| reading | ours | the lists say | lists | signs |", "|---|---|---|---:|---:|"]
    for (reading, glyph, alts, n_against), n in outvoted.most_common(25):
        lines.append(f"| `{reading}` | {glyph} | {' '.join(alts)} | {n_against} | {n:,} |")
    if contested:
        lines += ["", "## Where the lists disagree with each other", "",
                  "Our glyph has support, but not unanimous support. The sign's identity",
                  "is contested between houses; we are not the outlier.", "",
                  "| reading | ours | signs |", "|---|---|---:|"]
        for (reading, glyph), n in contested.most_common(15):
            lines.append(f"| `{reading}` | {glyph} | {n:,} |")
    lines.append("")

    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "signrefs.md").write_text("\n".join(lines) + "\n", encoding="utf8")
    print("\n".join(lines[:40]))

    j = judged["every list that knows it agrees"] + judged["the lists are split"] \
        + judged["every list that knows it disagrees"]
    if not j:
        print("no sign could be judged; is refs/ populated?")
        return 1
    rate = judged["every list that knows it disagrees"] / j
    print(f"\njudged {j:,} signs; outvoted on {rate * 100:.2f}%")
    if rate > CEILING_OUTVOTED:
        print("SIGNREFS GATE FAILED:")
        print(f"  outside opinion contradicts {rate * 100:.2f}% of judged signs, "
              f"over the {CEILING_OUTVOTED * 100:.1f}% ceiling")
        return 1
    print("outside opinion holds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
