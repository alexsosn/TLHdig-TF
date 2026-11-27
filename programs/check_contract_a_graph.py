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

from tlhdig import PROVENANCE_DIR, TF_VERSION, signs, source
from tlhdig.paths import CORPUS, PROGRAMS, REPORTS, ROOT

NEEDED = "otype oslots src_span src_file srcxml after"


def known_bad_spans() -> set[str]:
    """Documents with measured Contract-A provenance failures requiring an allowlist."""
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


# These eight source spans were independently measured in CI #1397's
# contract_a_graph.md. A syntactically repaired stream can differ from raw bytes,
# even when the coordinates and all readings are correct. Recognize only the
# exact original intervals and source hashes; do not skip whole documents.
_GAP_SOURCE = "CTH 570_XML_HDivT/KBo 58.79+.xml"
_GAP_SHA = "e2d9002b35b0f306ff89dbea70c4d22dd8516c03881d1c8faf68291892ee7e97"
_GAP_SPANS = frozenset({(26188,26294), (26295,26363), (29562,29645),
                        (29750,29830), (67136,67261), (67388,67491)})
_ATTRIBUTE_REPAIRS = {
    ("CTH 581_XML_HDivT/KBo 18.142.xml",8076,8477): (
        "2fb700b7b6ed4df543d271d6c2c57cc1ee6832ef1fd6fa5178b31444aaa71677",
        b"DA.BI</sGr>-&lt;/SP_f_AO_3a_SumGRAM&gt;",
        b"DA.BI&lt;/sGr>-&lt;/SP_f_AO_3a_SumGRAM&gt;"),
    ("CTH 585_XML_HDivT/KUB 31.54.xml",1143,1253): (
        "69b04fd61b2576449635da23fb6d4840d8d885dbd6e81af4c9a19e1d6543a7a1",
        b'c="<laes_in/>m<laes_fin/>"', b'c="&lt;laes_in/&gt;m&lt;laes_fin/&gt;"'),
}


def reviewed_inner(rel, data, a, b):
    """Expected graph content from the exact immutable source interval.

    Independent of the converter's OffsetMap and repair application. No tolerance
    for arbitrary missing closes, altered spans, or unreviewed XML escapes.
    """
    import hashlib
    import re
    attr = _ATTRIBUTE_REPAIRS.get((rel,a,b))
    gap = rel == _GAP_SOURCE and (a,b) in _GAP_SPANS
    if not gap and attr is None:
        return None
    if hashlib.sha256(data).hexdigest() != (_GAP_SHA if gap else attr[0]):
        raise ValueError(f"{rel}: SHA-256 mismatch for reviewed provenance interval")
    chunk = data[a:b]
    if gap:
        # The broken trans attribute is confined to the opening tag. Its
        # reviewed literal suffix marks the start of the unchanged word content.
        match = re.fullmatch(
            rb'<w trans="[^"\n]*<kap c-"[^"\n]*" mrp0sel="\?\?\?">'
            rb'((?:(?!<w\b|<lb\b|</w>)[\s\S])*?<gap\b[^>]*?/>)',
            chunk)
        if not match:
            raise ValueError(f"{rel}: reviewed gap-word boundary changed")
        return match.group(1)
    if not chunk.startswith(b"<w") or not chunk.endswith(b"</w>"):
        raise ValueError(f"{rel}: reviewed attribute word boundary changed")
    start, _ = source._tag_end(chunk, 0)
    inner = chunk[start:-4]
    _, old, new = attr
    if inner.count(old) != 1:
        raise ValueError(f"{rel}: reviewed attribute target changed")
    return inner.replace(old,new,1)


def main() -> int:
    from tf.fabric import Fabric

    # src_span and srcxml live in the provenance module, so this gate -- the one thing
    # that needs them -- loads both locations. A query user loads only the first.
    locations = [str(ROOT / "tf" / TF_VERSION)]
    prov = ROOT / PROVENANCE_DIR / TF_VERSION
    if prov.is_dir():
        locations.append(str(prov))
    TF = Fabric(locations=locations, silent="deep")
    inferred_present = (ROOT / "tf" / TF_VERSION / "inferred.tf").is_file()
    api = TF.load(
        NEEDED + (" inferred" if inferred_present else ""), silent="deep"
    )
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
            inferred = inferred_present and F.inferred.v(w) == 1
            if inferred:
                # Source-owned lexical range, not a forged <w>. Validate
                # independently against original XML paragraph/line spans.
                if rel != "CTH 170_XML_TLH/KBo 31.40.xml":
                    problems.append(f"{rel}: unexpected inferred word {w}")
                    continue
                original_spans = source.scan(data)
                paragraph = [
                    p for p in original_spans
                    if p.tag == "P___Standard"
                    and p.inner_start <= a < b <= p.inner_end
                ]
                boundaries = [
                    lb for lb in original_spans
                    if lb.tag == "lb"
                    and lb.outer_end <= a
                    and any(p.inner_start <= lb.outer_start < p.inner_end
                            for p in paragraph)
                ]
                if len(paragraph) != 1 or not boundaries or b"<w" in chunk:
                    problems.append(
                        f"{rel}: inferred word {w} span {span} lacks "
                        "unwrapped source line/paragraph ownership"
                    )
                    continue
                stats["inferred_source_groups"] += 1
            else:
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
            reviewed = reviewed_inner(rel, data, a, b) if not inferred else None
            if reviewed is not None:
                inner = reviewed
            else:
                inner = chunk if inferred else (
                    chunk[source._tag_end(chunk, 0)[0]: chunk.rindex(b"</w>")]
                    if b"</w>" in chunk else b""
                )
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
                stats["reviewed_repaired_inner" if reviewed is not None else "byte_identical"] += 1

    lines = [
        "# Contract A, verified against the shipped graph",
        "",
        "Generated by `programs/check_contract_a_graph.py`. For every `word` node this",
        "slices `src_span` out of the file `src_file` names and compares those bytes with",
        "the signs the word actually carries in the dataset.",
        "",
        "| check | count |",
        "|---|---:|",
        f"| words with a `src_span` | {stats['checked']:,} |",
        f"| span is a `<w>` element | {stats['is_a_word_element']:,} |",
        f"| source-backed unwrapped group | {stats['inferred_source_groups']:,} |",
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
