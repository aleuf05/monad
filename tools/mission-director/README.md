# Mission Director

Thin, single-mission orchestration layer over FleetCore (Quacken Transit
001). Consumes FleetCore's real events only — `vessel_events`
(`waypoint_reached`, `route_completed`) and real vessel positions — and
never fabricates simulation progress; the sim stays authoritative. Holds
its own persisted state machine (which phase the mission is in, an
evidence log, dwell timers) but issues only two real FleetCore commands:
`spawn-passive-contact` (the Rubber Ducky, once, at mission start) and
`record-watch-event` (marking real milestones on FleetCore's own log,
visible to every other instrument). No changes to `fleetcore/src/*`.

## State machine

```
MISSION_INITIALIZED
  -> mission start (operator action, spawns the Ducky)
TRANSIT_UNDERWAY
  -> first real waypoint_reached event for the tracked vessel (MONAD)
STRAIT_TRANSIT
  -> real route_completed event (final transit waypoint reached)
APPROACH_QUACKEN
  -> RendezvousReached: Director-derived from real position data
     (distance from MONAD to the Ducky's fixed spawn position <= 500m),
     never fabricated
RENDEZVOUS_HOLD
  -> continuous dwell inside the radius for 30s. Leaving the radius
     early resets the dwell timer to zero -- unmet progress, not a
     stall by itself.
MISSION_COMPLETE
```

Any active phase can also reach:

- **`MISSION_STALLED`** — no relevant real-event progress *and* no real
  vessel motion for 600s (a long leg the vessel is still actively
  transiting is not a stall). Not a failure; halts and awaits operator
  review. `resume` always returns to
  the exact phase it stalled from (never a forced jump — that would
  fabricate progress no real event produced), with that phase's stall
  clock re-armed fresh.
- **`MISSION_ABORTED`** — explicit operator action, any time.
- **`MISSION_FAILED`** — the tracked vessel or the Ducky contact is
  missing from FleetCore's own snapshot.

## Usage

```sh
cd tools/mission-director
python3 mission_director.py start
python3 mission_director.py run           # watches until a terminal phase, Ctrl+C to pause
python3 mission_director.py run --once    # single poll-and-check, e.g. for cron/scripted steps
python3 mission_director.py status
python3 mission_director.py abort "reason"
python3 mission_director.py resume        # only valid from MISSION_STALLED
python3 mission_director.py request-capture --view fleetcore-live --caption "..."
python3 mission_director.py attach-capture <id> <path-or-url>
python3 mission_director.py publish       # regenerate the report without advancing state
```

Set `FLEETCORE_URL` to point at a non-default server (defaults to
`http://localhost:4771`).

## Captures

`CAPTURE_REQUESTED` entries (event, recommended view, caption) are
emitted automatically at meaningful moments (mission start, rendezvous
reached, mission complete) and can also be requested manually. This tool
never takes a screenshot itself — automated headless-browser capture is
explicitly out of scope for this pass. An officer attaches a real
path/URL after the fact with `attach-capture`; the published report
picks it up on the next `run`/`publish`.

## Publishing

Every phase transition (and every `publish`/`attach-capture` call)
regenerates all three report artifacts at
`web/missions/quacken-transit-001/` — Caddy serves `web/` straight off
disk as `https://cameronlampley.com/monad/`, no deploy step:

- `mission.json` — the machine record, full state verbatim.
- `log.md` — human-readable evidence log.
- `index.html` — the public after-action report: summary, event
  timeline, final state, screenshots, anomalies, outcome.

## Boundaries

- No changes to `fleetcore/src/command.rs`, `world.rs`, or any other
  shared-core FleetCore file.
- Only two commands ever issued: `spawn-passive-contact` (once, for the
  Ducky) and `record-watch-event` (milestone markers). Never touches
  `set-route`, clock, or escort-mode commands — MONAD's actual transit
  is driven by whatever operator/toy is flying it; this tool only
  watches.
- No automated screenshot capture, no PDF output, no Facebook
  publishing — all explicitly out of scope for this pass.
- Tow mechanics (`TowEstablished`) not implemented, not emitted, not
  faked — a dedicated future sprint's scope, not this one's.
