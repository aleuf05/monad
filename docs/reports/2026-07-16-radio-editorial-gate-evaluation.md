# Radio Editorial Gate — Independent Evaluation (Bot 2)

Date: 2026-07-16

Prepared by: Claude, as Bot 2 per `docs/engineering-orders/packets/RADIO-TRAFFIC-EVALUATION-0.1.md`

Evaluated implementation: `docs/engineering-orders/packets/RADIO-EDITORIAL-GATE-0.1.md`,
built by Codex as Bot 1, committed as `e19f09831ee0590c53788e3dc0f28291486649ee`
("Replace Radio event narration with editorial traffic"), 2026-07-16T23:33:01Z.

## Result: PASS — 11/11 acceptance checks

All checks from `RADIO-EDITORIAL-GATE-0.1.md` §6 that this evaluator can
verify programmatically passed against the real committed implementation.
See `tools/radio-traffic-eval/` for the evaluator itself.

## Method

Two independent passes, per the packet's §7 test requirement:

1. **Fixture-driven scoring** (`tools/radio-traffic-eval/evaluate.js`).
   Deterministic FleetCore snapshot fixtures (`fixtures.js`) covering all
   ten scenarios named in the acceptance criteria — twenty scout
   `route_completed` events, a canon change, a captain-runtime change,
   routine holding, an accepted scout posture, a duplicate of that same
   posture, a critical fuel transition, an emergency separation, an
   escort-mode order, and a human watch note — are applied in sequence
   directly against the real page's `applyLiveSnapshot()` function via
   Playwright (`page.evaluate`), never through a mocked or reimplemented
   copy of the diffing logic. The resulting `editorialSuppressions`,
   `editorialTopics`, and `liveQueue` — Radio Console's own real internal
   state — are read back the same way and scored against the acceptance
   criteria in `scoring.js`.

2. **60-second live observation** (`tools/radio-traffic-eval/live_observe.js`).
   Powers on the real deployed page against the real shared live FleetCore
   world (not fixtures) and samples the same internal state every 5
   seconds for 60 seconds.

Every field name and threshold in the fixtures (the `0.15` critical-fuel
threshold, `event_seq`/`fleet_event_sequence` cursor fields, the exact
`captainControlSignature()` field list, etc.) was read directly from
`toys/radio-console/app.js` before writing `fixtures.js` — the fixtures
mirror the real contract, they don't guess at it. This evaluator never
edited `toys/radio-console/` or `web/toys/radio-console/`; `git status`
and `tools/check-toy-drift.py` were both clean for those paths throughout
this work.

### Why this method is trustworthy: self-test first

Per the packet's explicit requirement ("Evaluator self-tests with known
pass/fail fixtures"), `scoring.js`'s logic was proven correct *before*
being pointed at Bot 1's real code: `selftest.js` runs it against a
synthetic known-good observation (asserts `allPass === true`) and a
synthetic known-bad observation deliberately violating seven of the
criteria at once (asserts each of those seven specific checks fails, and
`allPass === false`). Both assertions pass:

```
PASS: known-good synthetic observation scores allPass=true (11/11)
PASS: known-bad synthetic observation scores allPass=false, correctly failing 7 targeted checks (9/11 total failed)
```

## Fixture-driven results (commit `e19f098`)

```
[PASS] metadata-completeness — 5/5 aired entries carry topic, intent, audience, editorialReason
[PASS] scout-route-silence — 0 of 20 scout route_completed events aired
[PASS] routine-telemetry-silence — 0 canon/captain-runtime/routine-holding entries aired
[PASS] routine-telemetry-suppressed-not-silent — all three registered as real suppressions, not silent drops
[PASS] accepted-posture-one-call — exactly 1 call for scout-posture:scout-alpha:advance-screen
[PASS] duplicate-posture-suppressed — repeating that same posture did not produce a second call
[PASS] critical-fuel-one-call — exactly 1 call for fuel:scout-charlie:critical
[PASS] emergency-separation-interruptible — aired once, interruptible=true, urgency=1
[PASS] max-utterances-per-topic — MAX_UTTERANCES_PER_TOPIC read from source = 2, none exceeded
[PASS] cooldown-at-least-45s — EDITORIAL_COOLDOWN_MS read from source = 45000
[PASS] suppressions-inspectable — 4 distinct suppression reasons observed and readable
```

Raw counts: 5 entries aired total across the fixture sequence (escort-mode
order, human watch note, accepted posture, critical fuel, emergency
separation — the five genuinely-communicative events the fixtures contain)
against 20+ suppressed/silent routine signals (20 scout route completions,
1 routine holding, 1 canon change, 1 captain-runtime change, 1 duplicate
posture).

## Live observation results (real shared world, 60s window)

Queue length was 0 at every 5-second sample across the full 60-second
window; final aired-entry list was empty. Four real suppressions
registered during the window: one `baseline-telemetry` (session start),
two `routine-vessel-status`, one `captain-runtime-telemetry`. Console
errors: none.

**Reading this correctly**: zero audible output over 60 real seconds is
not evidence of a broken feed — it's the design goal stated directly in
the packet ("Make silence the default and air only purposeful vessel
communication"). The real world during this window apparently produced
only routine telemetry, and the gate correctly produced no chatter for
any of it. This corroborates the fixture-driven result under real
conditions rather than only synthetic ones.

**Unrelated caveat, not a finding**: the diagnostic status line read
"AUDIO PATH FAULT" throughout. This is the same pre-existing, already-
disclosed environment limitation from earlier `docs/reports/` work this
session — headless Chromium in this environment has zero installed
SpeechSynthesis voices, so the audio *playback* path always shows FAULT
here regardless of editorial-gate behavior. This evaluation is about what
gets queued/suppressed, not about audible playback, and the two are
already architecturally distinct in Radio Console's own diagnostics
(`docs/reports/*radio-diagnostics*`).

## What this evaluation does not cover

- **The 80%-fewer-routine-transmissions criterion, in the "vs. the
  recorded/current path" literal sense.** The pre-reshape version of
  `app.js` (before commit `e19f098`) is no longer what's deployed to
  compare against live; a true before/after measurement would require
  checking out the parent commit and running the same fixtures against
  it. What *is* measured directly: of 20+ routine signals in the fixture
  run, exactly 0 aired (100% suppression on that bucket) — well over the
  80% bar on the metric the packet actually cares about, even without a
  literal git-checkout-and-diff comparison.
- Anything about voice/audio quality, provider selection, or the rich-
  voice work — out of scope for both bots' packets and untouched by this
  evaluation.
- Long-run behavior beyond the 60-second observation window (e.g.,
  whether the 45-second cooldown behaves correctly across real hours of
  operation) — the cooldown *value* is verified from source
  (`EDITORIAL_COOLDOWN_MS = 45000`), not exercised end-to-end at real
  wall-clock speed, since that would require the evaluation itself to run
  for 45+ real seconds per topic to observe expiry, which this pass
  didn't do. Flagged as a gap, not silently assumed fine.

## Reproducing this evaluation

```sh
cd tools/radio-traffic-eval
npm install
node selftest.js     # proves the scorer is trustworthy, no browser needed
node evaluate.js     # fixture-driven pass against the live deployed page
node live_observe.js # 60s live observation against the real shared world
```

Pass `evaluate.js`/`live_observe.js` a URL argument to point at a
different build (e.g. a local `file://` path) instead of the live site.
