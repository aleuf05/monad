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
       |  - Bootstrap API (port 4778) & Habitat Server (port 4777)   |
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
| **Captain Habitat API** | `4777` | `live-captain-habitat.service` (user unit) | Phone messaging SSE, multi-thread storage, tool execution, Heart lessons |
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
   - When the Captain performs real actions (sounding the ship, reading/writing files, persisting rules), distinct tool badges render above the response with expandable summaries.

7. **Captain Heart Modal (`❤️`):**
   - View durable operational lessons extracted from operator corrections.
   - Directly persist new governing rules without manual file edits.

---

## 3. Root Console (`/root/`)

The Root Console remains the operational command deck for deep inspection, system configuration, diagnostics, and long-form outputs.

**URL:** `https://cameronlampley.com/root/`  
**Authentication:** Gated by password cookie issued by `public-root-auth`.

### Command Deck Capabilities

- **Bridge / Command Draft Postures:** Switch between rapid conversational turn mode and structured long-form drafting.
- **Push-to-Talk Voice:** Hold-to-speak audio capture with server-side transcription and voice playback.
- **Corpus Search & Navigation:** Query live doctrine (`D_t`), reports, and Admiralty archive documents.
- **Generated Images & 3D Stage:** Inspect rendered assets, glTF Kraken models, and previews.
- **M³ Cycle Evaluator:** Review proposed repository mutations before committing.

---

## 4. Shared Identity & Continuity

The Live Captain operates under strict single-identity doctrine. Both the Phone Terminal and Root Console bind to the exact same governing state:

1. **Canonical Posture:** [`EDIT-THIS-ONE-FILE.md`](file:///home/cgl/dev/monad/EDIT-THIS-ONE-FILE.md) — The single authoritative file governing Captain behavior across all embodiments.
2. **Current Bearing:** [`tools/live-captain/context/current-bearing.md`](file:///home/cgl/dev/monad/tools/live-captain/context/current-bearing.md) — The active operational course and mission context.
3. **Continuity Ledger:** [`tools/live-captain/context/continuity-ledger.md`](file:///home/cgl/dev/monad/tools/live-captain/context/continuity-ledger.md) — Provenance-backed log of verified state facts.
4. **Heart Lessons:** `data/live-captain/habitat.db` (`heart_lessons` table) — Durable lessons learned from corrections.
5. **Claude ↔ Live Captain Channel:** [`tools/live-captain/context/claude-channel.md`](file:///home/cgl/dev/monad/tools/live-captain/context/claude-channel.md) — Shared asynchronous coordination channel.

---

## 5. Operations & Maintenance

### Sounding the Ship

To verify repository syntax, service unit alignment, Caddy routing, and CLI loader wiring:

```bash
bash scripts/sound-the-ship.sh
```

### Managing Services

```bash
# User Services (Phone Terminal Runtime)
systemctl --user status live-captain-habitat.service
systemctl --user restart live-captain-habitat.service

# System Services (Root Console & Core Daemons)
sudo systemctl status live-captain-bootstrap.service root-console.service
```

### Privileged Action Handoffs

Any operation requiring `sudo` privileges must be staged to [`/home/cgl/cmd.sh`](file:///home/cgl/cmd.sh) per standard commissioning doctrine.
