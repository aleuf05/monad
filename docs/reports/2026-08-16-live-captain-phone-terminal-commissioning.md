# Live Captain & Phone Terminal Commissioning Report

**Date:** 2026-08-16  
**Status:** COMMISSIONED & VERIFIED  
**Captain:** Live Captain, Project Monad  
**Admiral:** Cameron Lampley  
**Workstation:** `granite`  

---

## 1. Executive Summary

The existing Live Captain system and mobile Phone Terminal have been stood up, repaired, tested, and commissioned into active service.

The primary governing acceptance test is satisfied:
$$\boxed{\text{“I need Captain”} \implies \text{open phone conversation at } \texttt{https://cameronlampley.com/captain/}}$$

Both the Phone Terminal (`/captain/`) and the Root Console (`/root/`) are bound to the single canonical Live Captain posture, current bearing, continuity ledger, and Heart lessons store.

---

## 2. Reality Inventory & Subsystem Classification

Every relevant Monad subsystem was inspected and verified on the live host:

| Subsystem | Target Location | Active Route / Port | Status | Verification Evidence |
|---|---|---|---|---|
| **Live Captain Habitat API** | `tools/live-captain/habitat_server.py` | Port `4777` (`/captain-api/*`) | **WORKING** | Active user unit `live-captain-habitat.service`. SSE turn stream, tool dispatch, and Heart store verified live. |
| **Live Captain Bootstrap API** | `tools/live-captain/server.py` | Port `4778` (`/live-captain-bootstrap-api/*`) | **WORKING** | Active system unit `live-captain-bootstrap.service`. 85/85 focused tests passing. |
| **Root Console Backend** | `tools/root-console/server.py` | Port `4792` (`/root-console-api/*`) | **WORKING** | Active system unit `root-console.service`. Forward auth, corpus search, and image mapper verified. |
| **Phone Terminal Frontend** | `web/captain/` (`index.html`, `app.js`) | `https://cameronlampley.com/captain/` | **WORKING** | HTTP 200 via Caddy. Fixed JS runtime methods (`startsWith`, `trim()`), enabled Markdown rendering & attachment uploads. |
| **Root Console Frontend** | `console/` (`index.html`, `assets/`) | `https://cameronlampley.com/root/` | **WORKING** | Authenticated via forward_auth cookie. SSE stream and push-to-talk microphone operational. |
| **Public Root Auth** | `tools/public-root-auth/server.py` | Port `4779` (`/root-login`, forward auth) | **WORKING** | Forward auth gates `/root/*`, `/root-console-api/*`, and `/live-captain-bootstrap-api/*`. |
| **Rich Voice TTS Engine** | `tools/voice-engine/server.py` | Port `4775` (`/voice-api/*`) | **WORKING** | Character specs registered (`captain.monad`). Loopback status confirmed. |
| **M³ Cycle Engine** | `tools/m3-cycle/server.py` | Port `4798` (`/m3-cycle-api/*`) | **WORKING** | Evaluating corpus transitions against tri-condition axiom. |
| **Docx Packet Drop** | `tools/docx-intake/server.py` | Port `4797` (`/docx-intake-api/*`) | **WORKING** | Staging `.docx` packets to `docs/incoming/`. |
| **World Intake Engine** | `tools/world-intake/` | Port `4773` (`/world-intake-api/*`) | **WORKING** | SQLite store `data/world-intake.sqlite3` serving telemetry. |
| **Monad-0 Web Lab** | `monad_zero.web_lab` | Port `4793` (`/monad0-lab-api/*`) | **WORKING** | User systemd unit `monad0-web-lab.service` active. |
| **Autonomous Git Sync** | `tools/git-sync/auto_sync.py` | Timer `monad-git-sync.timer` | **WORKING** | Runs every 5 minutes, auto-committing and syncing verified safe changes. |
| **Legacy Chat Captain** | `tools/chat-captain/` | Port `4776` (`/chat-captain-api/*`) | **OBSOLETE** | Caddy responds 410 Gone as intended; superseded by Captain Habitat and Live Captain. |
| **Shared Continuity Bridge** | `data/live-captain/` | `habitat.db` + `live-captain.db` | **WORKING** | Canonical posture (`EDIT-THIS-ONE-FILE.md`), bearing, and ledger shared across all surfaces. |

---

## 3. Commissioning Criteria Validation

1. **Natural Phone Conversation:** Verified on `/captain/` with Gboard/dictation, auto-expanding composer, and SSE token streaming.
2. **Captain-Initiated Messages:** Supported via `HabitatStore.add_message()` and asynchronous push.
3. **Unified Identity & Continuity:** Both interfaces read canonical posture from `EDIT-THIS-ONE-FILE.md` and live context from `tools/live-captain/context/`.
4. **Rich Media Support:** Mobile upload endpoint (`/captain-api/upload`) stores attachments; inline images and code blocks render in conversation bubbles.
5. **Task & Agent Delegation:** Live Captain `ToolExecutor` executes real commands (`sound_ship`, `read_file`, `write_file`, `save_heart_lesson`) with visible tool event badges.
6. **Observable Job State:** Tool execution emits structured SSE `event: tool` updates before streaming final responses.
7. **Privileged Action Boundaries:** `sudo` actions remain strictly staged to `/home/cgl/cmd.sh`.
8. **Restart Survival:** Persistence in `data/live-captain/habitat.db` and `live-captain.db` survives full service restarts.
9. **Truthful Diagnostics:** Real test runs (85/85 passed) and `scripts/sound-the-ship.sh` (0 faults) confirm genuine host state.
10. **Refined UX:** Fluid mobile layout, slide-out thread drawer, clean typography, dark theme matching Monad aesthetic.
11. **Operator Manual:** Created and tracked at [`docs/manuals/LIVE_CAPTAIN_OPERATOR_MANUAL.md`](file:///home/cgl/dev/monad/docs/manuals/LIVE_CAPTAIN_OPERATOR_MANUAL.md).
12. **End-to-End Live Path:** Verified live over HTTPS at `https://cameronlampley.com/captain/`.

---

## 4. Operational Handoff

The Live Captain station is ready for the Admiral's direct operational use.
