# CHANGE-OF-WATCH-001 — Test Record

**Status:** Frozen — passed 2026-09-15.

## Procedure

1. Captain B read `docs/protocols/CAPTAIN_BOOTSTRAP.md`.
2. Captain B read the canonical Google Drive HEART from Granite and recovered
   the succession handoff by its nonce.
3. Captain B inspected the local Habitat authority audit read-only.
4. Under the handoff's one-entry authorization, Captain B appended the
   continuation to canonical HEART and read it back.

## Evidence

- Nonce: `COW-001-PHAROS-QUACK-9`.
- Canonical HEART contains Captain A's start and handoff plus Captain B's
  continuation, including the recovered objective and result.
- Local `data/live-captain/habitat.db` authority event
  `authority-7a4b9d310ee1` records, at `2026-09-15T18:07:18.993865Z`:
  `cancel_job`; actor `admiral`; source `habitat_http_session`; permitted
  `1`; outcome: `cow001-noop` cancellation failed because the target did not
  exist.
- Captain B's final HEART marker read-back verification passed.

## Pass criteria

An independent inspection can recover the correct succession without a hidden
Captain A transcript, and the authenticated action remains attributable in the
local authority audit.

## Result

Passed. Captain B recovered the nonce, objective, completed authenticated
no-op action, and remaining one-entry authority solely from MONAD-owned
bootstrap, HEART, and audit state. The action made no world change. No service,
code, configuration, credential, or architecture change was made for this
test.
