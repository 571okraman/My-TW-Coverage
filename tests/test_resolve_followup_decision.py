"""test_resolve_followup_decision.py — 6a enum: keep-unverified decision choice."""
import subprocess
import sys
from pathlib import Path


_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _run_resolve(*extra_args):
    """Run resolve_followup.py via subprocess and return result."""
    cmd = [
        sys.executable, str(_SCRIPTS / "resolve_followup.py"),
        "FU-00000000-001",
        "--status", "resolved",
        "--result", "test",
        "--source", "https://example.com",
        "--dry-run",
    ] + list(extra_args)
    return subprocess.run(cmd, capture_output=True, text=True)


def test_decisions_constant_has_keep_unverified():
    """DECISIONS constant includes keep-unverified."""
    spec = __import__("importlib.util").util.spec_from_file_location(
        "resolve_followup", _SCRIPTS / "resolve_followup.py")
    mod = __import__("importlib.util").util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert "keep-unverified" in mod.DECISIONS
    assert "keep" in mod.DECISIONS
    assert "drop" in mod.DECISIONS
    assert "promote" in mod.DECISIONS


def test_decision_keep_unverified_accepted():
    """--decision keep-unverified must NOT be rejected by argparse."""
    result = _run_resolve("--decision", "keep-unverified")
    # argparse should NOT reject; it may fail later (DB/FU not found)
    assert "invalid choice" not in result.stderr, \
        f"--decision keep-unverified rejected: {result.stderr[:200]}"


def test_decision_invalid_rejected():
    """--decision with unknown value must be rejected by argparse."""
    result = _run_resolve("--decision", "maybe")
    assert result.returncode != 0
    assert "invalid choice" in result.stderr or "argument --decision" in result.stderr, \
        f"Expected argparse rejection for 'maybe': {result.stderr[:200]}"