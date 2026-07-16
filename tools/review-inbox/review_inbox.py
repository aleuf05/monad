#!/usr/bin/env python3
"""Human Review Inbox V0.1 -- read-side unification of World Intake and
Mission Bus's review cards into one shared feed.

GLUE-05 (docs/architecture/human-review-inbox-v0.1.md) designed this
explicitly as a projection, not a new decision path: "Current endpoints can
remain... canon adjudication POSTs continue to go to World Intake." This
script never writes to either system -- it only reads World Intake's
/proposals endpoint and Mission Bus's existing mission-reviews.json
projection, normalizes both into the same ReviewCard shape, and publishes
the merged result.

See docs/engineering-orders/review-inbox-v0.1.md for scope.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request


HEARTBEAT_SECONDS = 600
HTTP_TIMEOUT_SECONDS = 5

WORLD_INTAKE_PENDING_URL = os.environ.get(
    "MONAD_WORLD_INTAKE_PENDING_URL", "http://127.0.0.1:4773/proposals?status=pending"
)
MISSION_REVIEWS_PATH = os.path.join("web", "data", "mission-reviews.json")
OUTPUT_PATH = os.path.join("web", "data", "review-inbox.json")


def repo_root():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(here))


def timestamp_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def normalize_world_intake_card(proposal):
    """Map a native World Intake assertion card onto GLUE-05's ReviewCard
    shape, per human-review-inbox-v0.1.md's "Mapping onto World Intake"
    table. proposed_data retains the full native card, assertion_id
    included, so nothing about the original is lost in translation."""
    assertion_id = proposal["assertion_id"]
    provenance = proposal.get("provenance") or {}
    subject = proposal.get("subject", "?")
    change = proposal.get("proposed_change") or {}
    summary = proposal.get("supporting_source_excerpt") or (
        f"{subject}: {change.get('operation', '?')} -> {change.get('value', '?')}"
    )
    return {
        "schema_version": "monad.review.v0.1",
        "review_id": f"review.world-intake.{assertion_id}",
        "mission_id": None,
        "artifact_id": f"artifact.world-intake.{assertion_id}",
        "artifact_type": "fleetcore-command-proposal",
        "revision": 1,
        "status": "pending",
        "requested_action": "accept-fleetcore-command",
        "required_authority": "human-command",
        "evidence_refs": [provenance.get("source_id")] if provenance.get("source_id") else [],
        "conflicts": proposal.get("conflicts", []),
        "summary": summary,
        "proposed_data": proposal,
        "created_at": provenance.get("source_timestamp"),
        "supersedes_review_id": None,
        "source_system": "world-intake",
        "decide_at": "../world-intake/",
    }


def fetch_world_intake_cards():
    request = urllib.request.Request(
        WORLD_INTAKE_PENDING_URL, headers={"User-Agent": "monad-review-inbox/1"}, method="GET"
    )
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
        payload = json.load(response)
    return [normalize_world_intake_card(p) for p in payload.get("proposals", [])]


def load_mission_bus_cards(root):
    path = os.path.join(root, MISSION_REVIEWS_PATH)
    try:
        with open(path, "r", encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, ValueError):
        return []
    cards = []
    for card in data.get("cards", []):
        merged = dict(card)
        merged["source_system"] = "mission-bus"
        merged["decide_at"] = "../agent-ops/"
        cards.append(merged)
    return cards


def build_inbox(root):
    now = timestamp_utc()
    world_intake_error = None
    mission_bus_error = None

    try:
        world_intake_cards = fetch_world_intake_cards()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError, KeyError) as error:
        world_intake_cards = []
        world_intake_error = str(error)

    try:
        mission_bus_cards = load_mission_bus_cards(root)
    except (OSError, ValueError) as error:
        mission_bus_cards = []
        mission_bus_error = str(error)

    all_cards = world_intake_cards + mission_bus_cards
    all_cards.sort(key=lambda c: c.get("created_at") or "", reverse=True)
    pending_count = sum(1 for c in all_cards if c.get("status") == "pending")

    return {
        "schema_version": "monad.reviewInbox.v0.1",
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "pending_count": pending_count,
        "sources": {
            "world_intake": {
                "card_count": len(world_intake_cards),
                "error": world_intake_error,
            },
            "mission_bus": {
                "card_count": len(mission_bus_cards),
                "error": mission_bus_error,
            },
        },
        "cards": all_cards,
    }


def write_inbox(root, inbox):
    path = os.path.join(root, OUTPUT_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(inbox, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp_path, path)
    return path


def stand_watch(once=False):
    root = repo_root()
    next_run = time.monotonic()

    while True:
        inbox = build_inbox(root)
        path = write_inbox(root, inbox)
        print(
            "{} review-inbox regenerated: {} cards ({} pending) -> {}".format(
                inbox["generated_at"],
                len(inbox["cards"]),
                inbox["pending_count"],
                os.path.relpath(path, root),
            ),
            flush=True,
        )
        if once:
            return 0

        next_run += HEARTBEAT_SECONDS
        time.sleep(max(0, next_run - time.monotonic()))


def parse_args():
    parser = argparse.ArgumentParser(description="Regenerate the shared Human Review Inbox feed.")
    parser.add_argument("--once", action="store_true", help="write one feed and exit")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        return stand_watch(once=args.once)
    except KeyboardInterrupt:
        print("Review Inbox relieved.", file=sys.stderr)
        return 0
    except OSError as error:
        print("review_inbox.py: {}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
