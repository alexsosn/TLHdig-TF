#!/usr/bin/env python
"""Gate: judge every assigned sign against lists made outside this corpus.

`check_alignment.py` measures agreement with `programs/signmap.tsv`, which is learned
from these same texts. That is a useful regression check and a poor witness: the learned
table records `MEŠ` -> 𒈨 at 0.57 confidence over 197 observations, and those 197 are
exactly the lines where the alignment had shifted. Evidence assembled from the
defendant's testimony acquits every time.

This reads six sign lists made elsewhere, by people who never saw TLHdig, and asks of
every sign in the corpus: do they attest the glyph we assigned to this reading?

The lists disagree with each other, which is why the verdict counts votes rather than
declaring a right answer. Four houses agreeing against us is a finding. Two houses
splitting is a fact about the sign.

The files live transiently in git-ignored `refs/`. `programs/signrefs.lock.json` pins the
exact upstream revision and content identity for every input; `fetch_signrefs.py`
acquires them. This checker refuses a partial, changed, malformed or unpinned source set
before the scholarly vote can run.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import TF_VERSION, appcheck, compact, signref_inputs, signrefs
from tlhdig.paths import PROGRAMS, REPORTS, ROOT

REFS = ROOT / "refs"
LOCK = PROGRAMS / "signrefs.lock.json"
STATUS = REPORTS / "signrefs-status.json"

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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("ordinary", "release"), default="ordinary")
    parser.add_argument("--lock", type=Path, default=LOCK)
    parser.add_argument("--refs", type=Path, default=REFS)
    parser.add_argument("--status", type=Path, default=STATUS)
    return parser


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


def _loaded_source_counts(refs: signrefs.References) -> Counter:
    counts = Counter()
    for by_source in refs.table.values():
        for source in by_source:
            counts[source] += 1
    return counts


def _write_state(state: str, acquisition: signref_inputs.Result, *, mode: str, status: Path) -> int:
    result = signref_inputs.Result(state, acquisition.sources)
    signref_inputs.write_status(status, result, mode=mode)
    print(f"SIGNREFS_CHECK_STATUS={state}")
    return signref_inputs.exit_code(state, mode=mode)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        sources = signref_inputs.load_lock(args.lock)
    except signref_inputs.LockError as exc:
        print(f"SIGNREFS INPUT LOCK FAILED: {exc}")
        return 1

    acquisition = signref_inputs.inspect_local(sources, args.refs)
    if acquisition.state != signref_inputs.PASSED:
        for source in acquisition.sources:
            detail = f" ({source.detail})" if source.detail else ""
            print(f"  {source.name}: {source.state}{detail}")
        return _write_state(
            acquisition.state,
            acquisition,
            mode=args.mode,
            status=args.status,
        )

    try:
        refs = signrefs.load(args.refs)
    except Exception as exc:
        # Integrity already passed. A parser failure is therefore a malformed/unsupported
        # locked source, never an availability skip.
        print(f"SIGNREFS PARSE FAILED: {type(exc).__name__}: {exc}")
        return _write_state(
            signref_inputs.FAILED,
            acquisition,
            mode=args.mode,
            status=args.status,
        )

    counts = _loaded_source_counts(refs)
    expected = {source.name for source in sources}
    loaded = set(counts)
    missing = sorted(expected - loaded)
    unexpected = sorted(loaded - expected)
    if missing or unexpected:
        if missing:
            print(f"SIGNREFS PARSE FAILED: verified sources produced no readings: {', '.join(missing)}")
        if unexpected:
            print(f"SIGNREFS LOCK FAILED: unpinned sources entered the vote: {', '.join(unexpected)}")
        return _write_state(
            signref_inputs.FAILED,
            acquisition,
            mode=args.mode,
            status=args.status,
        )

    present = sorted(loaded)
    lineages = sorted({signrefs.LINEAGE.get(s, s) for s in present})
    print(f"external lists loaded: {', '.join(present)}  ({len(refs):,} readings)")
    print(f"  distinct traditions behind them: {', '.join(lineages)}")
    print("  readings by source: " + ", ".join(f"{s}={counts[s]:,}" for s in present))

    d = ROOT / "tf" / TF_VERSION
    if not (d / "cu_sign.tf").is_file():
        print("no alignment in this dataset; build first")
        return _write_state(
            signref_inputs.FAILED,
            acquisition,
            mode=args.mode,
            status=args.status,
        )
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
    if not total:
        print("no assigned sign reached the external-reference judgement")
        return _write_state(
            signref_inputs.FAILED,
            acquisition,
            mode=args.mode,
            status=args.status,
        )

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
        print("no sign could be judged; external lists parsed but know none of this corpus")
        return _write_state(
            signref_inputs.FAILED,
            acquisition,
            mode=args.mode,
            status=args.status,
        )
    rate = judged["every list that knows it disagrees"] / j
    print(f"\njudged {j:,} signs; outvoted on {rate * 100:.2f}%")
    if rate > CEILING_OUTVOTED:
        print("SIGNREFS GATE FAILED:")
        print(f"  outside opinion contradicts {rate * 100:.2f}% of judged signs, "
              f"over the {CEILING_OUTVOTED * 100:.1f}% ceiling")
        return _write_state(
            signref_inputs.FAILED,
            acquisition,
            mode=args.mode,
            status=args.status,
        )
    print("outside opinion holds")
    return _write_state(
        signref_inputs.PASSED,
        acquisition,
        mode=args.mode,
        status=args.status,
    )


if __name__ == "__main__":
    raise SystemExit(main())
