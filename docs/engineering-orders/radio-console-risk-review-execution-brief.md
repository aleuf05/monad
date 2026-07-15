# Radio Console Risk Review — One-Page Execution Brief (for Claude/Codex)

**Source:** Admiral's Supplemental Architecture Packet (risk review + prototype requirements)
**Mode:** design-space exploration, not production delivery — do not collapse to one architecture yet
**Scale flag:** this packet's full scope (3 competing architectures + blind human perceptual testing) is a multi-week research effort for one ambience toy. Proceed on what's below; treat the perceptual-testing requirement as blocked on the Admiral (needs real listeners, a logistics dependency, not an engineering task) rather than something to silently skip or silently promise.

## Do now, no further design needed

1. **Radio-state indicator, 9 states.** Extend the existing `#dataSourceValue` element: `QUIET WATCH`, `NO ELIGIBLE TRAFFIC`, `TRAFFIC SUPPRESSED`, `PREPARING REPORT`, `FLEETCORE DISCONNECTED`, `SCHEDULER FAILURE`, `PAUSED`, `SCRIPTED` (should never occur — flag as a bug if seen, scripted mode is cut), `LIVE READ-ONLY`. Hard requirement: silence must always be visibly explained.
2. **Three independent control signals**, not one scalar: **Traffic Load** (candidate-transmission count, pending threads, arrival rate), **Operational Severity** (from real FleetCore state — currently: route state, fuel_fraction thresholds, nothing else exists yet), **Command Discipline** (an operating-mode setting: quiet watch / normal / harbor / priority / battle stations / radio silence — this is configuration, not derived). Keep independently observable — no collapsing into a god scalar.
3. **Hard preemption rules, outside the scalar model, always true:** emergency traffic preempts routine; human command gets immediate access; stale transmissions expire; critical unacknowledged orders escalate; FleetCore disconnect is always surfaced; scripted ambience never claims verified authority (moot here — scripted mode is cut); duplicate events never produce duplicate announcements.
4. **Candidate-transmission schema**, every entry carries: source identity, source class (verified FleetCore state / station observation / human command / derived interpretation — scripted ambience class not needed, cut from scope), authority scope, confidence, supporting event/observation, timestamp, provenance. Already-answered rule: dramatize wording, never upgrade authority.

## Needs one more decision before building (ask, don't assume)

5. **Architecture candidates — how many to actually prototype now?** Packet asks for 3 (Central Director / Independent Stations + Arbiter / Conversation-Incident Graph), each with a written skeleton + verdict. Given the scale flag above: recommend starting with **Model A (Central Radio Director)** only — simplest, matches this toy's existing single-file architecture, fastest to get a real stress-tested skeleton in front of you. Build B/C only if A's skeleton reveals a real limitation, not on a fixed schedule.
6. **Stress scenarios — full list or a starter subset?** Packet lists 10. Recommend starting with the 4 that are cheap to trigger against the *real* live fleet today (extended routine watch, quiet watch, FleetCore disconnect/recovery, human command interruption via `RecordWatchEvent`) before building synthetic-injection scenarios (sudden contact, busy harbor, repeated alarms, conflicting observations) that need fake data since FleetCore doesn't produce those yet.

## Explicitly blocked, not silently dropped

7. **Blind perceptual testing for station identity** — needs real human listeners. Not buildable by an agent alone. Flagging as `blocked-on-human` in the work queue, not skipped.
8. **Station "character" tuning** — depends on #5/#6 landing first; premature to design before a skeleton exists to tune.

## FleetCore contract-gap checklist (verify against real code, per this packet's §6 criteria)

Already known from this session's own verification: current state *is* available via documented interface (`/snapshot`), events *do* have stable identities (`event_seq`), disconnect/recovery *is* supported (WS reconnect with backoff, just shipped), replay *is* possible (checkpoint+event-tail, tested). Not yet verified: duplicate/stale-event handling from the radio's own consumption side, provenance preservation end-to-end. Check before claiming this criterion met — don't assume it holds just because FleetCore's side is solid.
