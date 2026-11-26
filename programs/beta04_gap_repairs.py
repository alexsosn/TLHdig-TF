"""Five reviewed Beta 0.4 source cases; proposal only, not a global XML repair.

The malformed trans attribute contains a literal broken markup string. Preserve
that value by XML escaping, and insert a close immediately after its gap rather
than at EOF. Never modify the immutable source or activate a new manifest here.
"""
import re
from pathlib import Path
from tlhdig import repair

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "programs"
CORPUS = ROOT / "corpus" / "TLHdig-0.4"
CASES = {
    "CTH 570_XML_HDivT/KBo 58.79+.xml": ("e2d9002b35b0f306ff89dbea70c4d22dd8516c03881d1c8faf68291892ee7e97", 6),
    "CTH 580_XML_HDivT/KUB 22.17.xml": ("43bef789dc91b0b4ff1a2b9d5765b13bbabe347b8891c2896137b494ed041669", 1),
    "CTH 580_XML_HDivT/KUB 50.29.xml": ("e997d3d9ee3a0cfe7563280e4738b67a10b769bf5f0de0657fc78ac95f5ce5c4", 2),
    "CTH 580_XML_HDivT/KUB 50.117.xml": ("eaf99bc3a1a82f0f651f26900733ba5ac9f1339c97a04ade0a9ba60296192025", 2),
    "CTH 585_XML_HDivT/585_u+.xml": ("9fa6fdeedfdb2800d90d414c6fbbcc647f9d44dd113306f38cee857a573ace42", 1),
}
PATTERN = re.compile(
    rb'<w trans="(?:[^"\n]*<kap c-"[^"\n]*|<parse)" mrp0sel="\?\?\?">'
    rb'(?:(?!<w\b|<lb\b|</w>).)*?<gap\b[^>]*?/>', re.S)


def unique_target(data, start, lengths):
    for length in lengths:
        part = data[start:start+length]
        if part and data.count(part) == 1:
            try:
                part.decode("utf8")
            except UnicodeDecodeError:
                continue
            return part
    raise ValueError("ambiguous repair target")


def propose(rel, raw):
    digest, count = CASES[rel]
    if repair.sha256(raw) != digest:
        raise ValueError("SHA-256 mismatch: reviewed source changed")
    if len(list(PATTERN.finditer(raw))) != count:
        raise ValueError("unexpected malformed gap-word count")
    fixed, patches = raw, []
    for _ in range(count):
        match = PATTERN.search(fixed)
        if match is None:
            raise ValueError("missing reviewed source case")
        old = match.group()
        start = old.index(b'trans="') + 7
        end = old.index(b'" mrp0sel')
        value = old[start:end]
        escaped = value.replace(b'&', b'&amp;').replace(b'<', b'&lt;').replace(b'"', b'&quot;')
        anchor = unique_target(fixed, match.end(), range(1, 500))
        closure = repair.Patch(anchor, b"</w>" + anchor,
            "close malformed gap word before following source sibling")
        fixed = repair.apply(fixed, [closure])
        patches.append(closure)
        target = unique_target(fixed, match.start(), range(end+1, len(old)+end+6))
        if len(target) > len(old)+5:
            raise ValueError("lexical repair extends beyond reviewed gap-word boundary")
        lexical = repair.Patch(target, target[:start] + escaped + target[end:],
            "escape corrupt literal trans attribute without changing decoded value")
        fixed = repair.apply(fixed, [lexical])
        patches.append(lexical)
    if PATTERN.search(fixed) or not repair.parses(fixed):
        raise ValueError("repair did not restore strict XML")
    return patches


def main():
    entries = {}
    for rel, (sha, _) in CASES.items():
        raw = (CORPUS / rel).read_bytes()
        entries[rel] = (sha, propose(rel, raw))
    repair.write_manifest(P / "patches-beta04-gap-candidate.yaml", entries)
    print("Five source-bound candidate documents; 24 patches, 12 word closures.")


if __name__ == "__main__":
    main()
