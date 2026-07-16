# Monad Watchman

Watchman is a permanent, non-LLM heartbeat process. Every five minutes it
appends one JSON object to:

```text
logs/agents/watchman/YYYY/YYYY-MM-DD_watch.jsonl
```

Each entry records UTC time, hostname, system uptime when available, the
current Git commit, repository path, disk capacity, and local Qdrant health.
Watchman reads repository state but writes only to its own log directory.

Watchman also checks the five other live services under `services`, each via
its systemd unit (`ActiveState`/`SubState`/`NRestarts`, read-only via
`systemctl show`) plus a real HTTP GET against its own API where one exists:

| key                      | unit                                | http check         |
| ------------------------ | ------------------------------------ | ------------------- |
| `fleetcore_serve`        | `fleetcore-serve.service`            | `GET /snapshot`     |
| `world_intake`           | `world-intake.service`               | `GET /proposals`    |
| `living_fleet_memory`    | `living-fleet-memory.service`        | `GET /captains/summary` |
| `living_captain_status`  | `living-captain-status.service`      | `GET /status`       |
| `living_fleet`           | `living-fleet.service`               | none — background loop, checked instead by staleness of `data/living-fleet/runtime.json`'s `last_cycle_at` (flagged `stale` past `MONAD_LIVING_FLEET_STALE_SECONDS`, default 60s) |

A service's `process.state` is `warning` if the unit has restarted at least
once since it was last (re)started (`restarts` > 0) even while currently
running, `failed` if systemd reports the unit failed, and `unknown` if
`systemctl` itself couldn't be queried. Health check URLs are overridable via
`MONAD_FLEETCORE_HEALTH_URL`, `MONAD_WORLD_INTAKE_HEALTH_URL`,
`MONAD_LIVING_FLEET_MEMORY_HEALTH_URL`, and
`MONAD_LIVING_CAPTAIN_STATUS_HEALTH_URL`.

## Granite Installation

The service file assumes the Granite account is `cgl` and the repository is
located at `/home/cgl/dev/monad`. Adjust `User`, `WorkingDirectory`, and
`ExecStart` before installation if Granite differs.

```sh
cd ~/dev/monad
sudo cp systemd/monad-watchman.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable monad-watchman
sudo systemctl start monad-watchman
sudo systemctl status monad-watchman
```

The Qdrant health endpoint defaults to `http://127.0.0.1:6333/healthz`. Set
`MONAD_QDRANT_HEALTH_URL` in the service if the local endpoint differs.

## Local Test

Write one heartbeat and exit:

```sh
./watchman.py --once
```

The test appends a real entry to Watchman's own daily log. It does not modify
Helmsman or Captain logs.
