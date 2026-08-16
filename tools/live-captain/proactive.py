"""Captain-Initiated Proactive Notification Subsystem.

Implements Section 13 of Live Captain Commissioning.
Allows Live Captain to initiate messages and alerts without waiting for an immediate user turn.
"""

from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROOT_DIR.parent.parent

from habitat_store import HabitatStore
from comms import OutboundMessage, Action, Urgency, WebChannelAdapter

DB_PATH = REPO_ROOT / "data" / "live-captain" / "habitat.db"
STORE = HabitatStore(DB_PATH)


class ProactiveNotifier:
    """Dispatches Captain-initiated messages into persistent conversation threads."""

    def __init__(self, store: Optional[HabitatStore] = None):
        self.store = store or STORE

    def notify(
        self,
        text: str,
        semantic_role: str = "captain",     # "captain", "engineering", "alert"
        urgency: str = Urgency.NORMAL.value,
        thread_id: Optional[str] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Posts a proactive message to a thread and persists it."""
        # Find or select target thread
        target_thread_id = thread_id
        if not target_thread_id:
            threads = self.store.list_threads(limit=1)
            if threads:
                target_thread_id = threads[0]["id"]
            else:
                new_thread = self.store.create_thread("Captain Station Logs")
                target_thread_id = new_thread["id"]

        # Build OutboundMessage
        action_objs = [Action.from_dict(a) for a in (actions or [])]
        outbound = OutboundMessage(
            destination=target_thread_id,
            text=text,
            actions=action_objs,
            urgency=urgency,
            semantic_role=semantic_role,
            timestamp=time.time(),
        )

        # Persist message to Habitat store
        saved_msg = self.store.add_message(
            thread_id=target_thread_id,
            role=semantic_role,
            text=text,
            attachments=[],
            tool_events=[{"name": "proactive_notification", "summary": f"Urgency: {urgency}", "role": semantic_role}],
        )

        return {
            "status": "notified",
            "thread_id": target_thread_id,
            "message": saved_msg,
            "outbound": outbound.to_dict(),
        }


NOTIFIER = ProactiveNotifier()
