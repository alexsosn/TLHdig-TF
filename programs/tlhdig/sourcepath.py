"""Pure parsing of TLHdig source-record paths.

A source path is provenance first: ``src_file`` is retained character-for-character as
the caller supplied it and is release-scoped identity, not a persistent cross-release
ID. The parser only extracts structure demonstrated by the release layouts. In
particular, it never promotes suffix-like tokens from intermediate directories to
project metadata.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


# Human labels for the project codes observed in the official Beta 0.3 archive.
# These labels are descriptive metadata only; unknown future codes remain parseable.
PROJECT_NAMES = {
    "TLH": "TLHdig base layer",
    "HFR": "Hethitische Festrituale",
    "BESRIT": "Beschwörungsrituale",
    "HDivT": "Hittite Divinatory Texts",
    "HAnn": "Hethitische Annalen",
    "KULTINV": "Kultinventare",
    "MYTH": "Mythologische Texte",
    "PTAC": "Hittite Palace-Temple Administrative Corpus",
    "GEBET": "Gebete",
    "ARINNA": "Arinna corpus",
    "luw": "Luwian material",
    "LUWGR": "Luwian material",
    "SVH": "Staatsverträge",
}

# Beta 0.2: CTH 241_XML
# Beta 0.3: CTH 241_XML_TLH
_TOP = re.compile(r"^CTH (?P<cth>[^_]+)_XML(?:_(?P<project>.+))?$")


@dataclass(frozen=True)
class SourcePath:
    """Parsed source-path metadata plus an explicit parse result."""

    src_file: str
    cth: str = ""
    project: str = ""
    project_name: str = ""
    source_subdir: str = ""
    source_stem: str = ""
    parse_ok: bool = False
    parse_error: str = ""


def _failed(
    raw: str,
    reason: str,
    *,
    source_subdir: str = "",
    source_stem: str = "",
) -> SourcePath:
    return SourcePath(
        src_file=raw,
        source_subdir=source_subdir,
        source_stem=source_stem,
        parse_ok=False,
        parse_error=reason,
    )


def parse(raw: str) -> SourcePath:
    """Parse one corpus-relative POSIX source path without rewriting it.

    Both published path grammars are accepted: Beta 0.2's ``CTH <n>_XML`` and Beta
    0.3's ``CTH <n>_XML_<project>``. Structural failures are returned as data instead
    of being collapsed to empty CTH/project values, so callers can decide whether a
    malformed upstream path is fatal for their use case.
    """
    if not isinstance(raw, str):
        raise TypeError("source path must be a string")

    if raw.startswith("/"):
        return _failed(raw, "absolute_path")
    if "\\" in raw:
        return _failed(raw, "non_posix_separator")

    parts = raw.split("/")
    if any(part in {".", ".."} for part in parts):
        filename = parts[-1] if parts else ""
        stem = filename[:-4] if filename.endswith(".xml") else ""
        return _failed(raw, "path_traversal", source_stem=stem)

    if not parts or parts[-1] == "":
        subdir = "/".join(parts[1:-1]) if len(parts) > 2 else ""
        return _failed(raw, "missing_filename", source_subdir=subdir)

    filename = parts[-1]
    stem = filename[:-4] if filename.endswith(".xml") else ""
    subdir = "/".join(parts[1:-1]) if len(parts) > 2 else ""

    if len(parts) < 2:
        return _failed(raw, "missing_top_directory", source_stem=stem)
    if any(part == "" for part in parts[1:-1]):
        return _failed(
            raw,
            "empty_path_component",
            source_subdir=subdir,
            source_stem=stem,
        )
    if not filename.endswith(".xml"):
        return _failed(raw, "not_xml", source_subdir=subdir)

    match = _TOP.fullmatch(parts[0])
    if match is None:
        return _failed(
            raw,
            "invalid_top_directory",
            source_subdir=subdir,
            source_stem=stem,
        )

    cth = match.group("cth")
    project = match.group("project") or ""
    return SourcePath(
        src_file=raw,
        cth=cth,
        project=project,
        project_name=PROJECT_NAMES.get(project, ""),
        source_subdir=subdir,
        source_stem=stem,
        parse_ok=True,
        parse_error="",
    )
