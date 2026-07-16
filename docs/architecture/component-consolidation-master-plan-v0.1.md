# Component Consolidation Master Plan V0.1

Status: living plan, tracks real progress. Every item below is grounded in a
direct check performed this session (grep, live curl/WebSocket, file
timestamps, test runs) — nothing here is inferred from a component's name or
description alone, per the Architecture Engine's own standing rule.

Objective, as given: **increase integration, keep good features, get rid of
junk.** Not "fewer files" for its own sake — every item either removes
something that provides zero remaining value, fixes something that's
silently drifted from its own documented intent, or gives an isolated,
working component a real job instead of deleting working code.

## Phase 0 — Done this session

| Item | What happened | Evidence |
|---|---|---|
| NPR fetch scripts | `tools/npr-headlines/fetch.py` and `tools/npr-podcasts/fetch.py` duplicated identical `urllib.request`/User-Agent boilerplate. Consolidated into `tools/npr-fetch/fetch.py`; both original paths kept as thin wrappers (`tools/npr-headlines/fetch.py` has a **live 15-minute crontab entry** pointing at that exact path — confirmed via `crontab -l` — so the path can't be removed without a crontab edit, which this project routes through the Lieutenant, not an agent session). | Verified byte-identical output across all entry points before committing. Commit `0f31e6a`. |
| GitHub issue #6 | "Bound unbounded FleetCore vessel event history" was already fixed in code (`vessel_event_retention`, default 2000) but never closed. | Re-confirmed live via direct WebSocket check moments before closing: `vessel_event_retention: 2000`, `vessel_events.length: 2000`. Closed with that evidence attached. |
| `engineering-comms` | A real, tested (17/17) message validator/router used by **nothing** anywhere in the repo — confirmed by grep across every `tools/`/`toys/` file. Wired into Mission Bus's `review()` as an independent validation + audit layer, closing a real gap (review()'s own signature never enforced non-empty `reason`). | 9/9 Mission Bus tests pass (including a new one proving both the fail-closed path and the real audit trail). Found and fixed a genuine `importlib`+`@dataclass` bug along the way. Commit `6afab05`. |
| MISSIONBUS-01 | Mission Bus was hardcoded to one mission (`MID`/`CID` module constants). Generalized to a parameterized `Record`, unblocking every future component adapter. | New test proves a second, independently-IDed mission runs its full lifecycle with zero event-ID collision; all 4 original tests pass unmodified. Commit `47b359b`. |

## Phase 1 — Confirmed, not yet executed (small, safe)

| Item | Finding | Recommended action |
|---|---|---|
| `web/bridge.html` | Reads `web/bridge-state.json`, **last written July 9** — a week stale as of this writing (July 16). Pre-dates FleetCore's live WebSocket feed; a hand-built artifact from before live streaming existed. Anyone who clicks the "Bridge" footer link sees frozen data with no indication it's not live. | **Retire.** `toys/bridge/` ("Bridge Station") and `toys/bridge-station-3.0/` already cover this need with genuinely live data. Zero feature loss. |
| `command-deck.html` | Initially looked like a dead duplicate of `index.html` (same links minus 3 newer ones) — but `docs/deployment.md` is explicit it's a **deliberate mirror kept for old bookmarked URLs**: *"update both together... `index.html` is not the single source of truth here."* It's drifted, not orphaned. | **Resync**, don't delete — add the 3 missing links (`ops.html`, Cognition Graph, Living Captain) to match `index.html` exactly, restoring the documented invariant. |
| Watchman | `watchman.py` implements 2 of the 8 checks its own name/role implies (disk, Qdrant health, plus git commit/uptime as extras). No process monitoring, no coverage of the other 5 live services (`fleetcore-serve`, `world-intake`, `living-fleet-memory`, `living-captain-status`, `living-fleet`), no stale-service/failed-restart detection. | **Flesh out**, in progress — genuinely useful, currently under-scoped relative to its own claimed role. Not a purge candidate. |
| `toys/periscope/mk2`/`mk3`/`mk4` | Turned out to be documentation-only folders (`ENGINEERING_REPORT.md` etc.), not duplicate code. Misplaced, not weak. | Low priority: move under `docs/reports/` or `docs/architecture/` where the project's own convention says evidence/reports live, out of the toy's own source folder. |

## Phase 2 — The real consolidation target (larger, staged)

Four toys all do "look at or command FleetCore," with genuine, confirmed overlap:

| Toy | Role | What it uniquely provides |
|---|---|---|
| `toys/bridge/` ("Bridge Station") | Thin iframe shell — literally just 3 `<iframe>` tags embedding Fleet Motion, Periscope, and Radio Console, read-only, plus a shared browser-local selection state (`toys/shared/fleet-state.js`) | The compositing/aggregation view |
| `toys/bridge-station-3.0/` | Real ~545-line React app, actual command authority (Set Waypoint) | Real command capability |
| `toys/fleetcore-live/` | Raw WebSocket feed viewer, read-only/debug | Nothing Bridge Station 3.0 doesn't already consume internally |
| `toys/fleetcore-control/` | Scenario launcher — spawn/route/despawn/Harbor Pilot Boarding | A command surface broader than Bridge Station 3.0's current Set-Waypoint-only scope |

**Proposed end state:** Bridge Station 3.0 becomes the one FleetCore command-and-control instrument. Staged, not a single risky swap:

1. Add the same embedded-panel tabs old Bridge already has (Fleet Motion + Periscope + Radio Console) — the iframe technique already works today, and Radio Console already ships an `is-embedded` CSS mode built for exactly this kind of embedding.
2. Fold FleetCore Control's spawn/despawn/Harbor-Pilot-Boarding commands in as an additional control panel.
3. Add a raw-feed debug tab covering what FleetCore Live shows (Bridge Station 3.0 already reads this same feed internally — this is exposing existing internal data, not a new integration).
4. Verify each addition live against the real deployed page before touching what it replaces.
5. Only once all three are verified equivalent: retire `toys/bridge/`, `toys/fleetcore-live/`, `toys/fleetcore-control/`.

Net: **4 toys → 1**, no feature dropped, one authoritative "Bridge" instead of three-plus things partially claiming that name. Not started — this is real React work against a build-step toy, staged deliberately so nothing gets retired before its replacement is verified equivalent.

## Phase 3 — Named but not scoped (design exists, no code)

**World Intake's adjudication flow + Mission Bus's `review()`** are the same conceptual pattern (a human must explicitly approve/reject/edit before something becomes accepted) implemented twice. `GLUE-05` (`docs/architecture/human-review-inbox-v0.1.md`) already designed the generalization — a shared review-card contract both would consume — specifically to prevent this. Not built yet. Bigger than Phase 1, more architecturally significant than Phase 2's UI merge; worth its own decision rather than folding into either phase above.

## What's explicitly *not* on this list

- Anything the Feature Matrix already marked "Required Next" / "Design Required" for features that don't exist yet (Watch Officer, cost tracking, per-agent registry). Nothing to purge if it was never built — that's a build decision, not a consolidation one.
- `archive/legacy-prototypes/` and `archive/sprints/` — already correctly retired (moved, not deleted) by a prior session. Doing their job.
- Anything currently claimed/in-progress by Codex (checked via `git log` and the shared queue before each item above was started, to avoid collision).

## Sequencing recommendation

Phase 1's three items are small, independently gated, and safe to do in any order (or all at once) without waiting on anything else. Phase 2 is the real prize but is genuinely staged, multi-session work against a build-step React app — start it deliberately, not as a side effect of something else. Phase 3 needs a decision (is this worth doing now, or later) before any code gets written, same as GLUE-05's other dependents.
