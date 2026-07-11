# Monad

Monad is an AI-assisted software engineering workspace. The current product
thread is a maritime command environment: a set of browser instruments, a shared
fleet-state layer, and an emerging deterministic world model called FleetCore.

The repository is intentionally experimental, but the newest artifacts are meant
to be runnable, inspectable, and documented.

## Start Here

The main browser entry point is the Bridge:

```powershell
cd "G:\My Drive\monad"
python -m http.server 8080
```

Open:

```text
http://localhost:8080/toys/bridge/
```

Bridge Station is the unified command console. It embeds the live browser
instruments and shows Bridge-owned engineering state. The individual instruments
still run independently.

## Current Front Door

### Bridge Station

Path:

```text
toys/bridge/
```

Bridge Station is the flagship browser artifact. It composes Fleet Motion,
Periscope Station, Watchbook, and an engineering/status rail into one command
deck. It reads shared browser-local fleet state through `toys/shared/fleet-state.js`.

Run it from the repository root with the local HTTP server command above.

## Main Browser Instruments

### Fleet Motion

Path:

```text
toys/fleet-motion/
```

Fleet Motion is the browser-side fleet movement and navigation toy. It renders
Monad, escorts, local passive traffic, routes, wakes, and operator controls on a
Leaflet map. It writes the browser-local shared fleet state that Bridge and
Periscope can observe.

### Periscope Station

Path:

```text
toys/periscope/
```

Periscope is a Canvas 2D optical watch instrument. It renders an atmospheric
sea view and vessel contacts derived from the shared fleet state when available,
with a local fallback when standalone.

### Watchbook

Path:

```text
toys/watchbook/
```

Watchbook is a read-only browser viewer for repository logs. Its generated
manifest is `toys/watchbook/log-index.json`; the plaintext `logs/` tree remains
canonical.

### FleetCore Live

Path:

```text
toys/fleetcore-live/
```

FleetCore Live is a thin browser client for the FleetCore live server. Unlike
Fleet Motion and Periscope, it does not run its own simulation. It displays
snapshots streamed by the FleetCore server.

## FleetCore

Path:

```text
fleetcore/
```

FleetCore is Monad's Rust world-model prototype. It owns deterministic maritime
state: vessels, routes, simulation clock, commands, events, persistence, replay,
and snapshots.

Common commands:

```powershell
cargo run --manifest-path fleetcore/Cargo.toml -- init
cargo run --manifest-path fleetcore/Cargo.toml -- inspect
cargo run --manifest-path fleetcore/Cargo.toml -- step 30
cargo run --manifest-path fleetcore/Cargo.toml -- snapshot
cargo test --manifest-path fleetcore/Cargo.toml
```

Live server:

```powershell
cargo run --manifest-path fleetcore/Cargo.toml --bin serve -- --port 4771
```

See `fleetcore/README.md` and `docs/architecture/fleetcore-api.md` for the
current protocol and limitations.

## Shared Browser State

Path:

```text
toys/shared/fleet-state.js
```

This file defines the browser-side fleet-state helper used by the Bridge and
Periscope. Fleet Motion remains the main writer in the static browser-toy path.
FleetCore has its own authoritative world model and can be adapted into this
shape when needed.

## Other Artifacts

```text
toys/reaction-diffusion-painter/
```

A standalone Gray-Scott reaction-diffusion painting toy.

```text
web/
```

Static public-site material and mirrored deployed toy assets.

```text
docs/
```

Architecture notes, deployment notes, FleetCore design documents, and operating
doctrine.

```text
logs/
```

Plaintext operational logs used by Watchbook.

```text
tools/
```

Small utility scripts, including Watchbook index generation and telemetry sync.

## Repository Layout

```text
.
|-- docs/
|   |-- architecture/
|   `-- deployment/
|-- fleetcore/
|   |-- src/
|   |-- data/
|   `-- tests/
|-- logs/
|-- tools/
|-- toys/
|   |-- bridge/
|   |-- fleet-motion/
|   |-- fleetcore-live/
|   |-- periscope/
|   |-- reaction-diffusion-painter/
|   |-- shared/
|   `-- watchbook/
|-- web/
|-- bridge.py
|-- bridge_web.py
|-- duo_chain.py
|-- helmsman_v2.py
`-- README.md
```

## Development Notes

- Most browser toys are static HTML, CSS, and JavaScript.
- Fleet Motion uses Leaflet/OpenStreetMap tiles, so it needs network access for
  map tiles unless cached.
- Periscope uses Canvas 2D and local image assets.
- FleetCore is Rust and uses Cargo.
- No top-level build step exists for the static browser artifacts.
- Serve from the repository root when testing cross-toy browser state.

## Useful Local Commands

Run the main Bridge:

```powershell
cd "G:\My Drive\monad"
python -m http.server 8080
```

Regenerate Watchbook index:

```powershell
python tools/build-log-index.py
```

Check JavaScript syntax for a toy:

```powershell
node --check toys/bridge/app.js
```

Run FleetCore tests:

```powershell
cargo test --manifest-path fleetcore/Cargo.toml
```

## Status

Monad is under active development. The Bridge is the best place to start today.
FleetCore is the direction for a persistent authoritative world, while the
current browser instruments remain useful standalone engineering artifacts.

## License

License information has not been finalized.
