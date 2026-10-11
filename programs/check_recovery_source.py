#!/usr/bin/env python
"""Independent loaded-TF source recovery gate for the four signed #150 pilots.

Unlike global validators still reading historically repaired XML, this builds
transient TF graphs from reviewed source-event recovery and audits them from an
independent consumer. No generated corpus, patch manifest or tracked TF files
are written or re-stamped.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import convert, prepared_source, recovery_audit, repair
from tlhdig.paths import CORPUS, PATCHES


PILOTS = (
    "CTH 209_XML_TLH/KBo 12.55.xml",
    "CTH 448_XML_BESRIT/KBo 10.36.xml",
    "CTH 820_XML_TLH/KUB 48.15.xml",
    "CTH 832_XML_TLH/UBT 70.xml",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", choices=PILOTS, action="append",
        help="Audit only this reviewed AOxml source (may be repeated)",
    )
    args = parser.parse_args(argv)
    files = tuple(dict.fromkeys(args.source or PILOTS))
    patches = repair.read_manifest(PATCHES)

    with TemporaryDirectory(prefix="tlhdig-recovery-gate-") as temp:
        for i, rel in enumerate(files):
            prepared = prepared_source.prepare(rel)
            api = convert.build(
                CORPUS, Path(temp) / f"tf-{i}",
                files=[CORPUS / rel], patches=patches,
                terminal_recovery_paths=(rel,),
            )
            if api is None:
                raise recovery_audit.AuditError(
                    f"{rel}: recovered TF conversion failed"
                )
            report = recovery_audit.verify(prepared, api)
            print(
                f"PASS {rel}: {report.words} source words, "
                f"{report.lines} literal lines, {report.analyses} analyses"
            )
    print(f"recovery source->loaded-TF gate: {len(files)} reviewed documents passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
