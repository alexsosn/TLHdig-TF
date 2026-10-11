"""Read-only evidence inventory for #21 alignment gaps and #23 sign disagreements.

Every record retains alternatives and overlapping candidate flags. Never vote a
replacement into cu_sign. Generated JSONL reports are research, not corrections.
"""
from __future__ import annotations
import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path

from tlhdig import TF_VERSION, appcheck, compact, cuneiform, signrefs, signref_inputs
from tlhdig.paths import ROOT, PROGRAMS, REPORTS


def is_pua(ch):
    n = ord(ch)
    return 0xE000 <= n <= 0xF8FF or 0xF0000 <= n <= 0xFFFFD or 0x100000 <= n <= 0x10FFFD


def classify_gap(cu, syms, multi):
    points = cuneiform.split_points(cu)
    flags = []
    if cuneiform.UNRENDERED_SOURCE in cu:
        flags.append("unrendered")
    if any(is_pua(c) for c in cu):
        flags.append("pua")
    if cuneiform.PLACEHOLDER in points:
        flags.append("placeholder")
        if points.count(cuneiform.PLACEHOLDER) != syms.count(cuneiform.ILLEGIBLE):
            flags.append("damage-count-mismatch")
    if any(s in multi for s in syms):
        flags.append("compound")
    if any(cuneiform.numeral(s) is not None for s in syms):
        flags.append("numeral")
    if any(c in cu for c in "?|°"):
        flags.append("editorial")
    if len(points) != len(syms):
        flags.append("count-mismatch")
    if not cu:
        primary = "no-cu"
    elif not syms:
        primary = "no-sign-slots"
    else:
        primary = next((v for v in ("unrendered", "pua", "damage-count-mismatch",
                  "compound", "numeral", "editorial", "count-mismatch") if v in flags), "unknown")
    return dict(primary=primary, flags=flags, points=len(points), slots=len(syms),
                delta=len(points) - len(syms),
                puaCodepoints=sorted({f"U+{ord(c):04X}" for c in cu if is_pua(c)}))


def equivalence_representatives(refs):
    """Build transitive sign-identity classes without changing source spellings.

    signrefs.References._same() stores direct associations; chains between HZL and
    OSL may require closure. The representative is stable and only used for
    diagnostic comparison -- never to rewrite a source's cu glyph.
    """
    parent = {}

    def root(glyph):
        parent.setdefault(glyph, glyph)
        while parent[glyph] != glyph:
            parent[glyph] = parent[parent[glyph]]
            glyph = parent[glyph]
        return glyph

    for glyph, related in refs.equiv.items():
        a = root(glyph)
        for other in related:
            b = root(other)
            if a != b:
                parent[max(a, b)] = min(a, b)
                a = root(a)
    return {glyph: root(glyph) for glyph in parent}


def classify_disagreement(reading, glyph, refs, canonical=None):
    """Classify raw reference votes separately from independent-lineage evidence."""
    v = refs.verdict(reading, glyph)
    status = ("unknown" if v.unknown else
              "split" if v.support and v.against else
              "supported" if v.support else "all-disagree")
    candidates = {k: sorted(vals) for k, vals in sorted(refs.table.get(reading, {}).items())}
    if canonical is None:
        canonical = equivalence_representatives(refs)

    def representative(g):
        return canonical.get(g, g)

    classes = {representative(g) for values in candidates.values() for g in values}
    assigned = representative(glyph)
    lineages = {}
    for source, source_glyphs in candidates.items():
        lineage = signrefs.LINEAGE.get(source, source)
        group = lineages.setdefault(lineage, [])
        group.append((source, {representative(g) for g in source_glyphs}))

    votes = {}
    opposed_alternatives = []
    for lineage, sources in sorted(lineages.items()):
        support = [assigned in classes_ for _, classes_ in sources]
        if all(support):
            kind = "supports"
        elif any(support):
            kind = "mixed"
        else:
            kind = "opposes"
            opposed_alternatives.append(set().union(*(cs for _, cs in sources)))
        votes[lineage] = {"vote": kind, "sources": sorted(src for src, _ in sources)}

    opposed = sum(vote["vote"] == "opposes" for vote in votes.values())
    consensus = (set.intersection(*opposed_alternatives)
                 if len(opposed_alternatives) >= 2 else set())
    return dict(status=status, reference_conflict=refs.contested(reading),
                equivalenceAwareReferenceConflict=len(classes) > 1,
                sourceCandidates=candidates, sources=len(candidates),
                traditions=len(refs.lineages(reading)),
                opposingTraditions=opposed,
                supportingTraditions=sum(x["vote"] == "supports" for x in votes.values()),
                mixedTraditions=sum(x["vote"] == "mixed" for x in votes.values()),
                lineageVotes=votes,
                independentConsensus=bool(consensus),
                independentConsensusAlternatives=sorted(consensus),
                equivalenceAwareSupport=v.support,
                equivalenceAwareAgainst=v.against,
                alternatives=sorted(v.alternatives))

def feat(directory, name, lo, hi):
    path = directory / (name + ".tf")
    if not path.is_file():
        return {}
    return {n: value for nodes, value in compact._parse(compact._split(path)[1])
            for n in nodes if lo <= n <= hi}


def line_to_sign(directory, low, high):
    owners, slots = {}, defaultdict(list)
    implicit = 1
    for raw in compact._split(directory / "oslots.tf")[1]:
        if "\t" in raw:
            key, _, val = raw.partition("\t")
            nodes = compact._nodes_of(key)
            if not nodes:
                continue
        else:
            nodes, val = [implicit], raw
        implicit = max(nodes) + 1
        for node in nodes:
            if low <= node <= high:
                for sign in compact._nodes_of(val):
                    owners[sign] = node
                    slots[node].append(sign)
    return owners, slots


def document_intervals(directory):
    """Source-record provenance by a document's own slot interval.

    Do not infer source identity from txtid: manuscript sigla repeat across records.
    The range check refuses a line crossing document boundaries.
    """
    ranges = appcheck.node_ranges(directory)
    low, high = ranges["document"]
    sources = feat(directory, "src_file", low, high)
    docids = feat(directory, "docid", low, high)
    output = []
    for nodes, value in compact._parse(compact._split(directory / "oslots.tf")[1]):
        for node in nodes:
            if not low <= node <= high:
                continue
            slots = compact._nodes_of(value)
            if slots:
                output.append((min(slots), max(slots), sources.get(node), docids.get(node)))
    output.sort()
    return output


def source_for_line(sign_ids, documents, starts=None):
    if not sign_ids or not documents:
        return None
    if starts is None:
        starts = [row[0] for row in documents]
    start, end = min(sign_ids), max(sign_ids)
    i = bisect_right(starts, start) - 1
    if i < 0 or end > documents[i][1]:
        return None
    return {"src_file": documents[i][2], "docid": documents[i][3]}


def _emit(handle, data):
    handle.write(json.dumps(data, sort_keys=True, ensure_ascii=False) + "\n")


def inventory(directory, outdir, *, do_gaps=True, do_signrefs=True, refdir=None):
    ranges = appcheck.node_ranges(directory)
    low, high = ranges["line"]
    slo, shi = ranges["sign"]
    owner, slots = line_to_sign(directory, low, high)
    docs = document_intervals(directory)
    doc_starts = [row[0] for row in docs]  # do not rebuild for each of ~400k lines
    origins = {line: source_for_line(signs, docs, doc_starts)
               for line, signs in slots.items()}
    syms = feat(directory, "sym", slo, shi)
    glyphs = feat(directory, "cu_sign", slo, shi)
    anchor = feat(directory, "anchor", slo, shi)
    levels = feat(directory, "cu_aligned", low, high)
    lnr = feat(directory, "lnr", low, high)
    txtid = feat(directory, "txtid", low, high)
    outdir.mkdir(parents=True, exist_ok=True)
    out = {}

    if do_gaps:
        cu = feat(directory, "cu", low, high)
        multi = cuneiform.load_multi(PROGRAMS / "signmap-multi.tsv")
        primary, flags = Counter(), Counter()
        missing_sources = 0
        with gzip.open(outdir / "research-alignment-gaps-21.jsonl.gz", "wt", encoding="utf8") as f:
            for line in sorted(levels):
                if int(levels[line] or 0) != 0:
                    continue
                reading = [syms.get(s, "") for s in slots[line] if not anchor.get(s)]
                original = cu.get(line, "")
                case = classify_gap(original, reading, multi)
                primary[case["primary"]] += 1
                flags.update(case["flags"])
                provenance = origins.get(line) or {"src_file": None, "docid": None}
                if provenance["src_file"] is None:
                    missing_sources += 1
                _emit(f, dict(lineNode=line, txtid=txtid.get(line), lnr=lnr.get(line),
                              **provenance, cu=original, readings=reading, **case))
        if sum(primary.values()) != 45_849 and TF_VERSION == "0.4.0":
            raise ValueError("level-0 audit incomplete against pinned tf/0.4.0 baseline")
        out["gaps"] = dict(issue=21, total=sum(primary.values()),
                           unlocatedSourceRecords=missing_sources,
                           primary=dict(primary), overlappingFlags=dict(flags),
                           evidence="candidate explanations; no automated correction")

    if do_signrefs:
        specs = signref_inputs.load_lock(PROGRAMS / "signrefs.lock.json")
        result = signref_inputs.inspect_local(specs, refdir)
        if result.state != signref_inputs.PASSED:
            raise ValueError(f"locked reference set not available: {result.state}")
        refs = signrefs.load(refdir)
        canonical = equivalence_representatives(refs)
        known = {name for tables in refs.table.values() for name in tables}
        if known != {spec.name for spec in specs}:
            raise ValueError("verified references did not all parse")
        statuses, flags, top = Counter(), Counter(), Counter()
        missing_sources = 0
        lang = feat(directory, "lang", slo, shi)
        with gzip.open(outdir / "research-sign-disagreements-23.jsonl.gz", "wt", encoding="utf8") as f:
            for sign, glyph in sorted(glyphs.items()):
                if not glyph or anchor.get(sign):
                    continue
                reading = (syms.get(sign) or "").strip()
                if reading in ("", "x", "…"):
                    continue
                case = classify_disagreement(reading, glyph, refs, canonical)
                statuses[case["status"]] += 1
                if case["status"] != "all-disagree":
                    continue
                attributes = []
                if any(is_pua(c) for c in glyph):
                    attributes.append("pua")
                if reading.lstrip("+").isdigit():
                    attributes.append("numeral")
                if len(glyph) > 1:
                    attributes.append("multi-codepoint")
                if case["reference_conflict"]:
                    attributes.append("reference-conflict")
                if case["equivalenceAwareReferenceConflict"]:
                    attributes.append("equivalence-aware-conflict")
                if case["independentConsensus"]:
                    attributes.append("independent-consensus")
                attributes.append("single-tradition" if case["traditions"] == 1 else
                                  "multiple-traditions")
                flags.update(attributes)
                top[(reading, glyph)] += 1
                line = owner.get(sign)
                provenance = origins.get(line) or {"src_file": None, "docid": None}
                if provenance["src_file"] is None:
                    missing_sources += 1
                _emit(f, dict(signNode=sign, lineNode=line, txtid=txtid.get(line),
                              lnr=lnr.get(line), **provenance, lang=lang.get(sign),
                              cu_aligned=int(levels.get(line, 0) or 0),
                              reading=reading, cu_sign=glyph, flags=attributes, **case))
        if statuses["all-disagree"] != 31_055 and TF_VERSION == "0.4.0":
            raise ValueError("all-reference audit incomplete against pinned tf/0.4.0 baseline")
        out["disagreements"] = dict(issue=23, statuses=dict(statuses),
                                    unlocatedSourceRecords=missing_sources,
                                    allDisagree=statuses["all-disagree"],
                                    independentConsensusCount=flags["independent-consensus"],
                                    overlappingFlags=dict(flags),
                                    topPairs=[dict(reading=r, glyph=g, count=n)
                                              for (r, g), n in top.most_common(100)],
                                    evidence="outvoted is not equivalent to wrong")
    out["tfVersion"] = TF_VERSION
    (outdir / "research-cuneiform-quality-21-23.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf8")
    return out


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["all", "gaps", "disagreements"], default="all")
    p.add_argument("--tfdir", type=Path, default=ROOT / "tf" / TF_VERSION)
    p.add_argument("--refs", type=Path, default=ROOT / "refs")
    p.add_argument("--outdir", type=Path, default=REPORTS)
    args = p.parse_args(argv)
    if not (args.tfdir / "otype.tf").is_file():
        p.error("current TF artifact not present")
    output = inventory(args.tfdir, args.outdir, do_gaps=args.mode != "disagreements",
                       do_signrefs=args.mode != "gaps", refdir=args.refs)
    print(json.dumps(output, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
