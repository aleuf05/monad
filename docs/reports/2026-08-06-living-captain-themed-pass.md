# Living Captain Strategic Themed Pass — 2026-08-06

**Result:** Engineering PASS; physical phone acceptance pending

## Truth

The stack was live and automated suites passed, but phone stress windows
produced no bridge telemetry. Source inspection found that
`reportBridgeSignal()` referenced removed variable `liveMode`. The resulting
`ReferenceError` occurred at pointer-down before recognition started. The
diagnostic instrument itself blocked the behavior it was meant to observe.

## Flow

The authoritative path is:

```text
authenticated Root page → Captain SSE open → trigger armed
→ pointer hold → browser recognition → release flush → one /turn
→ FIFO Captain admission → persisted reply → one server speech artifact
→ SSE playback → optional barge-in
```

## Friction repairs

- Removed the stale `liveMode` reference from bridge telemetry.
- Added a regression guard against reintroducing that legacy state.
- Treated a mobile client disappearing after persisted/SSE completion as a
  closed response reader rather than emitting a server traceback; turn
  admission still releases in `finally`.
- Preserved single-shot Bridge recognition and Command Draft behavior already
  present in the live source.

## Projection repairs

Phone render inspection revealed a second independent defect: the terminal
occupied only part of the viewport, empty-state text clipped, and the later
base speech-acceptance rule overrode the mobile hide rule, consuming the input
row. Mobile geometry now explicitly spans the viewport, compacts the prompt
source, permits input shrink, centers guidance, and hides acceptance controls
with sufficient specificity. A second render confirmed the trigger and input
together across the full phone width.

## Proof

- 57 Live Captain tests passed.
- 31 Root Console tests passed.
- 7 focused push-to-talk protocol tests passed.
- Browser JavaScript and server Python syntax passed.
- Desktop and three successive phone projections were inspected.
- Live Captain bootstrap restarted cleanly; Co-Captain stack reports READY.
- Repository whitespace validation passed for the touched implementation.

## Metaprocess refinement

The themed-pass order worked because each pass changed the next question:
truth found an impossible telemetry silence; flow located the earliest browser
boundary; friction removed the blocker; projection found a separate visual
constraint; proof prevented either repair from being mistaken for human audio
acceptance. Future interface campaigns retain this order while allowing a pass
to collapse when it supplies no new evidence.

The remaining gate is deliberately narrow: perform the real phone hold,
release, transcript, spoken reply, and barge-in trial, then record either
`✓ heard` or a precise fault.
