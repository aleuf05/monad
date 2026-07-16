#!/usr/bin/env python3
"""Report unexpected drift between public toy source and the live web tree."""

from __future__ import annotations

import argparse
import filecmp
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "toys"
LIVE_ROOT = ROOT / "web" / "toys"

# These artifacts have deployment-specific transforms documented in
# docs/deployment.md. They are checked by their build/copy procedures instead.
INTENTIONAL_FILE_DIVERGENCE = {
    "bridge/index.html",
    "fleetcore-control/index.html",
    "fleetcore-live/index.html",
    "periscope/duck.js",
}
SOURCE_ONLY_DIRS = {
    "bridge-station-3.0",  # Vite source; web contains its build output.
    "watchbook",  # Deliberately not public.
}
SOURCE_ONLY_PARTS = {"mk2", "mk3", "mk4", "node_modules"}
SOURCE_ONLY_SUFFIXES = {".md"}
SOURCE_ONLY_NAMES = {
    ".gitignore",
    ".oxlintrc.json",
    "package.json",
    "package-lock.json",
    "test_vessel_events_cursor.js",
    "test_voice.js",
    "vite.config.js",
}
SOURCE_ONLY_PATHS = {"periscope/assets/source/scout-sprite-chromakey.png"}


def public_source_files() -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in SOURCE_ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(SOURCE_ROOT)
        relative_string = relative.as_posix()
        if relative.parts[0] in SOURCE_ONLY_DIRS:
            continue
        if SOURCE_ONLY_PARTS.intersection(relative.parts):
            continue
        if path.suffix in SOURCE_ONLY_SUFFIXES or path.name in SOURCE_ONLY_NAMES:
            continue
        if relative_string in SOURCE_ONLY_PATHS:
            continue
        files[relative_string] = path
    return files


def live_files_for_public_sources(public_toys: set[str]) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in LIVE_ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(LIVE_ROOT)
        if relative.parts[0] not in public_toys or relative.parts[0] in SOURCE_ONLY_DIRS:
            continue
        files[relative.as_posix()] = path
    return files


def find_drift() -> list[str]:
    source = public_source_files()
    public_toys = {Path(relative).parts[0] for relative in source}
    live = live_files_for_public_sources(public_toys)
    drift: list[str] = []

    for relative in sorted(source.keys() - live.keys()):
        drift.append(f"missing live file: web/toys/{relative}")
    for relative in sorted(live.keys() - source.keys()):
        drift.append(f"live-only file: web/toys/{relative}")
    for relative in sorted(source.keys() & live.keys()):
        if relative in INTENTIONAL_FILE_DIVERGENCE:
            continue
        if not filecmp.cmp(source[relative], live[relative], shallow=False):
            drift.append(f"content differs: toys/{relative} != web/toys/{relative}")
    return drift


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    drift = find_drift()
    if drift:
        print("Unexpected toy deployment drift:")
        for finding in drift:
            print(f"- {finding}")
        return 1
    print("Public toy source and live runtime files are in sync.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
