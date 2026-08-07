"""Read-only Living Captain Intake projection over existing intake services."""

from __future__ import annotations

import json
import urllib.request
from collections import Counter
from datetime import datetime, timezone

WORLD_PENDING_URL = "http://127.0.0.1:4773/proposals?status=pending"
WORLD_DEFERRED_URL = "http://127.0.0.1:4773/proposals?status=deferred"
DOCX_RECENT_URL = "http://127.0.0.1:4797/api/recent"


def _fetch(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=4) as response:
        return json.loads(response.read())


def _safe(fetch, url: str) -> tuple[dict, str | None]:
    try:
        value = fetch(url)
        return (value if isinstance(value, dict) else {}), None
    except Exception as exc:  # projection reports a source fault; never masks it as empty
        return {}, str(exc)


def build(fetch=_fetch) -> dict:
    pending_body, pending_error = _safe(fetch, WORLD_PENDING_URL)
    deferred_body, deferred_error = _safe(fetch, WORLD_DEFERRED_URL)
    docx_body, docx_error = _safe(fetch, DOCX_RECENT_URL)
    pending = pending_body.get("proposals") or []
    deferred = deferred_body.get("proposals") or []
    staged = docx_body.get("entries") or []
    classes = Counter(item.get("assertion_class", "unknown") for item in pending)
    conflict_count = sum(bool(item.get("conflicts")) for item in pending)
    individual_count = sum(bool(item.get("requires_individual_approval")) for item in pending)

    # Keep the upstream queue authoritative while ensuring the bounded Captain
    # view cannot hide a proposal that needs individual attention behind six
    # routine cards.  Python's stable sort preserves source order within each
    # risk tier.
    prioritized = sorted(
        pending,
        key=lambda item: (
            not bool(item.get("requires_individual_approval")),
            not bool(item.get("conflicts")),
        ),
    )
    cards = []
    for item in prioritized[:6]:
        change = item.get("proposed_change") or {}
        cards.append({
            "id": item.get("assertion_id") or item.get("id"),
            "subject": item.get("subject") or "Unresolved subject",
            "class": item.get("assertion_class") or "unknown",
            "operation": change.get("operation") if isinstance(change, dict) else str(change),
            "confidence": item.get("confidence"),
            "conflicts": len(item.get("conflicts") or []),
            "individual_approval": bool(item.get("requires_individual_approval")),
            "source": (item.get("provenance") or {}).get("source_id"),
        })

    errors = {
        name: error for name, error in (
            ("world_pending", pending_error),
            ("world_deferred", deferred_error),
            ("packet_drop", docx_error),
        ) if error
    }
    return {
        "schema": "monad.captainIntake.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "degraded" if errors else "ready",
        "world": {
            "pending": len(pending),
            "deferred": len(deferred),
            "individual_approval": individual_count,
            "with_conflicts": conflict_count,
            "classes": dict(sorted(classes.items())),
            "cards": cards,
            "review_url": "/toys/world-intake/",
        },
        "packets": {
            "staged": len(staged),
            "entries": [{k: entry.get(k) for k in ("name", "path", "bytes", "mtime")} for entry in staged[:6]],
        },
        "errors": errors,
        "sources": [WORLD_PENDING_URL, WORLD_DEFERRED_URL, DOCX_RECENT_URL],
    }
