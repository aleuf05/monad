# Captain Standard Transition — Initial Observation

**Date:** 2026-08-07  
**Status:** Provisional proposal; no live process changed  
**Scope:** Identify process seams that are coupled to Claude as an actor rather
than to a role-neutral Captain standard.

## Observed seams

1. The repository still contains an explicit Claude-era division of labour.
   `docs/doctrine/014-operation-working-process.md:101-126` assigns core
   function to Claude and limits the Live Captain to non-essential function.
   The same passage records the single-reader concern but leaves it standing.

2. The root console has a backend-neutral entry point, but the neutrality is
   implemented as a switch between two actor-specific daemons:
   `tools/root-console/server.py:476-479` selects `ClaudeDaemon` or
   `CodexDaemon` from `CAPTAIN_BACKEND`.

3. The Claude daemon is an adapter that deliberately translates its event
   vocabulary into the Codex-shaped frontend envelope:
   `tools/root-console/claude_daemon.py:1-14` and `:39-42`. This is practical
   compatibility, but it makes one backend's vocabulary the implicit standard.

4. The fleet speech path names the actors as separate authorities:
   `scripts/fleet-say.py:7-16` says Claude writes production directly while the
   Captain writes only a channel file. That is a process boundary, not a
   capability-neutral contract.

5. The work queue still carries a specifically named `LC-CHANNEL-01` task to
   close a Captain → Claude loop (`docs/engineering-orders/queue.md:26-37`).
   This is evidence that the current process is organized around a relationship
   between named agents rather than around a shared exchange protocol.

## Proposed current standard

The replacement should be **Captain-standard**, not “Codex replaces Claude”:

- **Role before actor:** `Captain`, `Chief`, `Crew`, and `Admiral` are the
  stable interfaces; model, vendor, and process names are implementation
  details.
- **One exchange contract:** every handoff uses the MONAD object fields
  `TYPE / FROM / MISSION / STATUS / SUMMARY / DETAIL / EVIDENCE / NEXT`.
- **One authority rule:** Admiral intent governs purpose and boundaries;
  verified reality has veto; inherited context is evidence, not command.
- **One operational loop:** `Intent → Form → Act → Verify → Return → Distill`.
- **Backend-neutral transport:** the console and live surfaces consume a
  role-neutral event envelope. Adapters may translate provider formats, but no
  provider vocabulary becomes the semantic contract.
- **Append and supersede:** new state is explicit and provenance-bearing;
  historical objects are not silently rewritten.
- **Capability by demonstrated use:** no new integration is promoted merely
  because it sounds cleaner; a real bounded mission must show lower friction,
  better verification, or safer continuity.

## Boundary for this mission

This report records the observed coupling and a candidate standard. It does not
rename historical documents, delete Claude-specific adapters, alter the root
console, or rewrite the standing doctrine. The active discovery payload
explicitly forbids refactoring the ship while surveying it. A later
implementation order should convert this proposal into a migration plan with
an acceptance test and rollback path.

## Evidence and uncertainty

**Verified:** the paths and line ranges above exist in the current repository;
the root console defaults to `CodexDaemon` in the inspected source, while a
Claude adapter remains available.

**Inferred:** the process is partly actor-shaped because role boundaries,
channels, and frontend compatibility are named after Claude or Codex.

**Unresolved:** whether the existing adapters are still required for live
service compatibility, and which single role-neutral envelope can replace the
current event and handoff seams without breaking deployed behavior.

## Related primary sources

- `docs/doctrine/014-operation-working-process.md:101-126`
- `tools/root-console/server.py:476-479`
- `tools/root-console/claude_daemon.py:1-14,39-42`
- `scripts/fleet-say.py:7-16`
- `docs/engineering-orders/queue.md:26-37`
- `docs/monad-core/01-command-roles.md`
- `docs/monad-core/02-knowledge-cycle.md`
- `docs/monad-core/03-concept-to-mechanism.md`

## Initial watch result

On 2026-08-07, the existing Root Console and Live Captain daemon tests were
run together:

```text
python3 -m unittest tools.root-console.test_codex_daemon tools.live-captain.test_live_captain
Ran 59 tests in 4.625s — OK
```

**Verified:** the current backend adapters and their tested HTTP/event seams
pass the repository's focused test set.

**What this changes:** the first transition step should be a contract-level
observation and migration test, not an immediate daemon rewrite. Existing
behavior is a working baseline that a role-neutral standard must preserve or
explicitly supersede.

## API-use handoff

Drive/API access for this watch was deliberately bounded to:

- one folder search to ground the `MONAD` target;
- one immediate-folder listing and six bounded child-folder listings;
- targeted reads of the six named MONAD documents;
- one focused search for the referenced watch-brief phrases.

No Drive content was edited, moved, shared, or deleted. Future watches should
reuse known IDs, avoid broad content hydration, and make a new call only when
it resolves a named uncertainty or verifies a claimed change.

## Commissioned-state check

Read-only inspection of the systemd units and their environment showed:

- `root-console.service`: **active**
- `live-captain-bootstrap.service`: **active**
- `CAPTAIN_BACKEND=codex` in the shared Monad environment

**Verified:** the commissioned default currently runs the Codex backend for
both Captain surfaces, while Claude remains an available compatibility adapter
in source. No service state was changed.

## Free-running-state check

The repository already contains a server-owned free-running interaction loop;
it is documented in `tools/live-captain/context/current-bearing.md:316-335`.
That loop provides FIFO admission, shared persisted replies, one server-owned
speech artifact, and protection against stale overlapping submissions. The same
record identifies this as the stable baseline for natural interaction.

**Decision:** do not create a second autonomous loop. The correct transition
target is to observe and extend the existing loop's role-neutral contract. A
second loop would duplicate authority and recreate the exact overlap and spend
problems the current baseline was designed to remove.

**Safety boundary:** `docs/engineering-orders/living-captain-v0.2.md:53-64,85-94`
explicitly keeps unattended scheduling out of that version. Any future
free-running expansion needs a bounded spend/custody gate, explicit ownership,
and restart-safe evidence before it can write governing state.

**Admiral-level requirement:** loop stability is a command concern. A stable
loop must preserve continuity, bound concurrency and spend, survive restart,
expose its current state, and never silently widen authority. These are
acceptance conditions for any future evolution, not optional engineering
polish.
