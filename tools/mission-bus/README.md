# Mission Bus — Kraken Pilot

Append-only, read-only-to-FleetCore inquiry pilot.

```sh
python3 tools/mission-bus/mission_bus.py create
python3 tools/mission-bus/mission_bus.py execute
python3 tools/mission-bus/mission_bus.py review accept \
  --reviewer lieutenant.cgl --authority human-command --reason "..."
python3 tools/mission-bus/mission_bus.py project
```

The SQLite Mission Record is runtime state under `data/mission-record/`. The
public, rebuildable Agent Ops projection is `web/data/mission-ops.json`.
