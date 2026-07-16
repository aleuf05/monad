# Packet FC-LIVE-01 — fleetcore-live vessel-event cursor fix

## Originating intent
Phase I drift sweep (Master Packet §21) comparing `toys/` source against
`web/toys/` deployed copies.

## Verified starting state
`toys/fleetcore-live/app.js` (commit `cf4b200`, 2026-07-14) cursors
vessel events on each event's own `event_seq`. The deployed copy,
`web/toys/fleetcore-live/app.js` (last touched `c856645`, 2026-07-13),
still cursored on array length (`processedVesselEventCount`), under the
stale assumption that `vessel_events` never truncates. `fleetcore-serve`
now keeps only a bounded tail (`--vessel-event-retention`, issue #6), so
the deployed logic would silently stop seeing new vessel events once
the array rotated past retention.

## Objective / problem
Deploy the `event_seq`-cursor fix from source to production.

## Scope
`web/toys/fleetcore-live/app.js` only -- the cursor-tracking logic.

## Exclusions
`index.html`'s `#serverUrl` (`wss://cameronlampley.com/fleetcore-ws/ws`)
is a correct, deliberate prod value -- not touched. `README.md` and
`test_vessel_events_cursor.js` are source-only dev artifacts, not
shipped.

## Constraints / authority
`web/` is live production, no staging (`docs/deployment.md`). Single-
file logic swap, no schema or security surface.

## Acceptance criteria
- Deployed cursor logic matches source (`event_seq`-based)
- `index.html` unchanged
- `https://cameronlampley.com/toys/fleetcore-live/` returns 200 post-change
- New vessel events continue rendering (no regression)
- `watch_events` handling (separate idiom, same file) unaffected

## Tests / rollback
Source's `test_vessel_events_cursor.js` (7 tests) run against the
deployed logic post-copy. Rollback: single-file `git checkout`.

## Assigned actor
Claude, this session, on explicit authorization ("send").

## Evidence
- Diff confirmed clean (3 hunks, no dev-only strings) before applying
- `cp toys/fleetcore-live/app.js web/toys/fleetcore-live/app.js`
- Live 200 check on both the page and `app.js` directly
- `node test_vessel_events_cursor.js` -> 7/7 pass
- Landed in commit `2742e47`

## Completion state
**verified complete -> recorded**
