"""Read-only adapters for Living Captain's external sight."""

import json
import urllib.request


def fetch_fleetcore_snapshot(
    url: str = "http://127.0.0.1:4771/snapshot",
    timeout: float = 5.0,
) -> dict:
    """Fetch and return FleetCore's current snapshot."""
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.load(response)


def fetch_world_intake_pending(
    url: str = "http://127.0.0.1:4773/proposals?status=pending",
    timeout: float = 5.0,
) -> list[dict]:
    """Fetch and return World Intake's pending proposal list."""
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.load(response)["proposals"]
