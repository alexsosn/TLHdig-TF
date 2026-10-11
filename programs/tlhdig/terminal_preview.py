"""Opt-in one-word Text-Fabric witness for the first #150 recovery TDD slice.

NOT a production converter. Builds a tiny *actual TF graph* from the immutable
source-grounded terminal word and its immediately preceding literal line.
There is no serialized corrected XML, guessed </w>, or mutation of the corpus.
"""
from __future__ import annotations

from pathlib import Path

from lxml import etree as LE

from . import convert, prepared_source, recovery


def build_terminal_preview(
    prepared: prepared_source.PreparedSource,
    out_dir: Path,
    *,
    silent: str = "deep",
):
    """Create a TF sample; fail closed on any non-singleton recovered structure."""
    from tf.convert.walker import CV
    from tf.fabric import Fabric

    payload = recovery.terminal_word_payload(prepared)
    view = recovery.recover_word_state(prepared)
    line_candidates = [
        t for t in view.tokens
        if t.tag == "lb" and t.kind == "empty"
        and t.start_offset is not None
        and t.start_offset < payload.opening_offset
    ]
    if not line_candidates:
        raise recovery.SignatureDrift(
            f"{prepared.path}: terminal word has no source-anchored line start"
        )
    line_token = line_candidates[-1]
    if not prepared.original_bytes[line_token.start_offset:].startswith(b"<lb"):
        raise recovery.SignatureDrift(
            f"{prepared.path}: terminal line opening is not original"
        )

    line_bytes = prepared.mechanical_bytes[
        line_token.mechanical_start:line_token.mechanical_end
    ]
    try:
        # The real lb is self-closing; parse its proven lexical opening only.
        parser = LE.XMLParser(recover=False, resolve_entities=False, no_network=True)
        line_el = LE.fromstring(line_bytes, parser)
    except LE.XMLSyntaxError as exc:
        raise recovery.SignatureDrift(
            f"{prepared.path}: cannot parse terminal source line opener"
        ) from exc
    if line_el.tag != "lb":
        raise recovery.SignatureDrift(
            f"{prepared.path}: terminal line is not a literal lb"
        )

    def director(cv):
        document = cv.node("document")
        cv.feature(
            document,
            docid=Path(prepared.path).stem,
            src_file=prepared.path,
        )
        state = convert._State(
            cv, keep_empty=False, omap=None, lexemes=None,
            text_lang=line_el.get("lg"),
        )
        state.start_line(line_el)
        cv.feature(state.line, recovery_line_open=line_token.start_offset)
        state.word(
            None, None, None,
            recovered=payload, recovered_source=prepared.original_bytes,
            recovered_prepared=prepared,
        )
        state.finish()
        # Use precisely the same orphan/paired marker semantics as production;
        # the one-word source census remains independently asserted by tests.
        convert._emit_damage_clusters(cv, state)
        cv.terminate(document)

        for feat in cv.features():
            cv.meta(
                feat,
                description=convert.DESCRIPTIONS.get(feat, "(undocumented)"),
                valueType="int" if feat in convert.INT_FEATURES else "str",
            )

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tf = Fabric(locations=str(out_dir), silent=silent)
    cv = CV(tf, silent=silent)
    good = cv.walk(
        director,
        convert.SLOT_TYPE,
        otext=convert.OTEXT,
        generic=convert.GENERIC,
        intFeatures=set(),
        featureMeta={},
        warn=False,
    )
    if not good:
        raise RuntimeError(f"{prepared.path}: recovered terminal preview TF build failed")

    reader = Fabric(locations=str(out_dir), silent=silent)
    api = reader.loadAll(silent=silent)
    if api is True or api is False:
        api = getattr(reader, "api", None) if api else None
    if api is None:
        raise RuntimeError(f"{prepared.path}: recovered terminal preview TF load failed")
    return api
