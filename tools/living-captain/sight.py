"""Read-only adapters for Living Captain's external sight."""

import json
import urllib.request


DEFAULT_ALLOWED_REQUESTS = (
    ("GET", "http://127.0.0.1:4771/snapshot"),
    ("GET", "http://127.0.0.1:4773/proposals?status=pending"),
)


class CustodyViolation(RuntimeError):
    """Raised when a request falls outside the V0.2 custody manifest."""


def custody_manifest() -> dict:
    return {
        "allowed_requests": [
            {"method": method, "url": url} for method, url in DEFAULT_ALLOWED_REQUESTS
        ]
    }


def _check_request_allowed(url: str, method: str) -> None:
    normalized_method = method.upper()
    if normalized_method != "GET":
        raise CustodyViolation(
            f"blocked {normalized_method} {url}: non-GET requests are outside the custody manifest"
        )
    if (normalized_method, url) not in DEFAULT_ALLOWED_REQUESTS:
        raise CustodyViolation(
            f"blocked {normalized_method} {url}: URL is not in the custody manifest"
        )


def request_json(
    url: str,
    *,
    method: str = "GET",
    timeout: float = 5.0,
) -> dict:
    _check_request_allowed(url, method)
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.load(response)

def fetch_fleetcore_snapshot(
    url: str = "http://127.0.0.1:4771/snapshot",
    timeout: float = 5.0,
) -> dict:
    """Fetch and return FleetCore's current snapshot."""
    return request_json(url, timeout=timeout)


def fetch_world_intake_pending(
    url: str = "http://127.0.0.1:4773/proposals?status=pending",
    timeout: float = 5.0,
) -> list[dict]:
    """Fetch and return World Intake's pending proposal list."""
    return request_json(url, timeout=timeout)["proposals"]
