#!/usr/bin/env python
"""Research-only audit of canonical release-certification dependencies (#69).

This script does not change release semantics.  It inventories the current release-v5
entrypoints, local Python import closure, declared release inputs, app/dependency inputs,
and canonical workflow path filters, then reports which tracked dependency classes are
not represented by the workflow trigger.
"""
from __future__ import annotations

import ast
import fnmatch
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PROGRAMS = ROOT / "programs"
WORKFLOW = ROOT / ".github" / "workflows" / "certify-dataset.yml"
RELEASE_CHECK = PROGRAMS / "release_check.py"

GATE_RE = re.compile(
    r'certification\.Gate\("(?P<name>[^"]+)",\s*\((?P<command>[^)]*)\)\)'
)
QUOTED_RE = re.compile(r'"([^"]+)"')

# These values affect certification semantics but are not all direct gate commands.
EXPLICIT_INPUTS = (
    "programs/corpus.sha256",
    "programs/patches.yaml",
    "programs/signrefs.lock.json",
    "programs/release-delta.json",
    "programs/known_lossy.txt",
    "programs/contract_a_known.txt",
    "requirements.txt",
    "app/config.yaml",
    ".github/workflows/certify-dataset.yml",
)
MUTABLE_OUTPUT_ROOTS = ("tf/", "tf-provenance/", "reports/")


def workflow_paths() -> tuple[str, ...]:
    """Extract the current push.paths list without depending on YAML 1.1 `on` parsing."""
    lines = WORKFLOW.read_text(encoding="utf8").splitlines()
    in_paths = False
    indent = None
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not in_paths and stripped == "paths:":
            in_paths = True
            indent = len(line) - len(line.lstrip())
            continue
        if not in_paths:
            continue
        current_indent = len(line) - len(line.lstrip())
        if stripped and current_indent <= int(indent):
            break
        if stripped.startswith("- "):
            value = stripped[2:].strip().strip('"').strip("'")
            out.append(value)
    return tuple(out)


def gate_entrypoints() -> dict[str, str | None]:
    text = RELEASE_CHECK.read_text(encoding="utf8")
    result: dict[str, str | None] = {}
    for match in GATE_RE.finditer(text):
        parts = QUOTED_RE.findall(match.group("command"))
        entry = next((part for part in parts if part.startswith("programs/") and part.endswith(".py")), None)
        result[match.group("name")] = entry
    return result


def module_path(module: str, package_dir: Path) -> Path | None:
    candidate = package_dir / (module.replace(".", "/") + ".py")
    if candidate.is_file():
        return candidate
    package = package_dir / module.replace(".", "/") / "__init__.py"
    return package if package.is_file() else None


def local_imports(path: Path) -> set[Path]:
    """Return direct local Python imports under programs/ for one source file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf8"), filename=str(path))
    except (OSError, SyntaxError):
        return set()
    out: set[Path] = set()
    package_dir = PROGRAMS
    rel = path.relative_to(PROGRAMS)
    package_parts = list(rel.parent.parts)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                base = package_parts[: max(0, len(package_parts) - node.level + 1)]
                if node.module:
                    base += node.module.split(".")
                for alias in node.names:
                    candidates = [base, base + [alias.name]]
                    for parts in candidates:
                        resolved = module_path(".".join(parts), package_dir)
                        if resolved:
                            out.add(resolved)
            elif node.module and node.module.split(".", 1)[0] == "tlhdig":
                resolved = module_path(node.module, package_dir)
                if resolved:
                    out.add(resolved)
                for alias in node.names:
                    resolved = module_path(f"{node.module}.{alias.name}", package_dir)
                    if resolved:
                        out.add(resolved)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".", 1)[0] == "tlhdig":
                    resolved = module_path(alias.name, package_dir)
                    if resolved:
                        out.add(resolved)
    return out


def import_closure(entrypoints: set[Path]) -> set[Path]:
    seen: set[Path] = set()
    todo = list(sorted(entrypoints))
    while todo:
        path = todo.pop()
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        for dep in sorted(local_imports(path)):
            if dep not in seen:
                todo.append(dep)
    return seen


def covered(path: str, patterns: tuple[str, ...]) -> bool:
    """Approximate GitHub paths-filter matching for research classification."""
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def main() -> int:
    patterns = workflow_paths()
    gates = gate_entrypoints()
    entrypoints = {
        ROOT / path for path in gates.values() if isinstance(path, str)
    }
    # The orchestrator and independent verifier are certification dependencies too.
    entrypoints.update(
        {
            PROGRAMS / "release_check.py",
            PROGRAMS / "check_stamp.py",
            PROGRAMS / "tlhdig" / "certification.py",
            PROGRAMS / "tlhdig" / "release_policy.py",
            PROGRAMS / "tlhdig" / "stamp.py",
        }
    )
    code = import_closure(entrypoints)
    tracked = sorted({str(path.relative_to(ROOT)) for path in code} | set(EXPLICIT_INPUTS))
    uncovered = [path for path in tracked if not covered(path, patterns)]
    payload = {
        "schema": 1,
        "workflow": str(WORKFLOW.relative_to(ROOT)),
        "workflowPathFilters": list(patterns),
        "gates": gates,
        "dependencyPaths": tracked,
        "coveredDependencyPaths": [path for path in tracked if covered(path, patterns)],
        "uncoveredDependencyPaths": uncovered,
        "mutableOutputRootsExcludedFromProtectedIdentity": list(MUTABLE_OUTPUT_ROOTS),
        "notes": [
            "Import discovery is conservative research evidence, not a production dependency solver.",
            "Corpus bytes are represented by programs/corpus.sha256 plus the corpus-identity gate; the 24k XML files are not individually listed here.",
            "A workflow path filter can refresh evidence but cannot by itself make stale evidence fail closed at verification time.",
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
