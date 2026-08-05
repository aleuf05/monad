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


def voice_budget() -> dict | None:
    raw = run("curl", "-s", "-m", "4", "http://127.0.0.1:4775/budget")
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def spoken(state: dict) -> list[dict]:
    """The report, as lines the Buddy can say.

    Priority follows the router's contract: 8+ interrupts, 2-3 is routine.
    A fault speaks first and speaks urgently; a sound ship says so calmly.
    """
    lines = []
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
                      "text": f"Voice budget, {v['usd_used']:.4f} of "
                              f"{v['usd_limit']} dollars used."})
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
        "voice": voice_budget(),
    }
    state["sound"] = not state["units"]["down"] and state["suites"]["failed"] == 0
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
