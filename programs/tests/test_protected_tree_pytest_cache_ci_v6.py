"""Review-driven RED: ordinary CI must not create untrusted pytest bytecode caches."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CI = ROOT / ".github" / "workflows" / "ci.yml"


def test_ci_disables_python_bytecode_before_pytest_and_stamp_verification():
    text = CI.read_text(encoding="utf8")
    job = text.split("jobs:\n", 1)[1].split("    steps:\n", 1)[0]
    assert 'PYTHONDONTWRITEBYTECODE: "1"' in job
