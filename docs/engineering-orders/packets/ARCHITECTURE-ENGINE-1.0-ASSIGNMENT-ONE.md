# Architecture Engine 1.0 — Assignment One: System Inventory

- **Date:** 2026-07-16
- **Ordered by:** The Captain, Architecture Engine 1.0 Tech Lead Action Packet, Assignment One
- **Prepared by:** Claude, acting as Tech Lead
- **Method:** every line below is a directly observed fact (`ps`, `ss`, `systemctl`,
  `curl`, `diff`, `git`) captured this session, not inferred from source code
  existing. Where I could not verify something live, it is marked `Unknown`
  rather than assumed.

## Running services (systemd-managed, verified `active (running)`)

| Service | Binds | Verified via |
|---|---|---|
| `fleetcore-serve.service` | `0.0.0.0:4771` (ws + http) | `systemctl status`, live WS snapshot pulled this session |
| `world-intake.service` | `127.0.0.1:4773` | `systemctl status`, process listing |
| `living-fleet.service` (`captain_runtime.py`) | no listener (client role) | `ps aux`, PID 24664 |
| `living-fleet-memory.service` (`inspector_server.py`) | `127.0.0.1:4772` | `ps aux` + `ss`, PID 28596 |
| `living-captain-status.service` | `127.0.0.1:4774` | `ps aux` + `ss`, PID 166881 |
| `monad-watchman.service` | no listener (heartbeat/logger) | `ps aux`, PID 28722 |
| `caddy` (system-level, not a Monad unit) | `:80`, `:443`, loopback `:2019` admin | `ps aux`, reverse-proxies all of the above per `scripts/Caddyfile` |

**Scheduled job**, verified `inactive dead` (correct — oneshot, timer-triggered):
`living-fleet-memory-reflect.service`, activated by `living-fleet-memory-reflect.timer`
(next fire confirmed via `systemctl list-timers`).

**Finding — undocumented scheduling mechanism.** `scripts/npr-headlines-fetch.service`
and `scripts/npr-headlines-fetch.timer` exist in the repo, but neither unit is
installed (`systemctl status npr-headlines-fetch.timer` → "could not be found").
The NPR fetch that's actually running live is a **plain crontab entry**
(`*/15 * * * * .../tools/npr-headlines/fetch.py`), not the systemd path the
repo documents. Two competing installation methods exist for the same job;
only one is real. Recommend: either install the documented systemd timer and
remove the crontab entry, or delete the unused unit files and document cron
as the real mechanism — currently both exist and only one is true.

## Network-facing components

| Port | Bind | Owner | Status |
|---|---|---|---|
| 4771 | `0.0.0.0` (all interfaces) | fleetcore-serve | Running. **No command-token auth** — confirmed directly from its own startup log: `"command authority is GRANTED to every connection -- no token required"`. Already tracked as open issue #16 / Feature Matrix WT-02; not a new finding, but now directly re-confirmed from the live log rather than from code reading. |
| 4772 / 4773 / 4774 | `127.0.0.1` only | memory inspector / world-intake / living-captain-status | Running, loopback-only, reached publicly only via Caddy's `/captain-memory-api/`, `/world-intake-api/`, `/living-captain-api/` paths |
| 6333 / 6334 | `0.0.0.0` | Qdrant | Running — one collection present, `monad_core_memory` (confirmed via its own REST API) |
| 9443 | loopback via Caddy `handle_path /monad/portainer/*` | Portainer | Standing-protected infrastructure per `CLAUDE.md` — **not touched, not further inspected**, per the explicit standing order |
| 8000 | `0.0.0.0` | **Unknown** | Responds `404` to a bare GET. Not referenced in `Caddyfile`, not matched to any Monad service by name or by process owner visible without elevated permissions. Flagging as `Unknown` rather than guessing — needs an owner identified, not assumed safe. |
| 22, 53, 80, 443 | — | sshd, systemd-resolved, Caddy | Standard host services, out of Monad's scope |

## Persistent data stores

| Store | Size (this session) | Authoritative for |
|---|---|---|
| `data/fleetcore/world.json` + `data/fleetcore/events.jsonl` + `data/fleetcore/checkpoints/` | 13M / 47M / (checkpoint dir present) | FleetCore world state — append-only event log is the durable source, `world.json` is a materialized snapshot (per `fleetcore/src/persistence.rs`, verified in the earlier Feature Matrix pass) |
| `data/living-fleet/memory.db` (SQLite, WAL mode) | 23M | Living Fleet captain memory (episodic/semantic/procedural/relational/narrative) |
| `data/world-intake.sqlite3` | 120K | World Intake's sources/assertions/adjudications/commands pipeline |
| Qdrant `monad_core_memory` collection | — | Referenced by docs as broader-system memory; **not** the source of truth for `tools/living-fleet/memory/` per this session's PR review (that package's own retrieval path is local TF-IDF, not Qdrant-backed) |

## Experimental vs. maintained vs. deprecated (source tree)

- **`archive/legacy-prototypes/`, `archive/sprints/`** — already explicitly archived (moved, not deleted) by a prior session (`git log`: "Archive legacy prototypes and sprint briefs"). Correctly labeled by location, not by comment.
- **`toys/periscope/mk2/`, `mk3/`, `mk4/`** — three historical iteration directories still present alongside the live `toys/periscope/`. Not marked experimental/deprecated in-repo; a newcomer can't tell from the directory listing alone which is current. Recommend an explicit marker or archival, per the Architecture Engine's own "EXPERIMENTAL — NOT ARCHITECTURE OF RECORD" convention.
- **`.claude/worktrees/scout-screen-mode`** (locked worktree, branch `worktree-scout-screen-mode`) — still present. This is the same item as `HUMAN-03` / `WT-03` in the existing queue and Feature Matrix (access-blocked, not independently re-verified this session).
- **Stale remote branches** (`codex/issue-16-slice-g-auth`, `codex/issue-17-slice-a`, `codex/issue-18-slice-b`, `codex/history-v2-integration`, `agent/issue-18-slice-b`, `agent/periscope-glsl3-upgrade`, `agent/memory-api-latency`, `agent/living-captain-sight`, `agent/archive-legacy-files`) — all last-committed 2026-07-13/14, none merged into `main`. This matches `WT-01`/`WT-02` in the Feature Matrix (already classified there); re-confirmed present via `git branch -a`, not re-classified here.

## Finding — deployed-vs-source drift (`toys/<name>/` vs `web/toys/<name>/`)

Checked every toy directory with a byte-level diff, not by assumption. Result:

- **Genuinely in sync:** `agent-ops`, `living-captain`, `shared`, `world-intake`.
- **Differences that are correct and intentional** (confirmed by reading the actual diff, not just its existence): `fleetcore-live/index.html` and `fleetcore-control/index.html` differ only in a dev-default `ws://localhost:4771/ws` (source) vs. the real production `wss://cameronlampley.com/fleetcore-ws/ws` (deployed) — expected. `periscope/duck.js` differs by a self-documenting comment explaining a deploy-relative-path correction. `bridge`, `fleet-motion`, `reaction-diffusion-painter` differ only by extra README/notes files present in `toys/` and absent from `web/toys/` — expected, docs aren't meant to ship.
- **Real, undocumented drift — nothing explains why these differ:**
  - **`web/toys/radio-console/app.js`** vs **`toys/radio-console/app.js`**: the deployed copy has ~340 lines of live content-narration logic (FleetCore vessel/canon-event narration, baseline watch reporting) that the source copy entirely lacks. Already flagged in this session's PR #26 review.
  - **`web/toys/asset-viewer/{app.js,index.html,style.css}`** vs **`toys/asset-viewer/`**: the deployed copy has the entire drag-and-drop upload UI (progress bar, staged-file preview, drop zone) that the source copy lacks entirely.
  - **`web/toys/cognition-graph/`** (shipped this session) has **no `toys/cognition-graph/` source counterpart at all** — I wrote it directly to `web/`, which is the same pattern this finding is flagging in the other two toys. Noting this against myself rather than omitting it: it should get a `toys/` source copy to match the project's own convention, exactly like the other two gaps above.

This isn't three unrelated one-offs — it's the same failure mode three times: the deploy target (`web/toys/`) accumulating real logic that never makes it back to what the project treats as the editable source (`toys/`). Worth a standing check rather than three individual fixes.

## Not yet inventoried (honest gaps in this pass)

- Process ownership of port 8000 (needs elevated permissions I didn't use this session).
- Full `git log --all` sweep for dangling/unreferenced commits beyond named branches.
- Disk-level check for caches (browser-side `localStorage` usage — e.g. the Cognition Graph's own bring-your-own-key storage — is by design invisible to server-side inventory).
