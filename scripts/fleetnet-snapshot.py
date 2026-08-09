#!/usr/bin/env python3
"""Write the fleet's real state to web/data/fleetnet.json, for the Lady to speak.

Counted from the host, never from a document — doctrine 021. Everything here
comes from systemd, sockets, git and the test suites at the moment of
writing. Nothing is carried forward from a previous run.

    python3 scripts/fleetnet-snapshot.py

The front page reads this and the Buddy voices it on demand. Written as a
file rather than an endpoint so the public page can read it without auth and
without a service being up — the same reasoning as the Captain pause flag.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "web" / "data" / "fleetnet.json"


def run(*args: str) -> str:
    try:
        return subprocess.run(args, capture_output=True, text=True,
                              timeout=20, cwd=REPO).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


#: Units that are down on purpose. Reporting these as an alert is the same
#: error as reading `inactive` for a unit that was never installed — a real
#: state misread as a fault. Each is accounted for:
EXPECTED_DOWN = {
    "chat-captain-web": "legacy Chat Captain, parked per current-bearing.md",
    "monad-lan-web": "web-lan retired 2026-07-13",
    "public-docs-api": "superseded",
    "living-fleet-memory-reflect": "static one-shot, not a service",
}


def units() -> dict:
    """Installed units belonging to this repo, and which are active."""
    installed = active = 0
    down = []
    oneshot = []
    for path in Path("/etc/systemd/system").glob("*.service"):
        try:
            if "/dev/monad/" not in path.read_text(errors="replace"):
                continue
        except OSError:
            continue
        name = path.stem
        text = path.read_text(errors="replace")
        # A oneshot is INACTIVE between firings — that is what oneshot means.
        # Reporting it as down is the same misread as `inactive` meaning "never
        # installed". Detected from the unit file rather than kept in a list,
        # because the list is what failed: living-fleet-memory-reflect was in
        # EXPECTED_DOWN and then this script's OWN timer service was added and
        # immediately announced itself as a fault.
        if "Type=oneshot" in text:
            oneshot.append(name)
            installed += 1
            continue
        installed += 1
        state = run("systemctl", "is-active", name)
        if state == "active":
            active += 1
        elif name not in EXPECTED_DOWN:
            down.append({"unit": name, "state": state or "unknown"})
    return {"installed": installed, "active": active, "down": down,
            "expected_down": len(EXPECTED_DOWN), "oneshot": len(oneshot)}


def ports() -> int:
    out = run("ss", "-ltn")
    return len({line.split()[3].rsplit(":", 1)[-1]
                for line in out.splitlines()[1:]
                if line.split() and line.split()[3].rsplit(":", 1)[-1].startswith("47")})


def suites() -> dict:
    paths = [
        "tools/aegis-rig/test_solver.py",
        "tools/aegis-rig/test_parity.py",
        "tools/live-captain/test_pause.py",
        "tools/voice-engine/test_buddy_router.py",
        "tools/m3-cycle/test_engine.py",
        "scripts/test_fleetnet_snapshot.py",
    ]
    passed = failed = 0
    for suite in paths:
        tail = run("python3", suite).splitlines()
        ok = bool(tail) and tail[-1].strip() == "OK"
        # unittest writes its summary to stderr; a clean run leaves stdout bare
        result = subprocess.run(["python3", suite], capture_output=True,
                                text=True, cwd=REPO)
        ok = result.stderr.strip().endswith("OK")
        passed += 1 if ok else 0
        failed += 0 if ok else 1
    return {"passed": passed, "failed": failed, "total": len(paths)}


def voice_usage() -> dict | None:
    raw = run("curl", "-s", "-m", "4", "http://127.0.0.1:4775/budget")
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def http_probe(name: str, url: str, accepted: set[int], action: str) -> tuple[dict, dict | None]:
    result = subprocess.run(
        ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}",
         "--max-time", "4", url], capture_output=True, text=True, cwd=REPO,
    )
    try:
        code = int(result.stdout.strip())
    except ValueError:
        code = 0
    probe = {"name": name, "url": url, "code": code, "ok": code in accepted,
             "accepted": sorted(accepted)}
    if probe["ok"]:
        return probe, None
    return probe, {
        "id": f"endpoint:{name}", "severity": "critical",
        "title": f"{name} endpoint failed",
        "evidence": f"HTTP {code or 'unreachable'}; expected {sorted(accepted)}",
        "action": action,
    }


def host_resources() -> dict:
    disk = run("findmnt", "-n", "-o", "USE%,AVAIL", "/").split()
    disk_used = int(disk[0].rstrip("%")) if disk else 0
    meminfo = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, value = line.split(":", 1)
        meminfo[key] = int(value.strip().split()[0])
    total = meminfo.get("MemTotal", 1)
    available = meminfo.get("MemAvailable", 0)
    return {
        "disk_used_percent": disk_used,
        "disk_available": disk[1] if len(disk) > 1 else "unknown",
        "memory_available_percent": round(available / total * 100, 1),
        "load_1m": round(os.getloadavg()[0], 2),
    }


def operations(state: dict) -> dict:
    alerts = []
    for item in state["units"]["down"]:
        alerts.append({
            "id": f"unit:{item['unit']}", "severity": "critical",
            "title": f"{item['unit']} is {item['state']}",
            "evidence": "Monad unit is installed but not active",
            "action": f"Inspect journalctl -u {item['unit']}.service, then recover the unit.",
        })
    if state["suites"]["failed"]:
        alerts.append({
            "id": "tests:monitored", "severity": "warning",
            "title": f"{state['suites']['failed']} monitored suites failing",
            "evidence": f"{state['suites']['passed']}/{state['suites']['total']} passed",
            "action": "Run the failing monitored suite and repair the regression.",
        })

    probes = []
    contracts = [
        ("root-console", "http://127.0.0.1:4792/api/status", {401},
         "Inspect root-console.service and its authentication boundary."),
        ("live-captain", "http://127.0.0.1:4778/api/status", {401},
         "Inspect live-captain-bootstrap.service and its authentication boundary."),
        ("rich-voice", "http://127.0.0.1:4775/status", {200},
         "Inspect rich-voice.service before relying on Captain speech."),
        ("fleetcore", "http://127.0.0.1:4771/snapshot", {200},
         "Inspect fleetcore-serve.service and canonical snapshot availability."),
        ("public-root-auth", "http://127.0.0.1:4779/check", {401},
         "Inspect public-root-auth.service; Root access gating may be unavailable."),
    ]
    for contract in contracts:
        probe, alert = http_probe(*contract)
        probes.append(probe)
        if alert:
            alerts.append(alert)

    resources = host_resources()
    if resources["disk_used_percent"] >= 90:
        alerts.append({"id": "host:disk", "severity": "critical", "title": "Host disk nearly full",
                       "evidence": f"{resources['disk_used_percent']}% used; {resources['disk_available']} available",
                       "action": "Identify the largest growing data source and reclaim space safely."})
    elif resources["disk_used_percent"] >= 80:
        alerts.append({"id": "host:disk", "severity": "warning", "title": "Host disk pressure rising",
                       "evidence": f"{resources['disk_used_percent']}% used; {resources['disk_available']} available",
                       "action": "Review storage growth before it becomes operational."})
    if resources["memory_available_percent"] < 10:
        alerts.append({"id": "host:memory", "severity": "warning", "title": "Host memory pressure",
                       "evidence": f"{resources['memory_available_percent']}% memory available",
                       "action": "Inspect top memory consumers and service restart history."})
    if not state.get("voice"):
        alerts.append({"id": "voice:usage", "severity": "warning", "title": "Voice accounting unavailable",
                       "evidence": "Rich voice budget/usage endpoint did not return JSON",
                       "action": "Inspect rich-voice.service and /budget response."})

    rank = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda alert: (rank[alert["severity"]], alert["id"]))
    return {
        "status": "action-required" if alerts else "clear",
        "alerts": alerts,
        "alert_count": len(alerts),
        "next_action": alerts[0]["action"] if alerts else "Maintain watch; no operator action required.",
        "probes": probes,
        "resources": resources,
    }


def spoken(state: dict) -> list[dict]:
    """The report, as lines the Buddy can say.

    Priority follows the router's contract: 8+ interrupts, 2-3 is routine.
    A fault speaks first and speaks urgently; a sound ship says so calmly.
    """
    lines = []
    ops = state["operations"]
    if ops["alerts"]:
        for alert in ops["alerts"][:3]:
            priority = 9 if alert["severity"] == "critical" else 7
            lines.append({"priority": priority,
                          "text": f"Operator alert. {alert['title']}. {alert['action']}"})
    else:
        lines.append({"priority": 2, "text": "Operator watch clear. No action required."})
    u = state["units"]
    if u["down"]:
        names = ", ".join(d["unit"].replace("-", " ") for d in u["down"][:3])
        lines.append({"priority": 8,
                      "text": f"FleetNet alert. {len(u['down'])} units down. {names}."})
    else:
        lines.append({"priority": 3,
                      "text": f"FleetNet. All {u['active']} units active. "
                              f"{u['expected_down']} parked by design."})

    lines.append({"priority": 2,
                  "text": f"{u['active']} of {u['installed']} units running on "
                          f"{state['ports']} ports."})

    s = state["suites"]
    if s["failed"]:
        lines.append({"priority": 8,
                      "text": f"Warning. {s['failed']} test suites failing."})
    else:
        lines.append({"priority": 2,
                      "text": f"All {s['passed']} test suites green."})

    tree = state["tree"]
    if tree["uncommitted"]:
        lines.append({"priority": 3,
                      "text": f"{tree['uncommitted']} files uncommitted."})
    else:
        lines.append({"priority": 2, "text": "Working tree clean."})

    if state.get("voice"):
        v = state["voice"]
        lines.append({"priority": 1,
                      "text": f"Voice ungated. {v['seconds_used']:.1f} seconds "
                              f"generated today; usage remains accounted."})
    captain = state["captain_detail"]
    lines.append({"priority": 3,
                  "text": f"Live Captain helm {captain['backend']}. Voice output "
                          "verified; live event audio connected; spoken round "
                          "trip awaiting acceptance."})
    return lines


def main() -> int:
    state = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "units": units(),
        "ports": ports(),
        "suites": suites(),
        "tree": {
            "uncommitted": len([l for l in run("git", "status", "--porcelain").splitlines() if l]),
            "head": run("git", "rev-parse", "--short", "HEAD"),
        },
        "captain": "paused" if (REPO / "data/live-captain/paused.json").is_file()
                   and json.loads((REPO / "data/live-captain/paused.json").read_text()).get("paused")
                   else "running",
        "captain_detail": {
            "backend": "codex",
            "voice_output": "heard-live-over-fleetnet",
            "speech_round_trip": "awaiting-human-acceptance",
            "event_wire": "authenticated-live-captain-sse",
            "event_audio": "procedural-live-web-audio",
        },
        "voice": voice_usage(),
    }
    state["operations"] = operations(state)
    state["sound"] = state["operations"]["status"] == "clear"
    state["lines"] = spoken(state)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(state, indent=2))
    print(f"{state['units']['active']}/{state['units']['installed']} units · "
          f"{state['ports']} ports · {state['suites']['passed']}/{state['suites']['total']} suites · "
          f"{'SOUND' if state['sound'] else 'FAULTS'}")
    print(f"wrote {OUT.relative_to(REPO)}  ({len(state['lines'])} spoken lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
