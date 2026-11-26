"""One-off Beta 0.4 migration audit; never writes active manifests."""
from collections import Counter
from pathlib import Path
import json
import re
from xml.parsers import expat

from lxml import etree
from tlhdig import corpusid, repair, source

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "programs"
R = ROOT / "reports"
CORPUS = ROOT / "corpus" / "TLHdig-0.4"
QNAME = b"AO:-LineNrExpl"
VALID_QNAME = b"AO:LineNrExpl"
QNAME_TAG = re.compile(rb"</?AO:-LineNrExpl(?=[\s/>])")
VALID_EXAMPLE = "CTH 562_XML_HDivT/KBo 48.25.xml"
MAT = "CTH 585_XML_HDivT/KUB 31.54.xml"


def parse_error(data):
    try:
        expat.ParserCreate(namespace_separator="}").Parse(data, True)
        etree.fromstring(data, etree.XMLParser(resolve_entities=False, no_network=True))
    except (expat.ExpatError, etree.XMLSyntaxError) as exc:
        return str(exc)
    return None


def qname_patches(data):
    """Unique local byte targets; change only the illegal QName, not its content."""
    result = []
    current = data
    while (m := QNAME_TAG.search(current)) is not None:
        start, end = m.span()
        for extra in (0, 16, 32, 64, 128, 256, 512, 1024):
            old = current[start:end + extra]
            if current.count(old) == 1:
                new = old[:end-start].replace(QNAME, VALID_QNAME) + old[end-start:]
                result.append(repair.Patch(old, new, "candidate: namespace local name begins with hyphen; compare AO:LineNrExpl"))
                current = current.replace(old, new, 1)
                break
        else:
            raise ValueError("ambiguous QName patch")
    # Direct replacement is the independent whole-file expectation.
    expected = QNAME_TAG.sub(lambda m: m.group().replace(QNAME, VALID_QNAME), data)
    assert current == expected
    return result


def main():
    pin = corpusid.read_manifest(P / "corpus-beta04.sha256")
    assert not corpusid.verify(CORPUS, pin)
    valid = etree.fromstring((CORPUS / VALID_EXAMPLE).read_bytes())
    assert valid.xpath("//*[local-name()='LineNrExpl' and namespace-uri()='http://hethiter.net/ns/AO/1.0']")
    prior = repair.read_manifest(P / "patches.yaml")
    candidates = {}
    rows = {}
    counts = Counter()
    for rel, sha in sorted(pin.items()):
        if not rel.endswith(".xml"):
            continue
        data = (CORPUS / rel).read_bytes()
        err = parse_error(data)
        if err is None:
            counts["strict_valid"] += 1
            continue
        row = {"sha256": sha, "raw_parse_error": err}
        rows[rel] = row
        patches = []
        if data.startswith(b"HBEGIN:"):
            disposition = "encrypted"
        elif rel in prior and prior[rel][0] == sha:
            patches = prior[rel][1]
            disposition = "unchanged_old_repair"
        elif QNAME_TAG.search(data):
            patches = qname_patches(data)
            disposition = "candidate_qname_repair"
        elif rel == MAT:
            old = b'c="<laes_in/>m<laes_fin/>"'
            new = b'c="&lt;laes_in/&gt;m&lt;laes_fin/&gt;"'
            patches = [repair.Patch(old, new, "escape literal marker markup inside attribute; decoded value unchanged")]
            disposition = "candidate_attribute_escape"
        else:
            disposition = "needs_review"
        if patches:
            fixed = repair.apply(data, patches, expect_sha=sha)
            err2 = parse_error(fixed)
            row["candidate_parse_error"] = err2
            if err2 is None:
                spans = source.scan(fixed)
                assert not source.verify_reconstruction(fixed, spans)
                row["patches"] = len(patches)
                if rel == MAT:
                    root = etree.fromstring(fixed)
                    assert any(x.get("c") == "<laes_in/>m<laes_fin/>" for x in root.iter("materlect"))
                candidates[rel] = (sha, patches)
            else:
                disposition = "needs_review"
        row["disposition"] = disposition
        counts[disposition] += 1
        if disposition == "needs_review":
            # Proposals are evidence for manual review only, never accepted by parse success alone.
            props = repair.propose_iteratively(data)
            row["detector_proposals"] = [
                {"old": p.old.decode("utf-8", "replace"),
                 "new": p.new.decode("utf-8", "replace"), "reason": p.reason}
                for p in props
            ]
            try:
                row["detector_parse_error"] = parse_error(repair.apply(data, props, expect_sha=sha))
            except repair.PatchError as exc:
                row["detector_parse_error"] = str(exc)
    assert len(rows) == 23
    assert counts["strict_valid"] == 24108
    assert len(candidates) == 13
    repair.write_manifest(P / "patches-beta04-candidate.yaml", candidates)
    (P / "excluded-beta04-candidate.txt").write_text(
        "# Preliminary exclusions, not active policy; unresolved repairs need review.\n" +
        "".join(f"{rel}\t{'encrypted' if row['disposition']=='encrypted' else 'unparseable'}\n"
                for rel, row in rows.items() if rel not in candidates), encoding="utf8")
    (R / "beta04-repair-audit.json").write_text(
        json.dumps({"counts": dict(counts), "files": rows}, ensure_ascii=False, indent=2)+"\n",
        encoding="utf8")
    print(dict(counts))


if __name__ == "__main__":
    main()
