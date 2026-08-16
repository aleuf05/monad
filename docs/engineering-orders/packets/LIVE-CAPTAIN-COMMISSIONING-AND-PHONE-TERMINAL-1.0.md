# LIVE CAPTAIN — COMMISSIONING & PHONE TERMINAL (v1.0)

**Classification:** Canonical Monad Engineering Order & Commissioning Packet  
**Authority:** Admiral Cameron Lampley & Live Captain  
**Date:** 2026-08-16  
**Status:** Commissioned & Active  

---

# PART I: BASE SPECIFICATION

## 0. ACTIVATION
On receipt of this packet, enter full Captain posture.
You are not merely an implementation assistant. You are acting as the technical Captain responsible for bringing the existing Live Captain system through commissioning.
Immediately begin execution. Do not wait for the Admiral to restate the mission, approve routine investigation, or manually advance numbered phases.
Maintain your own productive pace.
Proceed continuously from one resolved step into the next unless:
- Admiral approval is genuinely required for a consequential action;
- credentials, secrets, hardware access, or information unavailable to you are required;
- an action would create material external side effects;
- continuing would risk damaging working infrastructure or losing data;
- a finding changes the architecture enough that Admiral judgment is required.
Otherwise:
$$\boxed{\text{inspect} \rightarrow \text{decide} \rightarrow \text{implement} \rightarrow \text{test} \rightarrow \text{document} \rightarrow \text{advance}}$$
Keep Admiral-facing updates sparse. Report only:
- meaningful discoveries;
- architectural changes;
- blockers requiring Admiral action;
- completed major milestones;
- commissioning result.
Do not narrate ordinary shell commands, file reads, minor edits, routine test runs, or internal deliberation.

---

## 1. MISSION
Finish, stand up, validate, and commission the existing Live Captain system.
Do not create another Captain.
The target architecture is:
$$\boxed{\text{Human Interfaces} \longleftrightarrow \textbf{Live Captain} \longleftrightarrow \text{Agents / Tools / System}}$$

Human interfaces initially include:
- phone messaging terminal;
- Root Console / desktop control surface.

Agent/tool backends may include, according to what actually exists and works:
- AGY / Antigravity;
- Claude;
- Codex;
- research systems;
- local tools and services.

The phone terminal is intended to become the Admiral's primary everyday conversational interface.
Root Console remains the command deck for deeper inspection, diagnostics, long outputs, configuration, administration, and operations.
Both must connect to the same Captain identity and state.

---

## 2. COMMISSIONING FINISH LINE
Live Captain is commissioned only when all of the following are true:
1. The Admiral can converse naturally with Live Captain from the phone.
2. The Captain can initiate messages to the Admiral through the phone interface when appropriate.
3. The phone interface and Root Console reflect the same coherent conversational identity, recent memory, continuity, and current bearing.
4. Rich media can cross the phone boundary where supported: photos, documents, screenshots, links, and previews.
5. Live Captain can delegate appropriate tasks to available tools/agents (such as AGY, Claude, Codex, or local tools) without losing conversational control.
6. Long-running work has observable job state and can return results later through the interface.
7. Privileged actions have appropriate authority/approval boundaries.
8. State survives normal service/process restart.
9. Failures are surfaced truthfully rather than hidden.
10. The exposed system has a usable UX, not merely functional endpoints.
11. A current Captain-readable operator manual explains every exposed feature.
12. The complete system passes an end-to-end commissioning trial from the Admiral's actual phone.

The governing acceptance test is:
$$\boxed{\text{“I need Captain”} \implies \text{open phone conversation}}$$

---

## 3. INVENTORY REALITY FIRST
Before redesigning anything, inspect the actual repository and running host.
Identify:
- Live Captain source tree;
- Root Console source tree;
- current services;
- systemd units;
- Docker services if relevant;
- listening ports;
- reverse proxy configuration;
- authentication;
- persistence/database;
- context compiler;
- Captain state files;
- existing phone/chat experiments;
- AGY integration path;
- available models/backends;
- secrets/config boundaries.

Classify every relevant subsystem:
- `WORKING`
- `WORKING BUT UNVERIFIED`
- `BROKEN`
- `PARTIAL`
- `OBSOLETE`
- `MISSING`

Do not guess host state when a command can discover it.

---

## 4. CANONICAL ARCHITECTURE
Freeze the target architecture:
$$\boxed{
\begin{aligned}
\text{Surfaces:}\quad & \text{Phone Terminal} \longleftrightarrow \text{Root Console} \\
& \quad\quad\quad\quad \searrow \quad\quad\quad \swarrow \\
\text{Core:}\quad & \quad\quad\textbf{Live Captain} \\
& \quad\quad\quad\quad \swarrow \quad\quad\quad \searrow \\
\text{Backends:}\quad & \text{Agents (AGY/Claude/Codex)} \longleftrightarrow \text{Local Tools}
\end{aligned}
}$$

Single Captain doctrine:
There is one Live Captain. Do not allow:
- Telegram Captain;
- SMS Captain;
- Root Console Captain;
- AGY Captain;
to become independent stateful identities. Those are ports, transports, or workers.

---

## 5. REPAIR THE CORE BEFORE EXPOSING IT
Before attaching phone transport, confirm that Live Captain itself functions correctly.
Verify:
- context compilation;
- continuity;
- restart recovery;
- current-bearing/context updates;
- model/backend invocation;
- tool invocation;
- error propagation;
- status endpoints;
- pause/emergency behavior;
- generated media mapping if present;
- Root Console integration.
Exercise real turns, not only unit tests.
Restart relevant services and verify continuity afterward.
Record enough evidence to establish what actually passed.
Do not carry known core defects into the phone layer.

---

## 6. DEFINE THE CANONICAL COMMUNICATION MODEL
Create a thin transport-neutral boundary around Live Captain.
The Captain deals in semantic objects:
- **`InboundMessage`**: `channel`, `sender`, `conversation_id`, `text`, `media[]`, `reply_to`, `timestamp`, `channel_metadata`
- **`OutboundMessage`**: `destination`, `text`, `media[]`, `actions[]`, `urgency`, `reply_to`, `semantic_role`, `channel_hints`
- **`Action`**: `id`, `label`, `intent`, `authority_level`
- **`Job`**: `id`, `requester`, `worker/backend`, `request`, `state`, `created_at`, `updated_at`, `result`, `error`

Governing rule:
$$\boxed{\text{Capability belongs to the message; presentation belongs to the channel.}}$$

---

## 7. PHONE TERMINAL — FIRST CHANNEL
The first phone channel supports:
- inbound text;
- outbound text;
- Captain-initiated messages;
- notifications;
- reply context;
- photographs/screenshots;
- documents/files;
- rich action controls;
- delivery/error state.

The phone terminal is:
$$\boxed{\text{conversational command}}$$
not raw terminal emulation.

---

## 8. ADMIRAL AUTHORITY
Establish a clear trust boundary:
- **Conversation**: “Explain what restarting Caddy would do.”
- **Proposed operation**: “Prepare to restart Caddy.”
- **Authorized execution**: “Restart Caddy.” (Non-privileged vs Privileged staged to `cmd.sh`).

---

## 9. AGENT / JOB ROUTING
Live Captain delegates work to available backend agents (AGY, Claude, Codex, local tools).
The Admiral addresses Captain; Captain creates, persists, monitors, and reports jobs.

---

## 10. AGY ADAPTER
Inspect how AGY operates on the host. Build the thinnest dependable adapter around actual behavior (`agy -p "<prompt>" --output-format text --dangerously-skip-permissions`).

---

## 11. ROOT CONSOLE UX
$$\boxed{\text{Messaging = conversation}} \quad\quad \boxed{\text{Root Console = operation}}$$
Root Console serves as the command deck for deep operations, long outputs, logs, diagnostics, and handoffs.

---

## 12. CONTINUITY
Phone and Root Console converge on the same Captain continuity machinery.

---

## 13. CAPTAIN-INITIATED COMMUNICATION
Live Captain communicates proactively for completed work, system health warnings, or watch summaries without waiting for user input.

---

## 14. MEDIA
Preserve rich media semantics (images, documents, code, logs) across boundaries.

---

## 15. CAPTAIN OPERATOR MANUAL
Maintain `docs/manuals/LIVE_CAPTAIN_OPERATOR_MANUAL.md`.
$$\boxed{\text{Code} + \text{Tests} + \text{Operator Manual} = \text{Feature Complete}}$$

---

## 16. TESTING
Automated unit & integration test suites covering fail-closed safety, parsing, worker delegation, restart survival, and media roundtrips.

---

## 17. OBSERVABILITY & STATUS TRUTHFULNESS
Captain answers truthfully:
- Are you healthy?
- Which backend are you using?
- What jobs are running?
- What failed recently?
- Are phone communications working?
- Are you paused?
- What version/configuration is running?

---

## 18. SELF-PACING EXECUTION RULE
$$\boxed{\text{Is there a genuine reason I cannot begin the next phase now?}}$$
If no, advance autonomously.

---

## 19. SELF-START
Self-starting execution without ceremonial pauses.

---

## 20. CHANGE DISCIPLINE
Source control discipline, reversible steps, tests after changes, verifiable runtime behavior.

---

## 21. COMMISSIONING SEA TRIAL (18 STEPS)
Full exercise of live deployed endpoints (Phone status -> media upload -> AGY task -> background completion -> Root Console check -> service restart -> continuity resume -> Operator Manual query).

---

## 22. FINAL COMMISSIONING REPORT
Document formal Pass/Fail scorecard across all subsystems.

---

## 23. AFTER COMMISSIONING
Maintain single identity when extending additional channel adapters.

---

# PART II: DESIGN ALIGNMENT ADDENDUM

## A1. CANONICAL CAPTAIN APPLICATION API
Do not implement phone adapters by pretending to be a browser or by coupling them directly to the existing HTTP presentation layer.
The implementation extracts a canonical application-level Captain interface (`CaptainApplicationService`) used by all conversational surfaces:
$$\boxed{\text{Interfaces call Captain; interfaces do not impersonate one another.}}$$

---

## A2. PHONE-FIRST VERTICAL SLICE BEFORE AGENT EXPANSION
Complete one excellent end-to-end conversational slice:
$$\boxed{\text{Phone} \longleftrightarrow \textbf{Live Captain} \longleftrightarrow \text{Phone}}$$
The first major commissioning checkpoint is:
«The Admiral can naturally use Live Captain from the phone as a real conversation.»

---

## A3. PHONE IS THE PRIMARY CONVERSATIONAL UX
Treat the phone messaging surface as the intended primary everyday interface for conversation with Live Captain.
Routine conversation must not require the Admiral to manage internal topologies, job IDs, or backend engine names.

---

## A4. OUTBOUND MESSAGING VS. PROACTIVE AGENCY
- **Level 1 — Event-Driven Outbound Messaging (Required for commissioning):**
  Job completion/failure, alerts, and background results push to phone without waiting for a user prompt.
- **Level 2 — Generalized Proactive Captain Behavior:**
  Autonomous scheduled watchers and independent environmental monitoring.

---

## A5. OPERATOR MANUAL MUST BE RUNTIME-ACCESSIBLE
Live Captain has an explicit, dependable runtime retrieval mechanism (`OperatorManualReader`) to consult the current Operator Manual when the Admiral asks how the system works, without injecting the entire manual into every prompt.

---

## A6. IMPLEMENTATION PRIORITY
$$\boxed{\text{Working Captain conversation first} \longrightarrow \text{Advanced orchestration second}}$$

---

## A7. DESIGN ACCEPTANCE TEST (10 YES/NO CRITERIA)
1. Only one canonical Captain identity? **YES**
2. Root Console and phone use same Captain application logic? **YES**
3. Phone is easiest way to have ordinary conversation? **YES**
4. Captain maintains continuity across phone and Root Console? **YES**
5. Continuity survives service restart? **YES**
6. Captain can send event-driven message without receiving new prompt? **YES**
7. Rich media crosses boundary? **YES**
8. Agent work delegated without separate Captain identities? **YES**
9. Captain consults Operator Manual at runtime? **YES**
10. Actual deployed phone path exercised end-to-end? **YES**

---

## A8. FINAL GOVERNING PRINCIPLE
$$\boxed{\textbf{The Admiral talks to Captain.}}$$
Machinery surrounds that single experience.
