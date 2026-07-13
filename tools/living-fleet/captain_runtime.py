#!/usr/bin/env python3
"""Shared persistent runtime for the Living Fleet escort captains.

The runtime never mutates world state. It reads FleetCore's public snapshot,
asks a provider for one bounded posture decision, and submits that structured
intent through FleetCore's normal command endpoint. The built-in doctrine
provider is the safe deterministic fallback; an external model/provider can be
connected with MONAD_CAPTAIN_PROVIDER_COMMAND without changing this runtime.
"""

import argparse
import json
import math
import os
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = Path(__file__).with_name("captains.json")
DEFAULT_STATE_DIR = ROOT / "data" / "living-fleet"
ALLOWED_POSTURES = {
    "hold-station",
    "advance-screen",
    "widen-flank",
    "cover-rear",
    "investigate-contact",
    "recover-formation",
    "emergency-separation",
}
EARTH_RADIUS_METERS = 6_371_000.0


def distance_meters(start, end):
    lat1 = math.radians(start["lat"])
    lat2 = math.radians(end["lat"])
    dlat = lat2 - lat1
    dlng = math.radians(end["lng"] - start["lng"])
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_METERS * math.asin(math.sqrt(a))


def vessel(snapshot, vessel_id):
    return next((item for item in snapshot.get("vessels", []) if item.get("id") == vessel_id), None)


def passive_contacts(snapshot):
    return [item for item in snapshot.get("vessels", []) if item.get("kind") == "passive-traffic"]


class DoctrineProvider:
    name = "doctrine-fallback-v1"

    def decide(self, observation, captain, memory):
        own = observation["own_vessel"]
        leader = observation["flagship"]
        peers = observation["other_vessels"]
        nearest_vessel = min(
            peers,
            key=lambda item: distance_meters(own["position"], item["position"]),
            default=None,
        )
        nearest_distance = (
            distance_meters(own["position"], nearest_vessel["position"])
            if nearest_vessel
            else float("inf")
        )
        formation_distance = distance_meters(own["position"], leader["position"])

        if nearest_distance < 300:
            return {
                "posture": "emergency-separation",
                "target_contact_id": None,
                "objective": "Create safe separation from nearby traffic.",
                "assessment": f"Nearest vessel is {nearest_distance:.0f} m away; separation takes priority.",
                "reconsider_after_ticks": 20,
            }
        if formation_distance > 5_000:
            return {
                "posture": "recover-formation",
                "target_contact_id": None,
                "objective": "Recover assigned formation geometry.",
                "assessment": f"Assigned vessel is {formation_distance:.0f} m from Monad.",
                "reconsider_after_ticks": 45,
            }

        if captain["captain_id"] == "captain.alpha":
            contacts = observation["contacts"]
            nearest_contact = min(
                contacts,
                key=lambda item: distance_meters(own["position"], item["position"]),
                default=None,
            )
            contact_distance = (
                distance_meters(own["position"], nearest_contact["position"])
                if nearest_contact
                else float("inf")
            )
            if nearest_contact and contact_distance <= 10_000:
                return {
                    "posture": "investigate-contact",
                    "target_contact_id": nearest_contact["id"],
                    "objective": f"Identify and screen contact {nearest_contact['callsign']}.",
                    "assessment": f"Contact {nearest_contact['callsign']} is {contact_distance:.0f} m away in the forward operating area.",
                    "reconsider_after_ticks": 30,
                }
            return {
                "posture": "advance-screen",
                "target_contact_id": None,
                "objective": "Maintain a useful forward reconnaissance screen.",
                "assessment": "No contact requires close investigation; formation geometry is stable.",
                "reconsider_after_ticks": 60,
            }
        if captain["captain_id"] == "captain.bravo":
            return {
                "posture": "widen-flank",
                "target_contact_id": None,
                "objective": "Preserve maneuvering room on Monad's flank.",
                "assessment": "Formation is stable; a wider lateral station improves security and turning room.",
                "reconsider_after_ticks": 60,
            }
        return {
            "posture": "cover-rear",
            "target_contact_id": None,
            "objective": "Maintain rear guard and formation integrity.",
            "assessment": "Formation is stable; the rear sector remains Charlie's primary responsibility.",
            "reconsider_after_ticks": 60,
        }


class CommandProvider:
    def __init__(self, command):
        self.command = shlex.split(command)
        if not self.command:
            raise ValueError("provider command is empty")
        self.name = f"command:{Path(self.command[0]).name}"

    def decide(self, observation, captain, memory):
        request = {"observation": observation, "captain": captain, "memory": memory}
        completed = subprocess.run(
            self.command,
            input=json.dumps(request),
            text=True,
            capture_output=True,
            timeout=20,
            check=True,
        )
        return json.loads(completed.stdout)


def validate_decision(decision):
    if not isinstance(decision, dict):
        raise ValueError("provider response must be a JSON object")
    posture = decision.get("posture")
    if posture not in ALLOWED_POSTURES:
        raise ValueError(f"unsupported posture: {posture!r}")
    if not str(decision.get("objective", "")).strip():
        raise ValueError("objective is required")
    if not str(decision.get("assessment", "")).strip():
        raise ValueError("assessment is required")
    reconsider = int(decision.get("reconsider_after_ticks", 60))
    if reconsider < 5 or reconsider > 10_000:
        raise ValueError("reconsider_after_ticks must be between 5 and 10,000")
    if posture == "investigate-contact" and not decision.get("target_contact_id"):
        raise ValueError("investigate-contact requires target_contact_id")
    return {
        "posture": posture,
        "target_contact_id": decision.get("target_contact_id"),
        "objective": str(decision["objective"])[:240],
        "assessment": str(decision["assessment"])[:500],
        "reconsider_after_ticks": reconsider,
    }


class CaptainRuntime:
    def __init__(self, fleetcore_url, captains, state_dir, provider):
        self.fleetcore_url = fleetcore_url.rstrip("/")
        self.captains = captains
        self.state_dir = Path(state_dir)
        self.state_path = self.state_dir / "runtime.json"
        self.provider = provider
        self.fallback = DoctrineProvider()
        self.memory = self._load_memory()

    def _load_memory(self):
        try:
            return json.loads(self.state_path.read_text())
        except (OSError, ValueError):
            return {"schema_version": 1, "captains": {}, "last_cycle_at": None}

    def _save_memory(self):
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.memory["last_cycle_at"] = time.time()
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.memory, indent=2) + "\n")
        tmp.replace(self.state_path)

    def get_snapshot(self):
        with urllib.request.urlopen(f"{self.fleetcore_url}/snapshot", timeout=5) as response:
            return json.load(response)

    def post_command(self, command):
        request = urllib.request.Request(
            f"{self.fleetcore_url}/command",
            data=json.dumps(command).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            return json.load(response)

    def observation_for(self, snapshot, captain):
        own = vessel(snapshot, captain["vessel_id"])
        flagship = next(
            (item for item in snapshot.get("vessels", []) if item.get("kind") == "flagship"),
            None,
        )
        if not own or not flagship:
            raise ValueError("assigned vessel or flagship is missing from authoritative snapshot")
        return {
            "world_id": snapshot["world_id"],
            "tick": snapshot["tick"],
            "event_sequence": snapshot["event_sequence"],
            "clock_state": snapshot["clock_state"],
            "own_vessel": own,
            "flagship": flagship,
            "contacts": passive_contacts(snapshot),
            "other_vessels": [item for item in snapshot.get("vessels", []) if item["id"] != own["id"]],
            "current_intent": next(
                (item for item in snapshot.get("escort_intents", []) if item["vessel_id"] == own["id"]),
                None,
            ),
            "recent_decisions": [
                item
                for item in snapshot.get("agent_decisions", [])[-12:]
                if item["vessel_id"] == own["id"]
            ],
        }

    def report(self, snapshot, captain, status, provider, message):
        return self.post_command(
            {
                "type": "report-captain-runtime",
                "captain_id": captain["captain_id"],
                "vessel_id": captain["vessel_id"],
                "status": status,
                "provider": provider,
                "message": message,
                "observed_tick": snapshot["tick"],
            }
        )

    def cycle(self):
        snapshot = self.get_snapshot()
        controls = {item["vessel_id"]: item for item in snapshot.get("captain_controls", [])}
        if snapshot.get("agent_fleet_paused"):
            for captain in self.captains:
                control = controls.get(captain["vessel_id"])
                if control and control.get("enabled"):
                    self.report(snapshot, captain, "idle", self.provider.name, "Agent fleet paused by operator.")
            self._save_memory()
            return []

        results = []
        for captain in self.captains:
            # Refresh per captain: a slow external provider or another captain's
            # command must not make the next decision stale before submission.
            snapshot = self.get_snapshot()
            controls = {item["vessel_id"]: item for item in snapshot.get("captain_controls", [])}
            control = controls.get(captain["vessel_id"])
            if not control or not control.get("enabled"):
                continue
            observation = self.observation_for(snapshot, captain)
            current = observation.get("current_intent")
            if current and current.get("reconsider_at_tick", 0) > snapshot["tick"]:
                continue

            captain_memory = self.memory["captains"].setdefault(
                captain["captain_id"], {"recent_decisions": []}
            )
            provider = self.provider
            runtime_status = "idle"
            try:
                decision = validate_decision(provider.decide(observation, captain, captain_memory))
            except Exception as error:
                provider = self.fallback
                runtime_status = "fallback"
                decision = validate_decision(provider.decide(observation, captain, captain_memory))
                captain_memory["last_provider_error"] = str(error)[:240]

            command = {
                "type": "submit-escort-intent",
                "captain_id": captain["captain_id"],
                "vessel_id": captain["vessel_id"],
                "posture": decision["posture"],
                "target_contact_id": decision["target_contact_id"],
                "objective": decision["objective"],
                "assessment": decision["assessment"],
                "observed_tick": snapshot["tick"],
                "observed_event_sequence": snapshot["event_sequence"],
                "reconsider_at_tick": snapshot["tick"] + decision["reconsider_after_ticks"],
            }
            result_snapshot = self.post_command(command)
            record = next(
                item
                for item in reversed(result_snapshot.get("agent_decisions", []))
                if item["captain_id"] == captain["captain_id"]
            )
            captain_memory.update(
                {
                    "current_objective": decision["objective"],
                    "last_assessment": decision["assessment"],
                    "last_posture": decision["posture"],
                    "last_decision_id": record["decision_id"],
                }
            )
            captain_memory["recent_decisions"] = (
                captain_memory.get("recent_decisions", []) + [record]
            )[-20:]
            self.report(
                result_snapshot,
                captain,
                runtime_status,
                provider.name,
                f"{record['outcome']}: {decision['posture']} — {record['result']}",
            )
            results.append(record)
        self._save_memory()
        return results


def load_captains(path):
    with open(path, encoding="utf-8") as stream:
        captains = json.load(stream)
    if not isinstance(captains, list) or not captains:
        raise ValueError("captain config must be a non-empty list")
    return captains


def parse_args():
    parser = argparse.ArgumentParser(description="Run the shared Living Fleet captain runtime.")
    parser.add_argument("--fleetcore-url", default=os.getenv("FLEETCORE_URL", "http://127.0.0.1:4771"))
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR))
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    provider_command = os.getenv("MONAD_CAPTAIN_PROVIDER_COMMAND")
    provider = CommandProvider(provider_command) if provider_command else DoctrineProvider()
    runtime = CaptainRuntime(
        args.fleetcore_url,
        load_captains(args.config),
        args.state_dir,
        provider,
    )
    while True:
        try:
            records = runtime.cycle()
            for record in records:
                print(
                    f"{record['decision_id']} {record['captain_id']} "
                    f"{record['posture']} {record['outcome']}",
                    flush=True,
                )
        except (OSError, ValueError, urllib.error.URLError) as error:
            print(f"living-fleet: cycle failed: {error}", file=sys.stderr, flush=True)
            if args.once:
                return 1
        if args.once:
            return 0
        time.sleep(max(1.0, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
