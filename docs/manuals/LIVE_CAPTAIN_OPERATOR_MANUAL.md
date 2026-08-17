# Live Captain & Phone Terminal Operator Manual

**Classification:** Canonical Monad Operator Manual  
**Authority:** Live Captain, Project Monad  
**Date:** 2026-08-16  
**Status:** Commissioned & Live  

---

## 1. System Architecture & Topology

The Live Captain operates as a unified operational intelligence connected to multiple human interfaces on the front and specialized tool/agent backends on the deck.

```text
       +-------------------------------------------------------------+
       |                      HUMAN SURFACES                         |
       |                                                             |
       |  Phone Terminal (/captain/)       Root Console (/root/)     |
       |  [Everyday mobile conversation]   [Command deck & deep ops] |
       +------------------------------+------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |                        LIVE CAPTAIN                         |
       |  - Canonical Posture: EDIT-THIS-ONE-FILE.md                 |
       |  - Current Bearing: tools/live-captain/context/             |
       |  - Continuity Ledger & Heart Lessons: data/live-captain/    |
       |  - Habitat Server (port 4777) & Bootstrap API (port 4778)   |
       +------------------------------+------------------------------+
                                      |
         +----------------------------+----------------------------+
         |                            |                            |
         v                            v                            v
   +------------+              +------------+              +---------------+
   | AGY / CLI  |              |   Claude   |              |  Local Tools  |
   | Embodiment |              |   Daemon   |              |  & Services   |
   +------------+              +------------+              +---------------+
```

### Core Services & Port Assignments

| Component | Port | Service Unit | Primary Function |
|---|---|---|---|
| **Captain Habitat API** | `4777` | `live-captain-habitat.service` (user unit) | Phone messaging SSE, multi-thread storage, tool execution, Heart lessons, Job Engine |
| **Live Captain Bootstrap** | `4778` | `live-captain-bootstrap.service` (system unit) | Root Console SSE turn pipeline, arbiter, objectives, pause state |
| **Root Console Daemon** | `4792` | `root-console.service` (system unit) | Deep telemetry, corpus search, handoffs, generated-image trust mapper |
| **Public Root Auth** | `4779` | `public-root-auth.service` (system unit) | Forward auth gatekeeper for `/root/` and privileged APIs |
| **Rich Voice Engine** | `4775` | `rich-voice.service` (system unit) | Gemini-backed TTS speech generation |
| **M³ Cycle Engine** | `4798` | `m3-cycle.service` (system unit) | Corpus change evaluation & tri-condition verification |
| **Docx Packet Drop** | `4797` | `docx-intake.service` (system unit) | Unpack `.docx` packets dropped into `/root/` |

---

## 2. Phone Messaging Terminal (`/captain/`)

The Phone Terminal is designed as the Admiral's primary mobile conversational interface for rapid dictation, course guidance, operational commands, and rich media review.

**URL:** `https://cameronlampley.com/captain/`

### Features & Capabilities

1. **Instant Access ("I need Captain"):**
   - Direct web navigation from any mobile browser (Safari, Chrome, Firefox).
   - Full mobile viewport optimization with fixed viewport and dynamic keyboard support.

2. **Mobile Input & Dictation:**
   - Full compatibility with soft keyboards (Android Gboard, iOS keyboard).
   - Built-in microphone dictation support directly into the auto-expanding composer.
   - Draft preservation: unsent text is automatically saved to local storage per thread.

3. **Live Streaming SSE Turns:**
   - Real-time token streaming with markdown formatting (headers, bold, lists, code blocks).
   - Interruptible execution: the **Stop** button terminates generation cleanly.

4. **Multi-Thread Drawer:**
   - Slide-out drawer organizes conversations by topic or mission.
   - One-tap thread creation (`+ New Conversation`) and deletion.

5. **Attachment & Media Ingestion:**
   - Tap `📎` to attach images, documents, or logs directly from mobile storage or camera.
   - Files are staged to `data/live-captain/uploads/` and referenced in context.

6. **Tool Execution Badges:**
   - When the Captain performs real actions (sounding the ship, reading/writing files, dispatching agent jobs, persisting rules), distinct tool badges render above the response with expandable summaries.

7. **Captain Heart Modal (`❤️`):**
   - View durable operational lessons extracted from operator corrections.
   - Directly persist new governing rules without manual file edits.

---

## 3. Canonical Communication Model

Live Captain implements a transport-neutral semantic boundary (`tools/live-captain/comms.py`):
$$\boxed{\text{Capability belongs to the message; presentation belongs to the channel.}}$$

### Core Objects

* **`InboundMessage`**: Semantic incoming payload containing `channel`, `sender`, `conversation_id`, `text`, `media[]`, `reply_to`, `timestamp`, and `channel_metadata`.
* **`OutboundMessage`**: Semantic response containing `destination`, `text`, `media[]`, `actions[]`, `urgency` (`low`, `normal`, `high`, `emergency`), `reply_to`, and `semantic_role` (`captain`, `engineering`, `alert`).
* **`Action`**: Semantic interactive control containing `id`, `label`, `intent`, and `authority_level`.
* **`MediaItem`**: Transport-neutral rich asset reference (`image`, `document`, `audio`, `video`, `code`).

---

## 4. Trust & Authority Boundaries

The Captain classifies all incoming operator directives into observable authority gates before execution:

1. **Conversational (`AuthorityLevel.CONVERSATIONAL`):**
   - Read-only explanations, questions, and analysis (e.g., *"Explain what restarting Caddy would do"*).
   - Executes immediately without side effects.
2. **Proposed (`AuthorityLevel.PROPOSED`):**
   - Previews, diffs, and staging (e.g., *"Prepare to restart Caddy"*).
   - Generates plan and stages artifacts without mutating live services.
3. **Authorized Non-Privileged (`AuthorityLevel.AUTHORIZED`):**
   - Direct repository inspections, soundings, file edits within workspace, and job dispatches.
4. **Privileged / Sudo (`AuthorityLevel.PRIVILEGED_STAGED`):**
   - System service management, host reboots, firewall modifications.
   - **Strictly bounded:** Must be staged into [`/home/cgl/cmd.sh`](file:///home/cgl/cmd.sh) per commissioning doctrine.

---

## 5. Multi-Embodiment Agent & Job Routing

Live Captain delegates asynchronous background tasks to available backend engines (`tools/live-captain/job_engine.py`):

```text
Admiral: "Captain, have AGY inspect the mobile streaming problem."
Captain: "Dispatched. Job: job-62de0513 | Worker: agy | State: running"
...
[Background Worker executes non-interactively, persists stdout in SQLite]
...
Captain Notification: "⚙️ Worker agy completed job job-62de0513. Found: ..."
```

### Worker Engines

* **`agy` (Antigravity CLI):** Dispatched via `/home/cgl/.local/bin/agy -p "<prompt>" --output-format text --dangerously-skip-permissions`.
* **`claude` (Claude Code CLI):** Dispatched via `/home/cgl/.local/bin/claude -p "<prompt>" --permission-mode bypassPermissions`.
* **`codex` (Codex CLI):** Dispatched via `/home/cgl/.local/bin/codex exec "<prompt>"`.
* **`local` / `sound_ship`:** Dispatches local verification scripts and shell tooling.

### Job API Endpoints

- `GET /captain-api/jobs` — List recent background jobs.
- `GET /captain-api/jobs/<id>` — Get status and output for a specific job.
- `POST /captain-api/jobs` — Submit a new background job.
- `POST /captain-api/jobs/<id>/cancel` — Cancel a running job.

---

## 6. Proactive Captain-Initiated Notifications

Live Captain can initiate messages and alerts without waiting for user input (`tools/live-captain/proactive.py`):

* **API Endpoint:** `POST /captain-api/notify`
* **Payload:** `{"text": "...", "role": "captain|engineering|alert", "urgency": "normal|high"}`
* Messages are persisted immediately to the active conversation thread in SQLite (`data/live-captain/habitat.db`) and appear instantly upon opening `/captain/`.

---

## 7. Shared Identity & Continuity

The Live Captain operates under strict single-identity doctrine. Both the Phone Terminal and Root Console bind to the exact same governing state:

1. **Canonical Posture:** [`EDIT-THIS-ONE-FILE.md`](file:///home/cgl/dev/monad/EDIT-THIS-ONE-FILE.md) — The single authoritative file governing Captain behavior across all embodiments.
2. **Current Bearing:** [`tools/live-captain/context/current-bearing.md`](file:///home/cgl/dev/monad/tools/live-captain/context/current-bearing.md) — The active operational course and mission context.
3. **Continuity Ledger:** [`tools/live-captain/context/continuity-ledger.md`](file:///home/cgl/dev/monad/tools/live-captain/context/continuity-ledger.md) — Provenance-backed log of verified state facts.
4. **Heart Lessons:** `data/live-captain/habitat.db` (`heart_lessons` table) — Durable lessons learned from corrections.
5. **Claude ↔ Live Captain Channel:** [`tools/live-captain/context/claude-channel.md`](file:///home/cgl/dev/monad/tools/live-captain/context/claude-channel.md) — Shared asynchronous coordination channel.

---

## 8. Verification & Diagnostics

### Sounding the Ship

```bash
bash scripts/sound-the-ship.sh
```

### Running Test Suites

```bash
python3 -m unittest discover -s tools/root-console
python3 -m unittest discover -s tools/live-captain -p "test_*.py"
```

### Managing Services

```bash
# User Services (Phone Terminal Runtime & Habitat API)
systemctl --user status live-captain-habitat.service
systemctl --user restart live-captain-habitat.service

# System Services (Root Console & Core Daemons)
sudo systemctl status live-captain-bootstrap.service root-console.service
sudo systemctl restart live-captain-bootstrap.service root-console.service
```

---

## 9. Captain Backend Selection & Execution Architecture

Live Captain utilizes an explicit backend dispatch model (`tools/root-console/agy_daemon.py`, `tools/root-console/claude_daemon.py`, `tools/live-captain/codex_daemon.py`).

### Supported Backends

* **`CAPTAIN_BACKEND=agy` (Primary Default):** Google Antigravity CLI (`/home/cgl/.local/bin/agy`) using `gemini-3.7-flash-high` (or configured `CAPTAIN_AGY_MODEL`). Fast, deterministic, multimodal execution with automated permission bypass.
* **`CAPTAIN_BACKEND=claude`:** Anthropic Claude Code CLI (`/home/cgl/.local/bin/claude`) using `CAPTAIN_CLAUDE_MODEL` (e.g. `opus` or `sonnet`).
* **`CAPTAIN_BACKEND=codex`:** OpenAI Codex CLI app-server (`/home/cgl/.local/bin/codex`).

### Current Default

The active commissioning configuration defaults to:
$$\boxed{\text{CAPTAIN\_BACKEND}=\text{agy}}$$
Configured in `/home/cgl/.config/monad/root-console.env` and loaded by `live-captain-bootstrap.service` and `root-console.service`.

### Identifying the Active Backend

Query `/api/status` on either service with authenticated session headers:

```bash
# Live Captain Bootstrap (Port 4778)
curl -s -b "monad_root_session=<cookie>" http://127.0.0.1:4778/api/status | jq '{backend: .backend, model: .daemon.model, running: .daemon.running}'

# Root Console (Port 4792)
curl -s -b "monad_root_session=<cookie>" http://127.0.0.1:4792/api/status | jq '{backend: .backend, model: .model, running: .running}'
```

### Fallback Policy: No Silent Fallback

Per strict doctrine (doctrine 010 & commissioning mandate):
* There is **zero silent fallback** between backends. AGY will never silently fall back to Claude or Codex.
* Any unknown or misspelled backend value (e.g. `CAPTAIN_BACKEND=unknown`) **fails closed and loudly** at service startup with a descriptive `ValueError: Unknown CAPTAIN_BACKEND`.

### Failure & Recovery Behavior

1. **Turn Execution Errors:** If an inference fails or times out (default 180s timeout), the active daemon broadcasts a failed turn event, terminates any hung subprocess cleanly, logs the failure in `data/live-captain/instruction-sources.log`, and returns a `502 Bad Gateway` error with full diagnostic detail.
2. **Process Crashes:** If a daemon subprocess exits unexpectedly, `systemd` automatically restarts the service (`Restart=on-failure`, `RestartSec=3`).
3. **Continuity Safety:** Context compilation occurs strictly from persistent storage (`EDIT-THIS-ONE-FILE.md`, `current-bearing.md`, `continuity-ledger.md`, `live-captain.db`), ensuring turns are idempotent across backend swaps or service restarts.

