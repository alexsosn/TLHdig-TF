#!/usr/bin/env python
"""Independent signed-source audit of the *current*, provenance-split TF build.

This is a release validator, not a converter: it consumes only existing,
serialized TF features, selecting each of the four SHA-reviewed AOxml recovery
pilots inside the combined corpus. Neither the converter's internal emitter
ledger nor historically fully repaired source XML is the reference. The
literal source bytes + reviewed mechanical-only lexicals are the witness.

The full corpus has millions of nodes: load only features that the external
source-word/line/sign/morphology auditor needs, not Fabric.loadAll().
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import PROVENANCE_DIR, TF_VERSION, convert, prepared_source, recovery_audit
from tlhdig.paths import ROOT

# Features actively read by recovery_audit and morph_output (in addition to
# the automatically loaded warp features otype/oslots). The provenance features
# are mandatory and must reside in their *separate* published module.
_REQUIRED_MAIN = frozenset({
    "src_file", "source_word_open", "source_line_open", "srcln",
    "after", "trans", "nanalyses", "index", "mrpsel", "mrpsel_kind",
    "nselected", "analyses", "selected",
})
_REQUIRED_PROVENANCE = frozenset({"srcxml", "src_span"})
_OPTIONAL_MORPHOLOGY = frozenset({
    "sel_base", "sel_clitic", "sel_group", "sep", "parse_ok",
    "lemma", "gloss", "morph", "stemclass_raw", "field4_kind",
    "det_hint", "mrp_control", "raw", "pos", "stemclass",
    "clitic_lemma", "clitic_morph", "clitic_stemclass", "clitic_det",
})


def verify_artifact(main_dir: Path, provenance_dir: Path) -> tuple[recovery_audit.AuditReport, ...]:
    """Verify *all four* source-reviewed documents in an existing split TF corpus.

    A missing feature, missing source document, duplicate source document, or
    source/sign/word/line/analysis mismatch fails the entire release check.
    Do not silently fall back to the main-only module or an in-memory build.
    """
    main_dir = Path(main_dir)
    provenance_dir = Path(provenance_dir)
    for name in ("otype", "oslots"):
        if not (main_dir / f"{name}.tf").is_file():
            raise ValueError(f"current TF module missing mandatory {name}.tf: {main_dir}")
    for name in sorted(_REQUIRED_MAIN):
        if not (main_dir / f"{name}.tf").is_file():
            raise ValueError(f"current TF module missing required {name}.tf: {main_dir}")
    for name in sorted(_REQUIRED_PROVENANCE):
        if not (provenance_dir / f"{name}.tf").is_file():
            raise ValueError(
                f"current provenance module missing required {name}.tf: {provenance_dir}"
            )
        if (main_dir / f"{name}.tf").exists():
            raise ValueError(
                f"current provenance feature {name}.tf is not split from the main TF module"
            )

    # Keep the multi-million-sign corpus memory footprint bounded by the
    # actual features inspected by the loaded-graph auditor.
    present_optional = {
        name for name in _OPTIONAL_MORPHOLOGY
        if (main_dir / f"{name}.tf").is_file()
    }
    selected = sorted(_REQUIRED_MAIN | _REQUIRED_PROVENANCE | present_optional)

    from tf.fabric import Fabric

    tf = Fabric(locations=[str(main_dir), str(provenance_dir)], silent="deep")
    api = tf.load(" ".join(selected), silent="deep")
    if api is None or api is False:
        raise ValueError("current TF and provenance modules could not be loaded together")

    reports = []
    for rel in sorted(convert.VERIFIED_RECOVERY_PILOTS):
        # This preparation authenticates the *actual* unchanged original
        # AOxml, signed repair-policy partition and one reviewed word event.
        prepared = prepared_source.prepare(rel)
        report = recovery_audit.verify_in_corpus(prepared, api)
        reports.append(report)
    return tuple(reports)


def main() -> int:
    reports = verify_artifact(
        ROOT / "tf" / TF_VERSION,
        ROOT / PROVENANCE_DIR / TF_VERSION,
    )
    for report in reports:
        print(
            f"PASS {report.source}: {report.words} original words, "
            f"{report.lines} literal lines, {report.analyses} analyses"
        )
    print(
        "current split TF signed-source recovery gate: "
        f"{len(reports)} documents passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
