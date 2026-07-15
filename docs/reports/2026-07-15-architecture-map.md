# Architecture Map

Date: 2026-07-15

Prepared for: Captain / Lieutenant

Scope: live service graph, public routes, storage, and source/live splits
derived from inspected reality on this host. This is a consolidation report,
not a design proposal.

## Top-Level Shape

Monad currently runs as a single repo-backed production tree at
`/home/cgl/dev/monad`, served directly from `web/` by Caddy. The live surface
is split into four kinds of things:

1. public static artifacts under `web/`
2. loopback-only Python/Rust services behind Caddy routes
3. a few host services that inspect or schedule those loopback services
4. Qdrant as a local derived-index dependency, with health checked at
   `http://127.0.0.1:6333/healthz`

## Service Graph

| Service | State | Working directory | Core role | Key edges |
|---|---|---|---|---|
| `caddy` | active | system default | public front door | serves `web/`, proxies loopback APIs |
| `fleetcore-serve` | active | `/home/cgl/dev/monad` | authoritative FleetCore world + WS/API server | no upstream app dependency; exposes `4771` |
| `world-intake` | active | `/home/cgl/dev/monad` | review/compile/submit pipeline for narrative intake | `Requires=fleetcore-serve.service`; exposes `4773` |
| `living-fleet` | active | `/home/cgl/dev/monad` | persistent escort captain runtime | `Wants=fleetcore-serve.service`; exposes no port |
| `living-fleet-memory` | active | `/home/cgl/dev/monad` | captain-memory inspector API | `Requires=living-fleet.service`; exposes `4772` |
| `living-fleet-memory-reflect.timer` | active | waiting | schedules captain-memory reflection | triggers `living-fleet-memory-reflect.service` every 30 min |
| `monad-watchman` | active | `/home/cgl/dev/monad` | host heartbeat/health logger | independent host watcher; uses Qdrant health URL env |
| `living-captain-status` | active | `/home/cgl/dev/monad` | Living Captain read-only status API | exposes `4774`; public via Caddy |

The live service dependencies are shallow:

- `world-intake` depends on `fleetcore-serve`
- `living-fleet-memory` depends on `living-fleet`
- `living-fleet-memory-reflect.timer` targets `living-fleet-memory-reflect.service`
- `living-fleet` depends on `fleetcore-serve` for observation
- `caddy` fronts the public app and proxies the loopback services
- `monad-watchman` checks Qdrant health on `127.0.0.1:6333/healthz`

## Ports and Routes

Verified listeners:

| Port | Listener | Purpose |
|---|---|---|
| `80` | `caddy` | public HTTP |
| `443` | `caddy` | public HTTPS |
| `4771` | `fleetcore-serve` | FleetCore snapshot / command / WebSocket server |
| `4772` | `living-fleet-memory` | captain-memory inspector |
| `4773` | `world-intake` | intake API |
| `4774` | `living-captain-status` | Living Captain status API |

Observed health check:

| Target | Result | Notes |
|---|---|---|
| `http://127.0.0.1:6333/healthz` | healthy | reached through `monad-watchman`'s configured `MONAD_QDRANT_HEALTH_URL` |

Verified Caddy routes in `/etc/caddy/Caddyfile`:

| Route | Upstream | Notes |
|---|---|---|
| `/fleetcore-ws/*` | `127.0.0.1:4771` | public FleetCore live WebSocket/HTTP path |
| `/captain-memory-api/*` | `127.0.0.1:4772` | public memory inspector path |
| `/world-intake-api/*` | `127.0.0.1:4773` | public intake API path |
| `/living-captain-api/*` | `127.0.0.1:4774` | public Living Captain status path |
| `/monad/portainer/*` | `https://localhost:9443` | deliberate operator-infrastructure exception |
| bare root | `web/` | public static site |

Live checks confirmed:

- `http://127.0.0.1:4771/snapshot` -> 200
- `http://127.0.0.1:4773/proposals?status=pending` -> 200
- `http://127.0.0.1:4774/status` -> 200
- `https://cameronlampley.com/` -> 200
- `https://cameronlampley.com/living-captain-api/status` -> 200

## Storage and State

Observed durable state:

| Area | Path | Notes |
|---|---|---|
| FleetCore | `data/fleetcore/` | `world.json`, `events.jsonl`, checkpoints, snapshots |
| Living Fleet | `data/living-fleet/` | `runtime.json`, `memory.db` |
| World Intake | `data/world-intake.sqlite3` | SQLite review/adjudication store |
| Living Captain | `data/living-captain/` | `state.json`, `actions.jsonl` |

What the storage tells us:

- FleetCore keeps the durable command history in `events.jsonl` and a bounded
  recent event tail in live state.
- World Intake keeps source, interpretation, adjudication, command, canon, and
  correction records separate in SQLite.
- Living Captain keeps identity, custody manifest, spend counters, and action
  log entries in its own local state directory.

## Source / Live Split

The repo does not ship everything under `toys/` into `web/toys/`.

- `toys/` is the source tree.
- `web/toys/` is the live tree served by Caddy.
- Public toys must be copied into `web/toys/` to count as shipped.
- Source docs, READMEs, tests, and reports stay in `toys/` or `docs/` and are
  not part of the live copy.

Observed counts:

- `web/toys`: 40 files
- `toys`: 62 files

That gap is expected. It reflects docs/tests/source material that should not be
deployed, plus a few deliberate deployment-time divergences.

Notable intentional divergences:

- `web/toys/fleetcore-live/` defaults to the public FleetCore WebSocket URL.
- `web/toys/fleetcore-control/` follows the same public server URL pattern.
- `web/toys/bridge/` contains the deployed Watchbook-to-Ship's-Log redirect
  instead of the source's original standalone Watchbook path.
- `web/toys/bridge-station-3.0/` is build output, not a raw source copy.
- `web/toys/bridge-station-3.0/fleet-state.js` exists in the live bundle as a
  generated asset; there is no same-path source file under `toys/`.

Deployed live artifacts currently include:

- `web/toys/fleetcore-live/`
- `web/toys/fleetcore-control/`
- `web/toys/agent-ops/`
- `web/toys/world-intake/`
- `web/toys/living-captain/`
- `web/toys/bridge/`
- `web/toys/periscope/`
- `web/toys/fleet-motion/`
- `web/toys/radio-console/`
- `web/toys/bridge-station-3.0/`

## Unreachable or Unverified Areas

- Container inventory was not fully verified. `docker ps` could not access the
  Docker socket, and `podman` is not installed on this host.
- Qdrant port `6334` was not independently verified in this pass. The only
  directly observed Qdrant edge is the HTTP health probe on `6333`.
- Any deeper classification of stale/duplicate worktrees belongs in the
  separate GA-01 audit.
- The architecture of `watchman.py` itself is tracked separately in WM-01;
  this report only confirms the host service exists and is active.

## Short Verdict

The live architecture is coherent:

- a single repo root backs the public site and the local services
- Caddy is the public boundary
- FleetCore, World Intake, Living Fleet, Living Captain, and Watchman are all
  active
- the source/live split is intentional and visible

The main unverified corner in this pass is container runtime inventory, not the
web/service path.
