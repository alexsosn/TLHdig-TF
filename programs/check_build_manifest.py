#!/usr/bin/env python
"""Verify that BUILD-MANIFEST.json still describes the current committed artifact."""
from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_current
from tlhdig import PROVENANCE_DIR, SOURCE_VERSION, TF_VERSION, build_manifest
from tlhdig.paths import ROOT


def main() -> int:
    main_dir = ROOT / "tf" / TF_VERSION
    provenance_dir = ROOT / PROVENANCE_DIR / TF_VERSION
    manifest = main_dir / build_manifest.MANIFEST
    problem = build_manifest.verify_manifest(
        manifest,
        source_version=SOURCE_VERSION,
        tf_version=TF_VERSION,
        main_dir=main_dir,
        provenance_dir=provenance_dir,
        input_files=validate_current.current_inputs(),
        code_files=validate_current.current_code_files(),
        gate_names=tuple(gate.name for gate in validate_current.GATES),
        root=ROOT,
    )
    if problem:
        print(f"current build manifest verification failed: {problem}")
        return 1

    payload = json.loads(manifest.read_text(encoding="utf8"))
    print(
        f"current build manifest OK: {len(payload['outputs']['files'])} files, "
        f"{payload['outputs']['digest']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
