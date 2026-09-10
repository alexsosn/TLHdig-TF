#!/usr/bin/env python
"""Contract A, checked against the graph that shipped.

`check_contract_a.py` validates `source.py` against the source corpus -- it never loads
the dataset, so it cannot tell whether the converter attached the right span to the right
node, whether `OffsetMap` translated repaired coordinates correctly, or whether
compaction preserved the assignment. It is the last gate here that cannot fail for the
reason it was written.

This one starts from the shipped graph: for every `word` node it reads `src_span`, slices
those bytes out of the file `src_file` names, and requires the slice to be the `<w>`
element whose signs that word actually carries.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import PROVENANCE_DIR, TF_VERSION, signs
from tlhdig.paths import CORPUS, PROGRAMS, REPORTS, ROOT

NEEDED = "otype oslots src_span src_file srcxml after"


def verify_document_header(data: bytes, span, srcxml) -> list[str]:
    """Verify one document's optional provenance against its original source bytes."""
    problems: list[str] = []
    if not span:
        return ["document has no src_span"]
    if srcxml is None:
        return ["document has no srcxml"]
    try:
        a, b = (int(x) for x in str(span).split("-", 1))
    except (TypeError, ValueError):
        return [f"document has unparseable src_span {span!r}"]
    if not (0 <= a < b <= len(data)):
        return [f"document span {span} lies outside the file ({len(data)} bytes)"]
    chunk = data[a:b]
    if not chunk.startswith(b"<AOHeader") or not chunk.rstrip().endswith(b"</AOHeader>"):
        problems.append(f"document span {span} is not an AOHeader outer element")
    expected = chunk.decode("utf8", "surrogateescape")
    if srcxml != expected:
        problems.append("document srcxml does not equal its exact source span")
    return problems


def known_bad_spans() -> set[str]:
    """Repaired documents whose spans are already known not to describe their bytes."""
    f = PROGRAMS / "contract_a_known.txt"
    if not f.exists():
        return set()
    return {
        ln.partition("\t")[0]
        for ln in f.read_text(encoding="utf8").splitlines()
        if ln.strip() and not ln.startswith("#")
    }


def known_lossy() -> set[str]:
    f = PROGRAMS / "known_lossy.txt"
    if not f.exists():
        return set()
    return {
        ln.partition("\t")[0]
        for ln in f.read_text(encoding="utf8").splitlines()
        if ln.strip() and not ln.startswith("#")
    }


def main() -> int:
    from tf.fabric import Fabric

    # src_span and srcxml live in the provenance module, so this gate -- the one thing
    # that needs them -- loads both locations. A query user loads only the first.
    locations = [str(ROOT / "tf" / TF_VERSION)]
    prov = ROOT / PROVENANCE_DIR / TF_VERSION
    if prov.is_dir():
        locations.append(str(prov))
    TF = Fabric(locations=locations, silent="deep")
    api = TF.load(NEEDED, silent="deep")
    if api is False or api is None:
        print("contract A: dataset does not load")
        return 1
    F, L = api.F, api.L

    lossy = known_lossy()
    bad_spans = known_bad_spans()
    stats = Counter()
    problems: list[str] = []
    cache: dict[str, bytes] = {}

    for doc in F.otype.s("document"):
        rel = F.src_file.v(doc)
        if not rel:
            stats["document_without_src_file"] += 1
            continue
        data = cache.get(rel)
        if data is None:
            path = CORPUS / rel
            if not path.is_file():
                problems.append(f"{rel}: src_file names a file that does not exist")
                continue
            data = path.read_bytes()
            cache = {rel: data}          # one document at a time; do not hold the corpus

        stats["documents_checked"] += 1
        header_problems = verify_document_header(
            data, F.src_span.v(doc), F.srcxml.v(doc)
        )
        if header_problems:
            stats["document_header_mismatch"] += 1
            problems.extend(f"{rel}: {problem}" for problem in header_problems)
        else:
            stats["document_header_exact"] += 1

        # Word-level historical exceptions never exempt the document header: every
        # emitted document must preserve its AOHeader exactly.
        if rel in bad_spans:
            stats["skipped_known_bad_span"] += len(L.d(doc, otype="word"))
            continue
        for w in L.d(doc, otype="word"):
            span = F.src_span.v(w)
            if not span:
                stats["word_without_span"] += 1
                continue
            stats["checked"] += 1
            try:
                a, b = (int(x) for x in span.split("-", 1))
            except ValueError:
                problems.append(f"{rel}: word {w} has an unparseable src_span {span!r}")
                continue
            if not (0 <= a < b <= len(data)):
                problems.append(
                    f"{rel}: word {w} span {span} lies outside the file ({len(data)} bytes)"
                )
                continue
            chunk = data[a:b]
            if not chunk.startswith(b"<w") or not chunk.rstrip().endswith(b">"):
                problems.append(
                    f"{rel}: word {w} span {span} is not a <w> element: "
                    f"{chunk[:40]!r}"
                )
                continue
            stats["is_a_word_element"] += 1

            if rel in lossy:
                stats["skipped_known_lossy"] += 1
                continue
            # The bytes the graph kept for this word, straight from its slots.
            slots = L.d(w, otype="sign")
            graph = "".join((F.srcxml.v(s) or "") + (F.after.v(s) or "") for s in slots)
            inner = chunk[chunk.index(b">") + 1: chunk.rindex(b"</w>")] \
                if b"</w>" in chunk else b""
            kept = "".join(
                s.srcxml + s.after
                for s in signs.tokenise_word(inner)
                if s.type != "empty"
            )
            if graph != kept:
                stats["mismatch"] += 1
                if len(problems) < 400:
                    problems.append(
                        f"{rel}: word {w} span {span}\n"
                        f"       source slice -> {kept[:90]!r}\n"
                        f"       graph slots  -> {graph[:90]!r}"
                    )
            else:
                stats["byte_identical"] += 1

    lines = [
        "# Contract A, verified against the shipped graph",
        "",
        "Generated by `programs/check_contract_a_graph.py`. Every document first verifies",
        "that its optional-provenance `src_span`/`srcxml` is the exact original AOHeader;",
        "word nodes then slice their source spans and compare those bytes with the graph.",
        "",
        "| check | count |",
        "|---|---:|",
        f"| documents checked for exact `AOHeader` provenance | {stats['documents_checked']:,} |",
        f"| exact document headers | {stats['document_header_exact']:,} |",
        f"| document header mismatches | {stats['document_header_mismatch']:,} |",
        f"| words with a `src_span` | {stats['checked']:,} |",
        f"| span is a `<w>` element | {stats['is_a_word_element']:,} |",
        f"| slice reproduces the graph's signs | {stats['byte_identical']:,} |",
        f"| skipped (known_lossy.txt) | {stats['skipped_known_lossy']:,} |",
        f"| skipped (contract_a_known.txt) | {stats['skipped_known_bad_span']:,} |",
        f"| mismatches | {stats['mismatch']:,} |",
        "",
    ]
    if problems:
        lines.append(f"## {len(problems)} problem(s)")
        lines.append("")
        lines.extend("    " + line for p in problems for line in p.split("\n"))
        lines.append("")
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "contract_a_graph.md").write_text("\n".join(lines) + "\n", encoding="utf8")
    print("\n".join(lines[:20]))
    if problems:
        print(f"CONTRACT A FAILED: {len(problems)} problem(s) -> reports/contract_a_graph.md")
        return 1
    print("every word's src_span slices the bytes the graph holds for it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
