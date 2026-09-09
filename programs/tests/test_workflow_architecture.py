"""Architecture sentinels for the stable read-only research workflow (#104)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "research.yml"
TASKS = ROOT / "programs" / "tlhdig" / "workflow_tasks.py"
CLI = ROOT / "programs" / "run_research_task.py"
DOCS = ROOT / "docs" / "WORKFLOWS.md"


def _text(path: Path) -> str:
    assert path.exists(), f"missing required workflow architecture file: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf8")


def _load_tasks():
    assert TASKS.exists(), "stable research-task registry is missing"
    spec = importlib.util.spec_from_file_location("workflow_tasks_test", TASKS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_stable_research_workflow_exists_and_is_manual_only():
    text = _text(WORKFLOW)
    assert "workflow_dispatch:" in text
    assert "pull_request:" not in text
    assert "schedule:" not in text


def test_stable_research_workflow_is_read_only_and_secret_free():
    text = _text(WORKFLOW)
    assert "permissions:" in text
    assert "contents: read" in text
    assert "contents: write" not in text
    assert "actions: write" not in text
    assert "secrets:" not in text
    assert "git push" not in text
    assert "gh api" not in text


def test_stable_research_workflow_avoids_arbitrary_shell_input():
    text = _text(WORKFLOW)
    lowered = text.lower()
    assert "eval " not in lowered
    assert "bash -c" not in lowered
    assert "sh -c" not in lowered
    assert "inputs.command" not in lowered
    assert "inputs.script" not in lowered
    # User-controlled task text must reach the shell through an environment variable,
    # not direct `${{ inputs.task }}` interpolation inside a `run:` command.
    run_lines = [line for line in text.splitlines() if line.lstrip().startswith("run:")]
    assert all("inputs.task" not in line for line in run_lines)


def test_stable_research_workflow_uses_explicit_ref_and_registered_task_cli():
    text = _text(WORKFLOW)
    assert "ref: ${{ inputs.ref }}" in text
    assert "RESEARCH_TASK: ${{ inputs.task }}" in text
    assert "python programs/run_research_task.py" in text
    assert '"$RESEARCH_TASK"' in text


def test_task_registry_is_allowlist_based_and_has_renderer_features_task(tmp_path):
    module = _load_tasks()
    assert "renderer-features" in module.TASKS
    with pytest.raises(module.UnknownResearchTask):
        module.command_for("definitely-not-registered", tmp_path)

    command = module.command_for("renderer-features", tmp_path)
    assert isinstance(command, tuple)
    assert command
    assert all(isinstance(part, str) and part for part in command)
    assert not any(part in {"bash", "sh", "-c", "eval"} for part in command)
    assert "research_renderer_features.py" in " ".join(command)


def test_research_cli_is_stable_and_does_not_use_shell_execution():
    text = _text(CLI)
    assert "workflow_tasks" in text
    assert "subprocess.run" in text
    assert "shell=True" not in text
    assert "os.system" not in text
    assert "eval(" not in text


def test_workflow_docs_make_ticket_local_yaml_an_exception():
    text = _text(DOCS).lower()
    assert "research.yml" in text
    assert "ticket-local" in text
    assert "exception" in text
    assert "contents: read" in text
    assert "write-capable" in text
