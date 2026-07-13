# FleetCore Live

A thin browser client for FleetCore's live server (`fleetcore-serve`, see `../../fleetcore/README.md`). It holds no simulation state of its own — every vessel position, clock reading, and watch-log line on screen came from a `WorldSnapshot` the server pushed a moment earlier.

This is different from every other toy in this repository: Fleet Motion, Periscope, and Bridge each run their own client-side simulation and sync through `localStorage`/`MonadFleetState`. FleetCore Live has no simulation loop; it draws whatever the server sends and forwards user actions back as `Command` messages.

## Run

1. Start the live server from the repository root:

   ```sh
   cargo run --manifest-path fleetcore/Cargo.toml --bin serve -- --port 4771
   ```

2. Serve this directory (or the repository root) over HTTP — opening `index.html` directly as a `file://` URL also works, since the page only needs a WebSocket to the server, not to itself:

   ```sh
   python3 -m http.server 8080
   ```

3. Open `http://localhost:8080/toys/fleetcore-live/` (or wherever you served it). The default server field is `ws://localhost:4771/ws`; click **Connect** if it doesn't connect automatically.

## Command Authority

This page has no way to supply a token — there is no token field or URL param. Whatever the server decides to grant this connection is what you get: the "Authority" status strip entry reads "Command" if the server's `connected` message reports `command_authority: true`, or "Read-only" otherwise (Pause/Resume and time-scale stay disabled). See `docs/deployment.md`'s "Known limitation" note for the current state of `fleetcore-serve`'s own gating (as of this writing it grants authority to every connection unconditionally, regardless of any `--command-token` the process was started with).

## What it shows

- A Leaflet map with one marker per vessel (amber = flagship, teal = scout, pale blue = passive traffic), positioned from the server's live snapshot.
- A status strip: link state, clock state, current tick, and simulation time.
- A vessel list — click an entry (or its map marker) to pan the map to it and open its popup.
- A watch-event log, newest first.
- Pause/Resume and a time-scale control, which send `pause-clock` / `resume-clock` / `set-time-scale` commands over the same WebSocket. Since the server broadcasts to every connected client, opening this page in two tabs (or two browsers) shows both staying in sync — pausing in one tab pauses the other's view too, because there is only one world, not two synced copies of it.

## Protocol

See `docs/architecture/fleetcore-api.md` for the full contract. In short: the server sends `{"type":"connected","command_authority":...}` then `{"type":"snapshot","snapshot":{...}}` on connect, another `snapshot` after every tick or applied command, and this page sends a raw `Command` JSON object (e.g. `{"type":"pause-clock"}`) to request a change when it has command authority.

## Reconnection

If the WebSocket drops, the page shows "Reconnecting in Ns…" and retries with exponential backoff (capped at 15s). A command sent while disconnected is silently dropped — there is no send-queue/retry for the write path yet.
