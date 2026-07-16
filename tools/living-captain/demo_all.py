#!/usr/bin/env python3
"""Run the Living Captain operator demos in one pass."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run(label: str, script: str) -> bool:
    print(f"== {label} ==")
    result = subprocess.run([sys.executable, str(ROOT / script)])
    print()
    return result.returncode == 0


def main() -> int:
    print("Living Captain operator demo bundle")
    print()
    restart_ok = run("restart continuity", "demo_restart.py")
    boundary_ok = run("custody and spend boundaries", "demo_boundary.py")

    if restart_ok and boundary_ok:
        print("RESULT: PASS -- both Living Captain demos completed successfully.")
        return 0

    print("RESULT: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
