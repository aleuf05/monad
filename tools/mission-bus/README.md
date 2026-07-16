# Mission Bus — Kraken Pilot

Append-only, read-only-to-FleetCore inquiry pilot.

```sh
python3 tools/mission-bus/mission_bus.py create
python3 tools/mission-bus/mission_bus.py execute
python3 tools/mission-bus/mission_bus.py pause --reason "Operator hold"
python3 tools/mission-bus/mission_bus.py resume --reason "Continue inquiry"
python3 tools/mission-bus/mission_bus.py review accept \
  --reviewer lieutenant.cgl --authority human-command --reason "..."
python3 tools/mission-bus/mission_bus.py project
python3 tools/mission-bus/mission_bus.py registry
```

The SQLite Mission Record is runtime state under `data/mission-record/`. The
public, rebuildable Agent Ops projection is `web/data/mission-ops.json`.
The public, rebuildable artifact index is `web/data/mission-artifacts.json`.
It is derived only from Mission Record events, uses record-event locators for
JSON artifacts, excludes superseded revisions, and fails closed on unknown
artifact types.
