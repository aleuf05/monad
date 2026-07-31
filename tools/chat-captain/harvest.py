"""Validates harvest proposals the Captain returns before they are ever
stored. Per the packet: "The Captain recognizes possible goodness. The ship
guarantees that the candidate survives" -- but only a structurally valid
candidate. Malformed proposals are dropped, never stored as garbage and
never crash the turn.
"""

from __future__ import annotations

from typing import Any, Optional

import database


def validate_proposal(proposal: Any) -> Optional[dict[str, Any]]:
    if not isinstance(proposal, dict):
        return None
    proposal_type = proposal.get("type")
    title = proposal.get("title")
    summary = proposal.get("summary")
    if proposal_type not in database.HARVEST_TYPES:
        return None
    if not isinstance(title, str) or not title.strip():
        return None
    if not isinstance(summary, str) or not summary.strip():
        return None
    confidence = proposal.get("confidence")
    if confidence is not None:
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = None
        else:
            if not (0.0 <= confidence <= 1.0):
                confidence = None
    provenance_note = proposal.get("provenance_note")
    if not isinstance(provenance_note, str):
        provenance_note = None
    return {
        "type": proposal_type,
        "title": title.strip(),
        "summary": summary.strip(),
        "confidence": confidence,
        "provenance_note": provenance_note,
    }
