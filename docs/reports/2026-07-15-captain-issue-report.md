# Captain Issue Report

Date: 2026-07-15

Prepared for: Captain / Lieutenant

Scope: Issues #6, #13, #14 deployment, plus new Living Captain V0.1/V0.2

## Executive status

Two independent bodies of work are integrated, tested, merged, and clean
at commit `52d3c71535d345131c1a88789f78be8d4f8a5664`, and are both staged
in one combined commissioning package (`/home/cgl/cmd.sh`) because
neither has been activated yet:

1. **Issues #6, #13, #14** (previously reported
   [2026-07-14](2026-07-14-captain-issue-report.md), documented in
   [`docs/handoff/2026-07-14-issues-6-13-14-deployment.md`](../handoff/2026-07-14-issues-6-13-14-deployment.md)):
   code and tests complete; the running services still predate all three
   fixes.
2. **Living Captain V0.1 + V0.2** (new,
   [`living-captain-v0.1.md`](../engineering-orders/living-captain-v0.1.md) /
   [`-v0.2.md`](../engineering-orders/living-captain-v0.2.md)): persistent
   identity, read-only sight, an append-only action record, a custody
   read-allowlist, and a restart-safe spend ceiling. **Zero
   canon-mutating write authority exists anywhere in this system.** Its
   static frontend (`web/toys/living-captain/`, homepage card) is already
   live; its backend (`living-captain-status.service`, a read-only status
   API) is not yet installed, so the page currently shows "Unreachable."

## Action required from the Lieutenant

Run:

```sh
/home/cgl/cmd.sh
```

Pinned to the current clean commit. It supersedes the earlier
issues-6-13-14-only package (pinned to `f5afd2c`, never run, now stale
against this HEAD) by folding both batches into one, per the
commissioning-handoff current-batch rule. It builds and tests FleetCore,
deploys the corrected `fleetcore-live` web client, restarts
`fleetcore-serve`/`world-intake`/`living-fleet-memory`, installs
`living-captain-status.service` and its Caddy route, captures
before/after evidence and rollback backups (with SHA-256 hashes), proves
the new binary and both new/changed public routes are live, and flushes
itself to a "nothing queued" script afterward.

## Active engineering issues

### FleetCore vessel-event history grows without a bound

GitHub: [Issue #6](https://github.com/aleuf05/monad/issues/6) -- **fix
implemented, not yet deployed.** Bounded retention (default 2,000,
configurable), stable `event_seq`, migration/trim of pre-existing state.
See the deployment gate below.

### Living World Intake never reached FleetCore

GitHub: [Issue #13](https://github.com/aleuf05/monad/issues/13) -- **fix
implemented, not yet deployed.** `/adjudications` now actually submits
compiled commands to FleetCore.

### Captain-memory reflection non-atomicity

GitHub: [Issue #14](https://github.com/aleuf05/monad/issues/14) -- fix
implemented and merged (single-transaction reflection commit); included
in this deployment for the running service to pick up, not a new code
change.

## Deployment or commissioning gates

Until `/home/cgl/cmd.sh` runs:

- live FleetCore rejects the new `event_seq`/retention fields as unknown;
- the deployed `fleetcore-live` web client still uses array-length
  cursoring, not `event_seq`;
- `world-intake`'s `/adjudications` handler runs the pre-fix binary that
  compiles but never submits;
- `living-captain-status.service` is not installed; `/living-captain-api/*`
  is not routed through Caddy;
- `https://cameronlampley.com/toys/living-captain/` is click-reachable
  right now but its status panel reads "Unreachable" -- an expected,
  temporary, honestly-surfaced gap, not a bug.

This is an activation gate, not an unresolved code defect, for all of the
above.

## Resolved findings

- Living Captain's restart demonstration (`demo_restart.py`) proves
  identity, `created_at`, and the full action-record history survive an
  unclean process kill and reassembly, run against real live
  `fleetcore-serve`/`world-intake`.
- Living Captain's custody boundary (`demo_boundary.py`) proves a non-GET
  or out-of-manifest request is rejected before any network call, and
  that rejections are durably logged (`custody_rejection`).
- Living Captain's spend boundary proves an exhausted observe budget
  persists correctly across restart and does not silently reset
  (`spend_exhausted`, logged).
- A real bug was found and fixed in `test_captain_v02.py` during
  integration review: it loaded `sight.py` a second time via a separate
  `importlib` spec, so its `CustodyViolation` was a distinct class object
  from the one `captain.py` actually raises -- `assertRaises` silently
  failed to match. Fixed by reusing the exact module instance `captain.py`
  already imports.
- Sight adapters (`tools/living-captain/sight.py`) were delegated to and
  independently verified from Codex: mocked unit tests plus a separate
  live smoke check against the real endpoints, not just Codex's
  self-report.

## Validation evidence

- Living Captain: 9/9 unit tests pass
  (`test_sight.py`, `test_captain.py`, `test_captain_v02.py`).
- Living Captain: both operator demonstrations
  (`demo_restart.py`, `demo_boundary.py`, bundled as `demo_all.py`) pass
  against real live `fleetcore-serve` and `world-intake`.
- Issues #6/#13/#14: per
  [the 2026-07-14 handoff doc](../handoff/2026-07-14-issues-6-13-14-deployment.md) --
  FleetCore's Rust suite, `fleetcore-live`'s Node cursor tests, Mission
  Director's Python cursor tests, and World Intake's suite all passing at
  last run. Re-run as a pre-flight gate inside `cmd.sh` itself before any
  restart.
- Repository and GitHub PR state clean; all changes pushed to
  `agent/living-world-intake-v0-1`.

## Deferred risks and evidence gaps

- Living Captain's status API was verified via JSON-contract
  field-by-field cross-checking against its frontend and code review, not
  a rendered browser screenshot -- no `chromium-cli` or Playwright is
  installed in this environment, and installing a full browser toolchain
  for a static read-only display page was judged disproportionate given
  this repo's "smallest test set that gives reasonable confidence"
  standing policy. Worth a real browser check once conveniently possible.
- Living Captain has no scheduler or unattended loop -- its identity only
  advances when an operator invokes it (currently `demo_all.py` or a
  direct `assemble()` call). This is by design for V0.1/V0.2, not a gap,
  but it means the status page reflects the last manual run, not a live
  continuously-updating process.
- Direct FleetCore command-authority (no per-connection auth) remains the
  same standing, previously-accepted tradeoff described in
  `docs/deployment.md`; this deployment does not change it and is not
  re-flagging it as new.
- Another session was observed actively editing `tools/living-captain/`
  on this same shared primary checkout concurrently with this one (see
  `docs/incidents/2026-07-14-world-intake-concurrent-session-collision.md`
  for the precedent this pattern matches). No file-content collision or
  branch clobbering occurred this time -- work was adapted in place
  rather than overwritten -- but the underlying shared-checkout risk that
  incident documented remains unaddressed as a process matter.

## Recommended next action

Run `/home/cgl/cmd.sh`, then verify
`https://cameronlampley.com/toys/living-captain/` shows a green
"Connected" status with real identity/spend/action-log data, and that
`https://cameronlampley.com/toys/fleetcore-live/` and a real World Intake
approval both reflect the #6/#13 fixes.

## Readiness statement

- Issues #6/#13/#14: **READY FOR DEPLOYMENT** (per the 2026-07-14 handoff
  doc's own conclusion, unchanged).
- Living Captain V0.1: **READY FOR CUSTODY/SPEND DESIGN** -- superseded by
  V0.2's completion below.
- Living Captain V0.2: **READY FOR WRITE-PATH DESIGN** -- the custody/spend
  gate is proven; a V0.3 order would be required before any
  canon-mutating write capability is even proposed, and none is proposed
  here.
