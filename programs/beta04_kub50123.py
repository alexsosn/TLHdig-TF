"""One reviewed candidate. Keep every literal reading, marker and opening tag."""
from tlhdig import repair
from audit_beta04_repairs import qname_patches

REL = "CTH 570_XML_HDivT/KUB 50.123.xml"
SHA = "416695b2a7368d7a22b680533e9eb053858ce47068b3a3a8f1d2aa91b5590273"
REASON = "correct swapped closing tag in KUB 50.123 Rs. 5 prime"


def propose(raw):
    if repair.sha256(raw) != SHA:
        raise ValueError("SHA-256 mismatch: reviewed KUB 50.123 source changed")
    old1 = b'<AO:-LineNrExpl><del_in/></w> <w><space c="14"/>'
    new1 = old1.replace(b'</w>', b'</AO:-LineNrExpl>', 1)
    old2 = b'<w mrp0sel="DEL"><del_fin/></AO:-LineNrExpl> <w trans="10"'
    new2 = old2.replace(b'</AO:-LineNrExpl>', b'</w>', 1)
    patches = [repair.Patch(old1, new1, REASON), repair.Patch(old2, new2, REASON)]
    current = repair.apply(raw, patches, expect_sha=SHA)
    patches.extend(qname_patches(current))
    fixed = repair.apply(raw, patches, expect_sha=SHA)
    if not repair.parses(fixed):
        raise ValueError("KUB 50.123 remains invalid after reviewed repairs")
    return patches
