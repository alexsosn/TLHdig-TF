"""Consumer-side original AOxml -> *loaded* Text-Fabric recovery audit (#150).

This gate does not trust the converter's emitted-opening ledger or the historical
full-repair lxml tree as expected output. Its witnesses are SHA-reviewed
immutable original bytes and mechanical-only lexical openers. The graph is read
back through the TF API after serialization.

Only the four explicitly reviewed, non-nested recovery pilot sources are in
scope. This is not a general corpus-wide source parser or independent grammar.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import morph_output, recovery


class AuditError(ValueError):
    """Source-backed word, line, or morphology is missing or altered in TF."""


@dataclass(frozen=True)
class AuditReport:
    source: str
    words: int
    lines: int
    analyses: int


def _exact_openings(api, label: str, nodes, feature: str, expected: tuple[int, ...]):
    """Compare a literal immutable-source opening inventory with loaded nodes."""
    values = tuple(getattr(api.F, feature).v(node) for node in nodes)
    if any(value is None for value in values):
        raise AuditError(f"{label}: TF node lacks original source opening")
    if len(values) != len(expected):
        raise AuditError(
            f"{label}: TF contains {len(values)} nodes, "
            f"source has {len(expected)} literal openings"
        )
    if len(set(values)) != len(values):
        raise AuditError(f"{label}: duplicate original source opening in TF")
    if set(values) != set(expected):
        raise AuditError(f"{label}: TF/source opening identity mismatch")
    return dict(zip(values, nodes))


def verify(prepared, api) -> AuditReport:
    """Fail closed on an incorrect *single-source* serialized TF recovery graph.

    The caller supplies a SHA/manifest-reviewed PreparedSource and the loaded TF
    API returned by a conversion of only that source with terminal recovery
    enabled. A multi-document graph is rejected to prevent unrelated nodes
    satisfying missing original-source identities.
    """
    source_words, source_lines = recovery.original_opening_sequences(prepared)
    witnesses = recovery.lexical_word_witnesses(prepared)
    if tuple(w.opening_offset for w in witnesses) != source_words:
        raise AuditError("original source word witnesses/openings disagree")

    if len(api.F.otype.s("document")) != 1:
        raise AuditError("expected exactly one source document in the loaded TF graph")

    nodes = (
        *api.F.otype.s("word"),
        *api.F.otype.s("layout"),
    )
    words_by_open = _exact_openings(
        api, "word", nodes, "source_word_open", source_words,
    )
    _exact_openings(
        api, "line", tuple(api.F.otype.s("line")),
        "source_line_open", source_lines,
    )

    analyses = 0
    for witness in witnesses:
        word = words_by_open[witness.opening_offset]
        kind = api.F.otype.v(word)
        if kind == "word":
            # This must be THIS lexical source opening's sign payload, not a
            # correct-looking sign body borrowed from another source word.
            signs = tuple(api.L.d(word, otype="sign"))
            if not signs:
                raise AuditError(
                    f"word: original opening {witness.opening_offset} has no sign slots"
                )
            body = b"".join(
                ((api.F.srcxml.v(s) or "") + (api.F.after.v(s) or "")).encode("utf8")
                for s in signs
            )
            if body != witness.body_bytes:
                raise AuditError(
                    f"word: original source body/sign mismatch at "
                    f"{witness.opening_offset}"
                )
            if (api.F.trans.v(word) or "") != witness.attributes.get("trans", ""):
                raise AuditError(
                    f"word: source transcription mismatch at {witness.opening_offset}"
                )
            raw_span = api.F.src_span.v(word)
            if witness.end_is_implicit:
                if raw_span is not None:
                    raise AuditError(
                        f"word: synthetic closing span claimed at {witness.opening_offset}"
                    )
            else:
                if not raw_span:
                    raise AuditError(
                        f"word: literal source span missing at {witness.opening_offset}"
                    )
                try:
                    start, stop = (int(x) for x in raw_span.split("-"))
                except (ValueError, AttributeError) as exc:
                    raise AuditError("word: malformed original source span") from exc
                if (
                    start != witness.opening_offset
                    or stop > len(prepared.original_bytes)
                    or not prepared.original_bytes[start:stop].endswith(b"</w>")
                ):
                    raise AuditError(
                        f"word: invalid source closing span at {witness.opening_offset}"
                    )
            analyses += len(api.E.analyses.f(word))
        elif kind != "layout":
            raise AuditError(
                f"source word opening {witness.opening_offset} became {kind!r}"
            )
        # Layout source morphology is known to be lossy (#105); fail rather
        # than counting it as successfully represented. The morphology checker
        # handles this special case and also audits candidate slots/edge values.
        try:
            morph_output.assert_word_output(api, word, witness.attributes)
        except morph_output.MorphOutputMismatch as exc:
            raise AuditError(
                f"word: morphology differs from source at "
                f"{witness.opening_offset}: {exc}"
            ) from exc

    return AuditReport(
        source=prepared.path, words=len(source_words),
        lines=len(source_lines), analyses=analyses,
    )
