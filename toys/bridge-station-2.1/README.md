# Bridge Station 2.1

The reference implementation of the operator loop: **Select → Act → World changes → Instruments respond.** A single React component (`src/App.jsx`, the artifact this project scaffolds) composites a Fleet Motion-style chart and a Periscope-style bearing display, both driven by one in-memory vessel array — click a contact, its bearing/range appear on Periscope; select the own ship (MONAD), set a waypoint, and both panels update as it turns and moves toward it.

**This is the first project in the Monad repo with a build step.** Every other toy (`toys/fleet-motion/`, `toys/periscope/`, `toys/bridge-2/`, etc.) is deliberately zero-dependency vanilla HTML/CSS/JS — no bundler, no `npm install`, open `index.html` and it runs. This one genuinely can't be: it's a JSX component using `lucide-react`, and JSX isn't valid browser JavaScript without a build step. Scaffolded with Vite specifically because the source artifact required it, not as a new default for future toys.

## Relationship to `toys/bridge-2/`

Separate artifact, not a successor. Deliberately not touched or replaced:

|  | `toys/bridge-2/` | `toys/bridge-station-2.1/` |
|---|---|---|
| Data source | Live `fleetcore-serve` WebSocket, real backend | In-memory mock state, no backend at all |
| Interaction | Read-only observer, no controls | Select contacts, set MONAD's waypoint |
| Stack | Vanilla JS, no build step | React + Vite, JSX, `npm run build` |

Both currently exist because they answer different questions: 2.0 proves FleetCore's real API works end to end; 2.1 is a UI/interaction reference for what commanding a vessel could look like, not yet wired to anything real.

**Update:** `toys/bridge-station-3.0/` is the merge of the two — this component's UI wired to real `fleetcore-serve` data, with Set Waypoint sending a real `Command`. This project (2.1) is left as-is, a frozen mock-data reference, not superseded or deleted.

## Run locally

```sh
cd toys/bridge-station-2.1
npm install
npm run dev
```

## Build and serve

```sh
npm run build
npx serve -s dist -p 8080
```

`serve` binds `0.0.0.0` by default (confirm with `serve --help` — the `-l` flag needs a full URI like `tcp://0.0.0.0:8080`, a bare `host:port` string will error; `-p <port>` alone is enough since the default host is already `0.0.0.0`).

## Deployment: LAN-only

Deployed at `http://192.168.0.100:8080/` — reachable from Granite's LAN, not the public internet. No auth layer, by design (see the original packet: "LAN is treated as the trust boundary"). Since there's no backend at all, there's nothing to expose beyond the static bundle itself.

Ad hoc `nohup npx serve ...` process — does not survive a Granite reboot, and has no systemd unit. Not addressed in this pass; durability was explicitly deferred by the operator.

## Known gaps vs. the packet's acceptance criteria

- "Fleet Motion, Periscope, selection, and Set Waypoint all function as in the prototype" — verified via Playwright against the deployed build: contact selection shows bearing/range and an "OBSERVE ONLY" tag, selecting MONAD exposes "Set Waypoint," clicking the chart in waypoint mode plots a course line and the ship's own course visibly changes over subsequent ticks (confirmed a real heading change, 250° → 268°, not just a UI state flip).
- "Service survives a reboot" — not set up, flagged per the packet's own reporting instructions, not silently skipped.
