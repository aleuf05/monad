# Monad Deployment

## POLICY: Live tests, rapid iteration, no staging

There is no staging environment and there isn't going to be one. Verification
happens against the real `https://cameronlampley.com/` -- that *is* the test
environment, by design (see "Deployment" below: no deploy step, editing
`web/` edits production directly). Prefer shipping and iterating live over
building out elaborate local test harnesses first.

- Favor rapid, reversible changes over exhaustive pre-validation. Get the
  feature actually working and visible on the live site, then iterate.
- Don't let caution slow down making a feature work. This is a
  single-operator demo project (see the security note further down) --
  the bar is "does it run and can the Lt. see it," not "has this been
  hardened."
- This does not relax the URL/port policy right below -- "test live" means
  the real domain, not a throwaway port standing in for it.

## POLICY: No strange URLs or ports

Every piece of public-facing functionality must be discoverable by plainly
browsing `https://cameronlampley.com/` -- linked from the homepage or
reachable by clicking through it, on the standard port, on the real domain.
No bare IPs, no non-standard ports, no LAN-only hostnames, no "it works if
you know the exact path" artifacts. If a change lives only in `toys/<name>/`
(source) and hasn't been copied into `web/toys/<name>/` (the live copy),
it does not count as shipped, no matter how thoroughly it was tested
locally -- verify against the real production URL before calling it done.

**Click-reachable from the root, not just resolvable.** Every feature needs
an actual link path starting from `https://cameronlampley.com/` -- a card or
link on the homepage, or something reachable from one. Knowing the URL
because it's in a doc or a commit message doesn't make it discoverable.
Shipping a toy means adding its nav entry in the same pass, not leaving it
to be found later.

**No prefix but the bare root.** The app is served only at
`https://cameronlampley.com/` -- no `/monad/` segment, no other prefix. The
old `/monad/` routes are fully retired (see `docs/deployment/public-hatch.md`)
and confirmed 404 as of 2026-07-13; only `/monad/portainer/*` remains, as a
deliberate, separately-protected exception for operator infrastructure, not
the app. Don't introduce a second prefix for anything new.

**Deploy to the live app always, as part of finishing the work, not as a
separate later step.** When a public toy under `toys/<name>/` changes,
re-copy it into `web/toys/<name>/` (and `web/toys/shared/` if
`fleet-state.js` changed) in the same pass, then verify the real
`https://cameronlampley.com/...` URL before reporting the work done.
Watch for path divergences the copy needs (see the `#serverUrl` and
duck-model-path examples below) -- a relative path that's correct from
`toys/<name>/` is not automatically correct once nested one level deeper
under `web/toys/<name>/`.

## POLICY: If the Lt. can't see it on the live app, it doesn't exist

Deployed-but-buried does not count as done. New or changed functionality
must be plainly, obviously visible on the live page it belongs to when the
Lt. glances at it -- not a console log, not a value only visible via
devtools/localStorage, not gated behind a non-obvious click sequence.

Optimize for the moment the Lt. actually sits down to test something: he
should never have to hunt, guess a path, or ask where a thing is. Every new
or changed feature should be the obvious, easy-to-find, easy-to-click thing
on the page he lands on -- this is the same goal as the click-reachable and
on-page-marker rules below, not a separate concern.

- Every new feature should get an obvious on-page marker when it first
  ships -- a visible "NEW" label/badge, a highlighted border/glow, or
  equivalent -- so it's immediately findable without a guided tour. Fine to
  remove once it's no longer new.
- Prefer surfacing state as visible page content (a readout, a status line,
  a label) over anything that would need devtools to observe.
- When reporting a feature done, say where on the live page to look for it.

Granite serves the Monad public site through Caddy, directly from the repo. There is no deploy step.

## Paths

- Granite repo path: `~/dev/monad`
- Live web root: `~/dev/monad/web` (Caddy's `root *` directive in `/etc/caddy/Caddyfile` points here directly)

## Deployment

There isn't one. Editing any file under `web/` changes what `https://cameronlampley.com/` serves immediately — Caddy reads straight off disk, no copy, no reload, no script.

As of 2026-07-12, Caddy's `root` was repointed from `/var/www/monad` (an rsynced copy, kept in sync by the now-retired `scripts/deploy-web.sh`) to `~/dev/monad/web` itself. `/var/www/monad` is no longer read by anything and can be left alone or removed. Permissions were verified compatible with this before switching: the `caddy` user (`caddy:caddy`) has traversal (`x`) on every ancestor directory down to `~/dev/monad/web` and read access on everything inside it, without needing any group changes.

## Doctrine

- Git carries source, and — as of this change — is also the live source. Editing `web/` on Granite is editing production directly.
- The Portainer reverse proxy path must not be disturbed.
- **`web/`, served at `https://cameronlampley.com/`, is the single deploy target.** Do not stand up a second one. Concretely:
  - Never launch an ad hoc local server (`python3 -m http.server <port>`, `npx serve`, etc.) against this repo, even "just to check" a change — `web/` is already live with no deploy step, so verify directly against `https://cameronlampley.com/...` instead. An orphaned instance of exactly this (bound `0.0.0.0`, serving a raw directory listing of the whole repo root including `.git/`) was found running unattended on 2026-07-13 and had to be killed as a live secrets-exposure risk — it wasn't hypothetical.
  - Don't add a second static-serving directory tree (`web-lan/` was one; it's retired — see below) or a second systemd unit for serving `web/`-equivalent content. If a toy genuinely needs network isolation from the public internet, that's a decision to raise explicitly, not something to default into by copying files to a new path.
  - If you start any process while testing (a dev server, a background watch loop, anything bound to a port), kill it once you're done, or hand it off to a real systemd unit if it needs to persist. Don't leave it running unattended.
  - No temporary/throwaway deployments as a stand-in for the real thing — no "just for now" port, subdomain, or ad hoc process instead of actually shipping into `web/`. `toys/<name>/` is source; it isn't done until it's copied into `web/toys/<name>/` and verified at the real URL (see `CLAUDE.md`'s "No strange URLs or ports" policy).
- `web-lan/` and its `monad-lan-web.service` unit were retired 2026-07-13 (see "FleetCore Live Backend" below) — do not recreate this pattern for a new toy without discussing it first.

## Public Artifacts

Interactive artifacts that must be reachable under `https://cameronlampley.com/` live inside `web/toys/`. Each is a plain copy of the matching `toys/<name>/` source directory (runtime files only — READMEs, engineering reports, and other docs stay in the repo and are not copied). Re-copy the relevant source directory into `web/toys/<name>/` whenever that toy changes; `web/toys/` does not update itself, and since there's no deploy step, the copy is live the moment it's saved.

- `web/toys/fleet-motion/` — Fleet Motion Mk2, copied from `toys/fleet-motion/`. Depends on `web/toys/shared/fleet-state.js`.
- `web/toys/periscope/` — Periscope Station, copied from `toys/periscope/` (`index.html`, `style.css`, `app.js`, `state.js`, `scene.js`, `effects.js`, `duck.js`, and the asset files under `assets/backgrounds/` and `assets/sprites/` that `ASSET_PATHS` loads). Depends on `web/toys/shared/fleet-state.js`. **One intentional divergence**: `duck.js`'s GLB path is `../../web/assets/models/uss-rubber-ducky.glb` in source (correct from `toys/periscope/`, two levels up to the repo root, then into `web/assets/models/`) but must be `../../assets/models/uss-rubber-ducky.glb` in the deployed copy (two levels up from `web/toys/periscope/` already reaches `web/`, so no extra `web/` segment) -- copy the file, then re-apply this one-line path fix by hand, don't raw-copy it.
- `web/toys/shared/fleet-state.js` — the `MonadFleetState` contract, copied from `toys/shared/fleet-state.js`. Fleet Motion, Periscope, and Bridge Station all depend on this being present and in sync with the source; a stale copy silently breaks cross-instrument selection sync (this happened once — `web/toys/fleet-motion/` sat un-refreshed since the `7003852` schema-v2 refactor until it was caught during the Bridge Station Mk III deploy).
- `web/toys/agent-ops/` — Agent Operations, copied from `toys/agent-ops/` (`index.html`, `app.js`, `style.css`). Reads Living Fleet state from the public FleetCore WebSocket and sends only captain enable/pause controls. Depends on both FleetCore and the portless captain runtime below.
- `web/toys/bridge-station-3.0/` — Bridge Station 3.0, a `vite build` output (not a plain file copy) from `toys/bridge-station-3.0/`. See "Bridge Station" below for the build config it needed to work from a subpath and to reach the public FleetCore WebSocket. As of `BRIDGE3-CONSOLIDATE-01` (2026-07-16) this is the *only* "look at or command FleetCore" toy — `toys/bridge/`, `toys/fleetcore-live/`, and `toys/fleetcore-control/` are retired, their capability folded into this one as tabs. Linked from `web/index.html` and `web/command-deck.html`'s "Bridge Instruments" section.
- `web/toys/radio-console/` — copied from `toys/radio-console/`. Its Newswire panel additionally depends on `web/data/npr-headlines.json` being kept fresh — see "NPR Newswire Feed" below; that file is not part of the toy copy itself and is not touched by a plain re-deploy.

### NPR Newswire Feed

Radio Console's Newswire panel reads `web/data/npr-headlines.json`, written by `tools/npr-headlines/fetch.py` from NPR's public "NPR Topics: News" RSS feed (`https://feeds.npr.org/1001/rss.xml`). Deliberately kept out of the transmission-scoring/speech pipeline the rest of the console uses (see the comment at `NEWSWIRE_URL` in `toys/radio-console/app.js`) so real-world news is never spoken in the same voice/urgency system as a fleet watch event.

This is the first real *external* (non-FleetCore) source the console carries — see NPR's terms of use before changing what the fetcher writes: headlines/links/other feed content may be displayed on a personal/noncommercial site with attribution and without modification, but NPR audio files may not be redistributed. The fetcher writes title/link/pubDate only, no audio, no full article text, and the panel renders the required "NPR News Headlines" attribution next to the content, not just in alt text.

NPR's feed only grants CORS to `apps.npr.org`, so the browser can't fetch it directly from `cameronlampley.com` — `tools/npr-headlines/fetch.py` is the server-side hop that avoids that, same-origin JSON on the other side.

**Current fetch schedule is a temporary bridge, not the final mechanism**: a user crontab entry (`crontab -l`, no sudo — added directly since this doesn't require privileged access) runs the fetch every 15 minutes. The proper systemd timer (`scripts/npr-headlines-fetch.service` / `.timer`, matching every other scheduled job in this repo, e.g. `living-fleet-memory-reflect.timer`) is written and ready but not yet installed — that's a privileged step (see `scripts/install-npr-headlines.sh`, which also removes the temporary cron entry once the timer takes over). Until someone with sudo runs that install script, the cron entry is what's actually keeping the feed live — check `crontab -l` before assuming the timer is what's running.

### Watchbook is intentionally not public

Watchbook (`toys/watchbook/`) reads the actual `logs/` tree via relative fetches (`../../logs/captains/...`). Deploying it as-is would publish the full captain/admiral watch log history — including internal ops/infra logs — to the public site. That has not been done. The public site's own Ship's Log page (`web/logs.html` / `web/assets/js/logs.js`) is the intentional, separate public-facing equivalent, and is what Bridge Station's Watchbook tab links out to instead of embedding Watchbook.

`web/bridge.html` (a separate, older, hand-built public "Bridge" page, distinct from `toys/bridge/`) was retired 2026-07-16 (`BRIDGE-RETIRE-01`, `docs/architecture/component-consolidation-master-plan-v0.1.md`): its data source, `web/bridge-state.json`, had gone stale (last written a week prior, pre-dating FleetCore's live WebSocket feed) and was silently showing frozen fleet state with no indication it wasn't live. `toys/bridge/` itself was retired the same day (`BRIDGE3-CONSOLIDATE-01`, see below) — every "Bridge" link across the site (`index.html`, `command-deck.html`, `logs.html`, `fleet.html`) now points straight to `toys/bridge-station-3.0/`.

## Site Root Is the Front Door — Links to Every Toy

`web/index.html` was briefly a redirect straight into `toys/bridge/` (see git history if that behavior is ever wanted back; `toys/bridge/` itself is since retired). It's the homepage again: mission/doctrine/fleet roster/Ship's Log content, plus sectioned card grids linking every deployed public toy — Radio Console, Bridge Station 3.0, Fleet Motion, Periscope Station, Reaction-Diffusion Painter, and the rest. `web/command-deck.html` is kept as an identical mirror (same content, distinct `<title>`) so the old URL still works — **update both together**, `web/index.html` is not the single source of truth here. Add a new card to both whenever a new toy gets deployed publicly.

## FleetCore Live Backend

`web/toys/bridge-station-3.0/` (the sole remaining "look at or command FleetCore" toy — see `BRIDGE3-CONSOLIDATE-01` above) is a thin client with no simulation of its own — it needs a real `fleetcore-serve` process running and reachable, unlike most other public artifacts in this repo, which are fully self-contained static pages.

Living Fleet adds `living-fleet.service`, one shared Python captain runtime with
no listening port. It talks only to FleetCore on `127.0.0.1:4771`; do not add a
proxy route for it. Install or restart both real services with the scripted
rollout:

```sh
scripts/install-living-fleet.sh
```

The installer builds both the `serve` process and the `fleetcore` operations
CLI so replay tooling stays on the same command schema as production. FleetCore
retains the newest 120 recovery checkpoints plus genesis; the append-only event
log remains the durable history.

**Running the process.** `fleetcore-serve` binds `127.0.0.1` only by default (see the comment on `DEFAULT_BIND_HOST` in `fleetcore/src/bin/serve.rs`). Its write path (`POST /command`, and any command sent over `/ws`) has no auth at all: every connection on both transports has full command authority, no token required — `--command-token` is still accepted on the command line but silently ignored (see the doc comment at the top of `fleetcore/src/bin/serve.rs`, which is authoritative over `docs/architecture/fleetcore-api.md`'s "Command Authority" section describing the originally-designed gate). Run it via the systemd unit at `scripts/fleetcore-serve.service` rather than an ad hoc background process, so it survives reboots and restarts on crash:

```sh
cargo build --release --manifest-path fleetcore/Cargo.toml --bins
sudo cp scripts/fleetcore-serve.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fleetcore-serve
sudo systemctl status fleetcore-serve
```

As of 2026-07-13, `scripts/fleetcore-serve.service`'s `ExecStart` already ships with `--bind-all --command-token bridge-3-0-lan` — command authority and LAN reachability are both on by default when this unit is installed, matching what's actually been live on this box, not the more conservative loopback-only/read-only configuration it originally shipped with.

As of 2026-07-13, `web-lan/` and its `monad-lan-web.service` unit have been retired — `web/` (served at `https://cameronlampley.com/`) is the single deploy target now. There is no longer a separate LAN-only mirror; the constraint that originally motivated one (Caddy's root wasn't LAN-scoped, and `fleetcore-serve` was loopback-only) was resolved once the public hatch was finished end-to-end (see `docs/deployment/public-hatch.md`), making the second deploy target redundant.

`bridge-3-0-lan` is moot in practice: `fleetcore-serve` currently grants command authority to every connection unconditionally regardless of what token (if any) is presented (see "Known limitation" below), and none of this repo's toy UIs can even present a token anymore — the Command Token field/param that used to exist in `toys/fleet-motion/` and `toys/bridge-station-3.0/` (plus the now-retired `toys/fleetcore-live/`, `toys/fleetcore-control/`, and `toys/bridge/`) was removed everywhere once that became clear. **The token itself was never a real secret regardless**: it's committed in plaintext across this repo's own git history (watch logs, this file, past commit messages), and the public `/fleetcore-ws/` reverse proxy was finished without rotating it first — see the Bridge Station 2.1/3.0 section below for the full history. If you ever want real command-authority isolation, the server needs actual per-client auth (not just a shared token), and every client above would need a way to present credentials reintroduced.

**Exposing it publicly.** A `handle_path` block in `/etc/caddy/Caddyfile` proxies the public path to the loopback-only server:

```caddyfile
handle_path /fleetcore-ws/* {
    reverse_proxy http://localhost:4771
}
```

This lives inside the same `cameronlampley.com { ... }` block as the bare-root `file_server` and `/monad/portainer/*` config, not as a separate site block. `handle_path` strips the matched prefix before proxying, so a public request to `/fleetcore-ws/ws` reaches `fleetcore-serve`'s own `/ws` route, and `/fleetcore-ws/snapshot` reaches `/snapshot`. After editing:

```sh
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

**Resolved as of 2026-07-13:** rock64 has been removed from the path entirely — see `docs/deployment/public-hatch.md`. The router forwards ports 80/443 directly to Granite, and Granite's own Caddy terminates TLS (automatic HTTPS via Let's Encrypt) and serves the site directly at the bare root. WebSocket upgrades through the full `wss://cameronlampley.com/fleetcore-ws/ws` path are confirmed working end to end (verified with a real HTTP/1.1 upgrade handshake, `101` response). `http://localhost/fleetcore-ws/snapshot` on Granite itself is still the right first check to isolate Caddy/`fleetcore-serve` from anything upstream, but there is no longer a separate rock64 hop to account for.

**`/monad/` was retired the same day** (see `docs/deployment/public-hatch.md`'s "History" section) — the static-content and `fleetcore-ws` paths moved to the bare root; only `/monad/portainer/*` stays, deliberately, since it's operator infrastructure under separate standing protection ("the Portainer reverse proxy path must not be disturbed"), not part of the app.

**Known limitation, accepted for now:** as of 2026-07-12 there is no command-token gate at all — `fleetcore-serve` grants full command authority to every connection on both `/command` and `/ws` unconditionally (`fleetcore/src/bin/serve.rs`), explicit user request. The live world is shared by every visitor with no per-visitor isolation: anyone who can reach the server (which, through the public reverse proxy, means anyone on the internet) can pause/resume, reset the fleet, despawn vessels, or set any vessel's route. This was an explicit, informed choice, not an oversight; add real auth before treating this as anything more than a single-operator demo.

**Standing policy: security hardening is not the priority for this project.** This is a single-operator demo, and the above is a known, accepted tradeoff, not an open question to keep re-flagging. Don't gate a feature's completion on adding auth, a token gate, or other hardening here — the priority is that things run and are reachable per the URL/port policy at the top of this file. The one thing still worth a flag is anything that would expose this machine's own real secrets (credentials, private keys, tokens for other systems) — that's a different category from "the demo world itself has no login."

## Bridge Station — `toys/bridge-station-3.0/`, Public

As of 2026-07-13, Bridge Station 3.0 (real FleetCore data, Vite + React) is the only
surviving generation of the Bridge Station lineage. `toys/bridge-2/` (2.0) and
`toys/bridge-station-2.1/` (mock-data 2.1) have been removed from the repo and their
ad hoc dev-server processes killed — superseded, not needed.

**2026-07-16 (`BRIDGE3-CONSOLIDATE-01`): the four toys that overlapped on "look
at or command FleetCore" are now one.** `toys/bridge/` (the original "Live
Console" — iframe-composited Fleet Motion/Periscope/Radio Console),
`toys/fleetcore-live/` (raw Leaflet-map feed viewer), and
`toys/fleetcore-control/` (spawn/despawn/scenario/Harbor Pilot Boarding
console) are retired — `git rm`'d from both `toys/` and `web/toys/`, not
archived. Bridge Station 3.0 absorbed their capability as three additional
tabs alongside its existing default view (now labeled "Bridge"):

- **Control** — spawn/despawn forms, pause/resume + time scale, reset fleet,
  the three quick scenarios (distress call, storm convoy, collision course),
  and the full Harbor Pilot Boarding phase state machine, ported from
  `fleetcore-control/app.js`'s `HARBOR_STEPS`.
- **Radio** — the same `<iframe src="../radio-console/">` embed old Bridge
  used; Radio Console's own `is-embedded` styling still auto-detects it.
- **Raw Feed** — a table/list readout of the same snapshot fields FleetCore
  Live's Leaflet map showed (tick, sim time, clock state, time scale, command
  authority, vessel table, watch events, vessel events) — table form instead
  of a map, so no new map-library dependency was needed.

All three tabs reuse the same open WebSocket connection Bridge Station 3.0
already holds for its default view, rather than opening a second connection
per tab. Verified live via Playwright against the real deployed page before
the old toys were removed: all four tabs render with zero console errors, a
real Distress Call command round-tripped (spawned vessel and matching watch
event both appeared), and the Radio tab's iframe loads. `web/index.html` and
`web/command-deck.html`'s "Bridge Station"/"FleetCore Live"/"FleetCore
Control Center" cards are gone; every "Bridge" link across the site now
points to `toys/bridge-station-3.0/` directly.

Bridge Station 3.0 is deployed the same way as every other public toy: `npm run
build` in `toys/bridge-station-3.0/`, then the `dist/` output copied into
`web/toys/bridge-station-3.0/` — no separate port, no ad hoc process, served straight
through Caddy like the rest of `web/`. Two things this build needed that other,
non-bundled toys don't:

- `vite.config.js` sets `base: './'` so the built `index.html`/asset references are
  relative, not absolute — required because this is served from a subpath
  (`/toys/bridge-station-3.0/`, not domain root).
- `src/App.jsx`'s `serverUrl()` now defaults to
  `wss://cameronlampley.com/fleetcore-ws/ws` instead of deriving
  `ws://<page-hostname>:4771/ws` — the latter would have tried to reach port 4771
  directly on `cameronlampley.com` (not open, and blocked as mixed content on an
  `https://` page regardless).

**Command authority:** `fleetcore-serve` still runs with `--command-token bridge-3-0-lan`
(see the "FleetCore Live Backend" section above), but as of this writing it grants
command authority to every connection unconditionally regardless of what token (if
any) is presented — so the client-side token that used to be baked into Bridge
Station 3.0's bundle (`COMMAND_TOKEN` in `src/App.jsx`) was pure theater and has
been removed, along with the equivalent Command Token field/param in every other
toy (`fleetcore-control`, `fleetcore-live`, `bridge`, `fleet-motion`'s
`?commandToken=` passthrough). None of these toys can present a token anymore;
whatever the server grants a connection is what that connection gets. If real
per-client auth is ever added server-side, these clients will need a token
mechanism reintroduced.

## Living World Intake — `toys/world-intake/`, Public

Captain review desk for the intake pipeline (`ingest → extract → review →
compile → commit`) that turns adjudicated narrative assertions into real
FleetCore canon changes. Deployed the same shape as Captain Memory/Agent
Operations: a loopback-only Python backend behind a Caddy `handle_path`
proxy, plus a static `web/` copy of the review UI.

**Backend.** `world-intake.service` (`scripts/world-intake.service`) runs
`tools/world-intake/world_intake.py ... serve`, a single-threaded stdlib
`http.server` bound to loopback, `Requires=fleetcore-serve.service`. It
owns its own SQLite store at `data/world-intake.sqlite3` and talks to
FleetCore's real command endpoint (`http://127.0.0.1:4771/command`) to
submit adjudicated proposals as `apply-canon-change` commands — this is
the one seam that has to match FleetCore's real schema exactly
(`CanonChange` enum + full 6-field `CanonProvenance`), which
`world_intake.py`'s `compile()` builds directly rather than through a
separate mapping layer.

Install/restart via `scripts/install-world-intake.sh`, same
build-and-enable pattern as the other services in this file.

**Public route.** `handle_path /world-intake-api/* { reverse_proxy
127.0.0.1:4773 }` in `/etc/caddy/Caddyfile`, alongside the other
`handle_path` blocks in the same `cameronlampley.com { ... }` block. The
static UI lives at `web/toys/world-intake/` (copied from
`toys/world-intake/`, no build step) and is linked from the homepage
card grid. Verified live as of 2026-07-14:
`https://cameronlampley.com/toys/world-intake/` returns 200, and
`https://cameronlampley.com/world-intake-api/proposals` returns real
queue data through the proxy (not the UI's demo-mode fallback).

**Command authority:** same standing tradeoff as FleetCore itself — no
per-visitor auth on the review/adjudication actions. See "Known
limitation, accepted for now" above; the same acceptance applies here,
not a new gap.

## Living Captain — `toys/living-captain/`, Public

Read-only status view over `tools/living-captain/`: one persistent
identity (`captain.monad`), sight into real FleetCore/World Intake state,
a custody-gated read boundary, a spend-limited observe budget, and an
append-only action record. See
`docs/engineering-orders/living-captain-v0.1.md` and `-v0.2.md` for the
design. **No canon-mutating write authority exists anywhere in this
system** — every canon change still goes through FleetCore's own
authenticated command path, same as World Intake.

**Backend.** `living-captain-status.service`
(`scripts/living-captain-status.service`) runs
`tools/living-captain/status_server.py`, a single-threaded stdlib
`http.server` bound to loopback (`127.0.0.1:4774`). It only reads
`data/living-captain/state.json` and `actions.jsonl` — it never
assembles a `LivingCaptain` instance and never calls `observe()`, so
running it costs no spend budget and has no dependency on
`fleetcore-serve` or `world-intake` being up. The Captain identity
itself is only ever advanced by an operator-invoked run (currently
`tools/living-captain/demo_all.py`, or a direct `LivingCaptain.assemble()`
call) — there is no scheduler or unattended loop yet.

Install/restart via `scripts/install-living-captain.sh`, same
build-and-enable pattern as the other services in this file.

**Public route.** `handle_path /living-captain-api/* { reverse_proxy
127.0.0.1:4774 }` in `/etc/caddy/Caddyfile`, alongside the other
`handle_path` blocks in the same `cameronlampley.com { ... }` block. The
static UI lives at `web/toys/living-captain/` (copied from
`toys/living-captain/`, no build step) and is linked from the homepage
card grid.

**Command authority:** none exists to have a tradeoff about. The status
API is GET-only and read-only by construction; the Captain's own
outbound reads are custody-gated to exactly two URLs
(`tools/living-captain/sight.py`'s manifest).
