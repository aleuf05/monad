#!/usr/bin/env python3
"""Run the Live Captain tests and append a machine-readable verification record."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROOT_DIR.parent.parent
DEFAULT_LOG_PATH = REPO_ROOT / "data" / "live-captain" / "test-runs.jsonl"
TEST_COMMAND = [sys.executable, "-m", "unittest", "tools/live-captain/test_live_captain.py"]


def build_report(command: list[str], completed: subprocess.CompletedProcess[str], duration: float) -> dict:
    """Build a stable summary without treating console text as the source of pass/fail truth."""
    output = completed.stdout + completed.stderr
    match = re.search(r"Ran (\d+) tests?", output)
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        revision = None
    return {
        "schema": "live-captain-test-run/v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "cwd": str(REPO_ROOT),
        "revision": revision,
        "duration_seconds": round(duration, 3),
        "tests_run": int(match.group(1)) if match else None,
        "exit_code": completed.returncode,
        "result": "pass" if completed.returncode == 0 else "fail",
    }


def append_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report, sort_keys=True) + "\n")


def main() -> int:
    started = time.monotonic()
    completed = subprocess.run(TEST_COMMAND, cwd=REPO_ROOT, text=True, capture_output=True)
    sys.stdout.write(completed.stdout)
    sys.stderr.write(completed.stderr)
    report = build_report(TEST_COMMAND, completed, time.monotonic() - started)
    append_report(DEFAULT_LOG_PATH, report)
    print(f"Verification record: {DEFAULT_LOG_PATH} ({report['result']})")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
