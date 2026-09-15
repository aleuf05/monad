# Captain Interface Reconnaissance

**Date:** 2026-09-15  
**Scope:** existing web interfaces for an everyday Windows/Android Captain
interface with Monad-controlled history  
**Method:** read-only source inspection, live HTTP probes, service/process
inspection, and read-only SQLite inspection. No messages were sent, no live
turn was started, and no service was restarted.

## Evidence labels

- **Verified now:** observed on this host or over the live URL during this
  audit.
- **Source evidence:** present in the inspected source; not necessarily
  exercised during this audit.
- **Historical report:** dated evidence, useful context but not current proof.
- **Claimed by source:** documentation assertion not independently verified.

## 1. Candidate comparison

| Candidate | Source / URL / status | Real backend and execution | History, tools, restart behavior | Windows / Android assessment | Disposition |
|---|---|---|---|---|---|
| **Root Console + Live Captain bootstrap** | Source: `console/`, `tools/root-console/`, `tools/live-captain/`. URL: `https://cameronlampley.com/root/`. Verified now: `root-console.service` and `live-captain-bootstrap.service` are active; unauthenticated page redirects to `/root-login`; protected APIs return `401`. | Source evidence: browser `EventSource` → `/live-captain-bootstrap-api/api/stream`; submit → `POST /live-captain-bootstrap-api/api/turn`; server compiles kernel, bearing, ledger, and recent messages, records the Admiral message, calls `daemon.send_and_wait()`, records the Captain reply, then returns it. `codex_daemon.py` starts `codex app-server`, sends `thread/start` and `turn/start`, and exposes real item/tool/thread events. Backend dispatch defaults to AGY and supports Claude/Codex. | Source evidence: SQLite `data/live-captain/live-captain.db`, append-only `messages` plus `restarts`, objectives, concept rooms/turns, and evidence. Recent context is bounded to 12 messages for inference, with omitted count reported; full message rows remain durable. Verified now: 691 messages, 40 restart markers, and current tail present in the DB. Page reload reopens the authenticated stream; server restart reconstructs from DB. Tool results are streamed by the app-server event path and not fully rehydrated into the transcript UI after reload; the durable main transcript is. | Source evidence: responsive CSS switches to a stacked terminal/status layout below 760px; controls include keyboard submit, long-command textarea, visible presence states, progress spinners, activity/tool/reasoning/thread/MCP widgets, and explicit failure text. Readable but dense on a phone; the status rail competes with the conversation and long histories are not presented as a selectable history list. Cross-device behavior is architecturally plausible through HTTPS cookie + server DB, but not verified with two devices in this audit. | **Strongest candidate. Improve this.** It is the only existing surface with real Captain execution, live progress, auth, and a durable shared store. |
| **Living Captain Private Conference** | Source: `tools/living-captain/web_service.py`, `live_captain_engine.py`, `conversation.py`. URL/API: `https://cameronlampley.com/live-captain-chat-api/` (Caddy path); local health `http://127.0.0.1:4776/health`. Verified now: `live-captain-web.service` active; local health returned `200 {"ok":true,"service":"live-captain-conference"}`. | Source evidence: `POST /messages` calls `CaptainEngine.reply()`; the engine appends user text, builds bounded provider context, calls the configured provider, then appends the assistant reply. This is a real Gemini/provider path, not the current Codex/AGY execution path. | Source evidence: append-only `data/living-captain/conversation.jsonl` plus stable `conversation-state.json`, usage ledger, action log, and an owner lock. Verified now: transcript/state files exist; `conversation.db` is empty and not the active store. Restart/reload survives because the JSONL/state files are read by the engine. Tool execution is explicitly absent in Version 1. | No native browser UI was found for this conference path; it is an authenticated HTTP API plus terminal client. Therefore it cannot be the everyday Windows/Android interface without adding a frontend. | **Useful reference seam, not the selected UI.** Reuse its secure cookie, append/fsync discipline, and single-owner lessons where compatible. |
| **Captain Habitat** | Source: `tools/live-captain/habitat_server.py`, `habitat_store.py`, `job_engine.py`. Intended local port 4777 and Caddy path `/captain-api/*`. Verified now: `live-captain-habitat.service` is inactive/dead; no listener on 4777; no shipped browser UI found. | Source evidence: `/chat` is SSE; it stores an Admiral message, compiles the full system prompt, runs Gemini or a deterministic fallback, executes parsed tools, stores Captain `tool_events`, and emits a `done` event. It supports thread creation/list/get and job endpoints. | Source evidence: SQLite `data/live-captain/habitat.db` has `threads` and `messages` with `attachments_json` and `tool_events_json`; verified now: 27 threads and 56 messages. This is the best existing schema for explicit resumable threads and tool-result replay, but its execution process is not running now. | No UI to assess. API has permissive `Access-Control-Allow-Origin: *` and unauthenticated write endpoints in source, which is unsuitable for direct internet exposure. | **Do not select as-is.** Reuse its thread/tool-result data model only if the security and runtime path are deliberately repaired. |
| **Chat Captain (legacy)** | Source: `tools/chat-captain/` and its old frontend logic `console/assets/js/chat-captain.js`. Historical URL: LAN `http://192.168.0.100:8080/`; public legacy path `https://cameronlampley.com/chat-captain-api/`. Verified now: public API returns `410 {"error":"legacy_chat_captain_parked"}`. | Source evidence: real `POST /api/chat` through `CaptainEngine` and the Codex-backed provider, with project/mode/session operations. Historical/current deployment config deliberately parks this route. | Source evidence: SQLite schema includes `captain_state`, projects, sessions, messages, image jobs, harvest items, and mode events. It has durable history and image job records, but its frontend/API path is retired. | Historical frontend was readable and had transcript reload, mode/project controls, harvest review, image polling, and visible errors. It is not available at its documented public route now. | **Reject as implementation target.** Preserve as historical reference only. |
| **Public Living Captain status instrument** | Source: `web/toys/living-captain/`, `tools/living-captain/status_server.py`. URL: `https://cameronlampley.com/toys/living-captain/`; API `/living-captain-api/`. | Verified/source evidence: read-only status projection; it does not send Captain turns or execute tools. | Reads state/actions projections only; no conversation UI or resume loop. | Public, likely responsive status view, but not a conversation interface. | **Not a candidate.** |

## 2. Strongest candidate

The Root Console is the clear choice: `console/index.html` is already an
operator-facing web application, `/root/` is a single authenticated URL, and
the current two-service split preserves the important boundary between the
browser conversation and Root Console-owned authentication/handoffs/images.
It reaches a real execution backend and records the conversation in the
Monad-controlled SQLite store rather than depending on provider thread
continuity.

The principal weakness is not execution. It is continuity presentation:
reload and restart rebuild the model context from durable rows, but the UI
does not expose a first-class, navigable history/thread list, and raw tool
event history is primarily a live stream rather than a durable replay view.

## 3. Smallest repairs for the requested complete loop

Target loop: **Windows start → Android continue → Windows return with
conversation, actions, and results intact.**

1. Keep `/root/` and its existing password/session boundary as the sole URL.
Do not create a second mobile site or a second Captain backend.
2. Add a read-only `GET` history endpoint or extend the existing status
   response to return paginated durable turn records from
   `data/live-captain/live-captain.db`, including sequence, role, timestamp,
   text, and linked execution/event identifiers.
3. Add a compact History drawer/list in `console/index.html` that loads on
   page open, lets the operator select a prior turn, and preserves the current
   live transcript position. This makes a reload visibly prove continuity.
4. Persist a normalized execution record for each turn/tool event (or add a
   replay projection over the existing diagnostic/event data), so a result
   produced while the Android tab was open can be inspected after returning to
   Windows. Do not imply that live SSE alone is durable.
5. Make reconnect explicit: on SSE reconnect, fetch the durable history and
   status before accepting a new turn; show “reconnected / history restored”
   or a concrete fault banner.
6. Perform one Admiral-controlled two-device acceptance test with a harmless
   marker. Start on Windows, continue from Android, reload Android, return to
   Windows, and verify the same marker, Captain replies, execution summary,
   and result are visible in the history projection.

No provider migration, new frontend, or Habitat revival is required for this
smallest loop.

## 4. Exact blockers and Admiral-required verification

- **Credential/device access:** this audit intentionally did not log in or
  send a turn. The Admiral must perform the two-device acceptance test with
  the existing Root Console credential.
- **Android behavior is not verified here:** source CSS and keyboard paths
  were inspected, but no Android browser session was available to test mobile
  viewport, background-tab behavior, cookie retention, SSE reconnection,
  virtual keyboard resizing, or scroll position.
- **Cross-device session semantics:** the shared server-side SQLite path and
  HTTPS cookie make it plausible, but concurrent device ownership and
  duplicate submission behavior require an actual acceptance test.
- **Tool-result durability:** live app-server events are visibly handled in
  the browser, but the audit found no UI/API that reconstructs the complete
  historical tool-event timeline after reload. This is the main technical
  blocker for the phrase “actions and results intact.”
- **Backend identity:** the bootstrap source defaults to AGY and supports
  multiple daemon backends. The authenticated status payload, or a harmless
  real turn, should be used by the Admiral to confirm which backend is active
  in the deployed process before relying on provider-specific behavior.
- **Habitat security:** its source exposes unauthenticated write-capable API
  operations and permissive CORS. It must not be exposed or revived as the
  everyday public path without an explicit security repair.

## 5. Saved audit report

This report is saved at:

`/home/cgl/dev/monad/docs/reports/2026-09-15-captain-interface-reconnaissance.md`

Primary current evidence includes:

- `console/index.html` and `console/assets/js/root-console.js`
- `tools/live-captain/server.py`, `persistence.py`, and `codex_daemon.py`
- `tools/root-console/server.py` and `codex_daemon.py`
- `tools/living-captain/web_service.py`, `live_captain_engine.py`, and
  `conversation.py`
- `tools/live-captain/habitat_server.py` and `habitat_store.py`
- `scripts/Caddyfile`
- current systemd state and live HTTP probes recorded during this audit

Historical context was used only from `LIVE_CAPTAIN_COMMISSIONING_REPORT.md`,
`docs/reports/2026-08-02-live-captain-phone-analysis-packet.md`, and the
component READMEs; those records are not treated as current runtime proof.
