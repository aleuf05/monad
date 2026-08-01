"""Immutable experiment manifests and replay digest helpers."""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from typing import Any


def make_manifest(*, run_id: str, seed: int, mode: str, control: str, q_schedule: list[float], perturbation_schedule: list[dict[str, Any]], compute_budget: dict[str, Any], code_commit: str | None = None) -> dict[str, Any]:
    if code_commit is None:
        try:
            code_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        except (OSError, subprocess.CalledProcessError):
            code_commit = "unknown"
    manifest = {
        "run_id": run_id, "schema_version": "mc0.manifest.v1", "code_commit": code_commit,
        "seed": seed, "mode": mode, "control": control, "q_schedule": q_schedule,
        "perturbation_schedule": perturbation_schedule, "compute_budget": compute_budget,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    canonical = dict(manifest)
    canonical.pop("created_at")
    manifest["config_hash"] = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()
    return manifest


def replay_digest(events: list[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(events, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
