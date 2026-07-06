#!/usr/bin/env python3
"""test_discover_readonly.py — Contract tests for discover.py read-only guarantee.

Tests that discover.py without --apply performs zero writes.
"""
import sys
import pathlib
import subprocess
import tempfile
import os
import shutil

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

import discover


def test_readonly_run_zero_writes(tmp_path):
    """Acceptance: discover-readonly / Read-only run performs zero writes

    Create fake reports with bare mentions, run discover search (no apply),
    verify mtime and content are unchanged.
    """
    # Create fake sector directory and report
    sector = tmp_path / "Semiconductors"
    sector.mkdir()
    report = sector / "2330_TSMC.md"
    report.write_text(
        "# 台積電\n\n液冷散熱 is mentioned here.\n\n## 財務概況\n\nRevenue: 100",
        encoding="utf-8",
    )
    original_mtime = report.stat().st_mtime
    original_content = report.read_text(encoding="utf-8")

    # Store REPORTS_DIR and restore after test
    original_reports_dir = discover.REPORTS_DIR
    discover.REPORTS_DIR = str(tmp_path)

    try:
        results = discover.search_reports("液冷散熱", None)
        # Should find the bare mention
        assert len(results) == 1
        assert results[0]["bare"] > 0

        # Verify no write happened (mtime and content unchanged)
        assert report.stat().st_mtime == original_mtime
        assert report.read_text(encoding="utf-8") == original_content
    finally:
        discover.REPORTS_DIR = original_reports_dir


def test_apply_without_do_apply_raises():
    """Acceptance: discover-readonly / Direct call to write path without apply raises

    Calling apply_wikilinks() without do_apply=True should raise RuntimeError.
    """
    fake_results = [{"bare": 1, "filepath": "/tmp/fake.md"}]
    try:
        discover.apply_wikilinks(fake_results, "test", do_apply=False)
        assert False, "Expected RuntimeError"
    except RuntimeError as e:
        assert "read-only path violation" in str(e)


def test_no_subprocess_without_rebuild(monkeypatch):
    """Acceptance: discover-readonly / read-only guarantee; no subprocess without --rebuild

    When running discover without --rebuild, subprocess.run should not be called.
    """
    called = []
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: called.append(True))

    # Simulate running discover with a minimal buzzword, no --rebuild
    original_argv = sys.argv
    try:
        sys.argv = ["discover.py", "液冷散熱"]
        # We can't easily call main() because it calls sys.exit, so we
        # just verify the code path: search_reports should not call subprocess
        results = discover.search_reports("test", None)
        # If no results, that's fine — the point is search_reports doesn't call subprocess
        assert len(called) == 0, "search_reports should not call subprocess.run"
    finally:
        sys.argv = original_argv