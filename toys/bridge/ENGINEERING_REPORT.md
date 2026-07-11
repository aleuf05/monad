# Bridge Station Mk V Engineering Report

## Summary

Bridge Station Mk III (previous revision of this report) replaced the three-way tab switch with a two-way split and made Fleet-Motion-originated selection changes visible across both live panels. It left one documented gap: a contact selected directly in Periscope was local to Periscope only and never propagated to Fleet Motion or Bridge's status rail.

Mk IV closes that gap. Periscope now writes `selection.selectedShipId` back into `MonadFleetState` when a contact is selected by direct user interaction (scope click, details button, or contact strip) — but not when Periscope's own selection changes because it auto-acquired Fleet Motion's selection, which would have created a feedback loop. Selection sync between Fleet Motion, Periscope, and Bridge is now genuinely bidirectional. Closing this required more than adding a write call: Fleet Motion, which is still the periodic writer of the rest of `MonadFleetState`, needed to check for externally-written selection changes on every animation frame rather than its own independently-throttled poll, or its own next scheduled write could land on stale local state and silently clobber Periscope's selection within a few seconds. This was caught by browser verification, not by inspection — see Validation Performed.

## Created Artifacts

No new top-level artifacts were created.

## Modified Artifacts

- `toys/periscope/app.js`
- `toys/fleet-motion/app.js`
- `toys/bridge/README.md`
- `toys/bridge/ENGINEERING_REPORT.md`
- `logs/captains/2026/2026-07-11_bridge-live-console.md` (Mk III)
- `logs/captains/2026/2026-07-11_periscope-selection-writeback.md` (Mk IV)

## Implementation Notes

- Collapsed the `plot` and `periscope` station tabs/panels into a single `console` station. Its panel (`#panel-console`, class `live-console`) is a CSS grid holding both instrument articles (`#liveFleetMotion`, `#livePeriscope`) so both iframes are mounted and visible simultaneously rather than one being `hidden`.
- Kept the Watchbook tab and panel untouched in behavior — it is still shown/hidden via the same `selectStation()` tab logic, unmodified except for the station id set shrinking from three entries to two.
- Kept the existing standalone `../fleet-motion/` and `../periscope/` "Open standalone" links and the station-links block intact.
- Added a CSS grid (`.live-console`) with two equal columns on desktop, collapsing to a single stacked column with scrollable overflow under 900px viewport width so the layout stays usable (not squeezed) on common mobile widths.
- Added a `syncPulse` CSS keyframe animation and `is-sync-pulse` class on `.live-instrument` panels for the selection-change cue.
- In `app.js`, `updateSharedState()` now reads `selection.selectedShipId` on every tick (both the 1s poll interval and the existing `storage` event listener) and compares it against the last-observed value. On a change, it calls `triggerSyncCue()`, which adds `is-sync-pulse` to both live-instrument panels and removes it after 900ms. The comparison is gated by a `hasObservedSelection` flag so the cue does not fire on first load.
- Did not modify Fleet Motion's or Periscope's simulation logic, and did not modify Watchbook.
- Did not change the `MonadFleetState` schema.

## Mk IV Implementation Notes

- `toys/periscope/app.js`'s `selectVessel(contact, { propagate = false })` gained an options parameter. The three call sites that originate from direct user interaction (scope click, details button, contact strip) now pass `{ propagate: true }`. The two call sites that don't represent a new user choice — `autoAcquireSharedContact()`'s re-selection when it adopts Fleet Motion's current selection, and `updateSelectedPanel()`'s per-frame refresh of the already-selected contact's live data — pass nothing, defaulting to `false`. Without that distinction, Periscope would echo Fleet Motion's own selection straight back to it every frame, which is harmless in itself (idempotent) but pointless churn, and more importantly would make it impossible to tell "Periscope is reflecting Fleet Motion" apart from "Periscope is asserting its own choice."
- A new `propagateSelection(contact)` in `toys/periscope/app.js` only fires for contacts with a `source` field set (i.e. contacts that came from `MonadFleetState` via `toScoutContacts()`), never for Periscope's own local demo vessels, which have no corresponding id in Fleet Motion's state to select. It reads the current shared state, and no-ops if `selection.selectedShipId` already matches (avoiding a redundant write on repeat clicks of the same contact).
- `toys/fleet-motion/app.js` gained `syncExternalSelection()`, called at the top of `animationFrame()` — before `advanceFleet()` (and therefore before `updateStatus()` -> `persistFleetState()`) runs. It compares `MonadFleetState.read()`'s `selection.selectedShipId` against a tracked `lastKnownSelectionId`; on a genuine external change it adopts the id into the local `selectedShipId` variable, triggers the same `flashAt()` cue `selectShip()` already used, and calls `updateStatus()`.
- The first version of `syncExternalSelection()` was throttled to once per second on its own timer, independent of `persistFleetState()`'s ~1.2s write throttle. Browser verification (see below) caught that this independent throttling reintroduced the exact clobbering problem this feature was meant to fix: Fleet Motion's own periodic write could fire on stale local state in the gap between two external-selection polls, silently overwriting Periscope's selection back to Fleet Motion's previous value. Localstorage would show the correct id for a moment, then quietly revert within a few seconds. The fix was to remove the independent throttle: `syncExternalSelection()` now runs unthrottled on every frame, which by construction always executes immediately before `persistFleetState()` in the same synchronous call chain, so `selectedShipId` is guaranteed current at the moment any write decision is made. This mirrors the existing precedent of Periscope's own `sharedContacts()`, which already does a full `MonadFleetState.read()` + JSON parse every animation frame with no reported performance issue in this codebase.
- `lastKnownSelectionId` is also updated on Fleet Motion's own successful writes (inside `persistFleetState()`), not just on adoption, so a value Fleet Motion itself just wrote is never mistaken for a new external change on the next frame's poll.

## Why both iframes had to be visible, not just present

Bridge Mk II already mounted all three iframes in the DOM at all times and only toggled a `hidden` attribute to switch between them. That was insufficient for this sprint's goal: browsers throttle or fully suspend `requestAnimationFrame` in `display:none` iframes, and Periscope's re-aim logic (`autoAcquireSharedContact`, `render()`) runs inside a `requestAnimationFrame` loop. With Periscope hidden, its render loop — and therefore its shared-state polling — does not reliably run, so the live sync built in `7003852` had no visible (or even actively running) audience. Making both panels part of the same always-visible grid, rather than switching between them, is what actually makes the sync observable.

## Resolved Gap: Periscope-originated selection now propagates

Mk III shipped with selecting a contact directly in Periscope (`selectVessel()` in `toys/periscope/app.js`) only updating Periscope's own local `state.selectedId` and detail panel, with no write to `MonadFleetState`. Mk IV closes this — see Mk IV Implementation Notes above. No `MonadFleetState` schema change was needed; the existing `selection.selectedShipId` field was already generic enough to carry a Periscope-originated id.

## Validation Performed (Mk III, retained)

- Ran `node --check toys/bridge/app.js` — no syntax errors.
- Served the repository root with `python3 -m http.server 8790 --bind 127.0.0.1`.
- Drove `http://127.0.0.1:8790/toys/bridge/` with a headless Chromium via Playwright (installed ad hoc into the scratchpad for this verification; not added to the repo).
- Verified Fleet Motion and Periscope are both visible at 1440×900 with no click, and both iframes resolve to their expected `src`.
- Dispatched a native click on an escort marker inside the Fleet Motion iframe. Confirmed: both `#liveFleetMotion` and `#livePeriscope` gained the `is-sync-pulse` class within the poll window; Periscope's own detail panel updated to the selected escort's name and bearing; the Bridge status rail's "Selected Vessel" field updated to match — all without a page or iframe reload.
- Resized to 390×844 (a common mobile width). Confirmed the two live panels stack vertically, each retaining a usable ~300px height within the viewport, rather than being squeezed side by side.
- Clicked the Watchbook tab. Confirmed the Watchbook panel becomes visible, the Live Console panel becomes hidden, and Watchbook's own content (log index, search, latest log) renders normally.
- Captured all browser console messages (`console` events and `pageerror`) throughout the run: none were emitted, so no new console warnings or errors were introduced.

## Validation Performed (Mk IV)

- Ran `node --check toys/periscope/app.js` and `node --check toys/fleet-motion/app.js` — no syntax errors.
- Served the repository root locally and drove `toys/bridge/` with headless Chromium via Playwright.
- Periscope-originated selection: clicked a contact button in Periscope's contact strip (`escort-bravo`, deliberately not whichever contact was already auto-acquired, so the click is unambiguously the cause). Confirmed Periscope's own panel updated immediately, Bridge's status rail updated to "Escort Bravo," and `localStorage`'s `MonadFleetState.selection.selectedShipId` read back `escort-bravo` directly from Fleet Motion's own frame.
- Caught the clobbering race described above: the first implementation showed Fleet Motion's own selection readout (`#stateSelectionValue`) still showing "MONAD" immediately after the click, still showing it 4s and 8s later, and `localStorage` reverting to `monad` by the 8-second mark — the write was being made and then silently undone. Fixed by removing `syncExternalSelection()`'s independent throttle (see Mk IV Implementation Notes). Re-ran the identical scenario after the fix: Fleet Motion's own readout showed "ESCORT BRAVO" immediately and held steady through 8 seconds of repeated checks, with `localStorage` never reverting.
- Fleet-Motion-originated selection (regression check for the Mk III behavior): called `selectShip("escort-charlie")` inside the Fleet Motion iframe directly. Confirmed the `is-sync-pulse` class appeared on both `#liveFleetMotion` and `#livePeriscope`, Bridge's status rail updated to "Escort Charlie," Periscope's panel updated to "SCOUT CHARLIE," and the pulse class cleared again after ~900ms (not stuck on) — all still working exactly as Mk III left it.
- Captured all browser `console` and `pageerror` events across every run: none were emitted.

## Validation Caveat

Fleet Motion's own splash/loading overlay is visible over its map on the initial screenshot in the sandboxed run; this is Fleet Motion's existing intro-sequence behavior (also present in the Mk II tabbed layout) and is unrelated to either sprint's changes. Mk IV verification did not re-check the 390×844 mobile layout, since neither sprint touched CSS/layout — only selection-sync JavaScript.

## Mk V: Radio Console Integration

Wired the newly built `toys/radio-console/` (see `logs/captains/2026/2026-07-11_radio-console-v1.md`) into Bridge as a third Live Console panel, at Admiral C's direction after the standalone toy was already built and verified. Unlike Fleet Motion and Periscope, Radio Console has no `MonadFleetState` read or write path — it's pure ambience, so this integration is purely layout/embedding, not another state-sync sprint.

### Implementation Notes

- `toys/bridge/index.html`: added a third `<article class="instrument live-instrument live-instrument-compact" id="liveRadio">` inside `#panel-console`, matching the existing header/iframe/"Open standalone" pattern used by Fleet Motion and Periscope.
- `toys/bridge/style.css`: `.live-console` gained `grid-template-rows: minmax(0, 1fr) auto` — the two big instruments keep the flexible top row, Radio Console gets a new `.live-instrument-compact` class (`grid-column: 1 / -1; height: 360px`) spanning both columns in a shorter row below rather than becoming an awkward third item in a fixed two-column grid. `.station-deck`'s `min-height` budget was raised (760px→1000px base, 720px→940px at the 1180px breakpoint) to make room without compressing Fleet Motion/Periscope's map area.
- The 360px height figure isn't a guess — it came from directly measuring Radio Console's own rendered layout at Bridge's actual embedded width (~490px) via a Playwright script, after the toy-side embedded trimming below reduced its natural height from ~436px to ~337px, then adding a small margin.
- `toys/radio-console/`'s own `app.js` and `style.css` gained an embedding-aware mode: `window.self !== window.top` (wrapped in try/catch, since a cross-origin check would throw) adds an `is-embedded` class to `<body>`, and `style.css` uses that class to hide the subtitle/eyebrow, shrink headings and control padding, and cap the transcript's visible height — specifically for Bridge's fixed short panel. The same page still renders at full size when opened standalone (`toys/radio-console/README.md`, `Open standalone` link). A separate change lowered Radio Console's own two-column-to-one-column stacking breakpoint from 780px to 420px, because Bridge's ~490px-wide panel column would otherwise fall inside the old breakpoint and stack signal/transcript vertically — taller, not shorter, exactly backwards from what embedding needed. 390px phones in standalone mode still fall below 420px and stack as before.

### Validation Performed

- Playwright, both desktop (1440×900) and mobile (390×844): confirmed the Radio Console iframe loads (`#powerButton` reachable via `frameLocator`), no horizontal overflow on mobile, zero console errors or page errors across every run.
- First attempt used a 220px compact-panel height with no embedded-mode trimming at all: screenshots showed Radio Console's panel cut off right after the status strip — Power/channel/volume controls, the signal meter, and the transcript were all below the fold and, because `.station-deck` uses `overflow: hidden`, genuinely inaccessible, not just requiring a scroll. Caught by looking at the actual rendered screenshot, not by inspecting the CSS in isolation.
- Measured the real fix iteratively rather than guessing a final number twice: a dedicated Playwright script loaded Radio Console inside a bare iframe at Bridge's actual embedded width and read back `getBoundingClientRect().height` for the shell and each internal panel, both before and after adding the embedded-trimming CSS (436px → 337px), which is what the final 360px panel height and the CSS trims above are based on.
- Re-screenshotted after the fix, powered on via a real click (`frameLocator("...").locator("#powerButton").click()`) and forced an immediate transmission: Power/channel chips/volume/mute, the signal meter (now animating with real amber bars while "transmitting"), and a transcript entry are all visible within the panel on both desktop and mobile, with no scrolling required to reach the primary controls.

## Mk V.1: Mobile Live Console Layout Fix

The Validation Caveat above flagged that the 390×844 mobile layout hadn't been re-checked since Mk III's CSS/layout work. This watch closed that gap and found a real bug: at ≤900px, Periscope's panel rendered at 215px tall (iframe itself only 150px) while Fleet Motion and Radio Console both got their intended 360px — Periscope's own optics view (`.scope-frame`) sat below the visible fold, reachable only via an unindicated scroll inside the iframe. Present on screen, but not usable by a first-time visitor, per this sprint's own acceptance criteria.

### Root Cause

`.live-console`'s base rule (non-mobile) sets `grid-template-rows: minmax(0, 1fr) auto` — two explicit tracks sized for the desktop two-column layout (row 1: Fleet Motion + Periscope side by side; row 2: Radio Console spanning both columns). The `@media (max-width: 900px)` override switches to a single column and adds `grid-auto-rows: minmax(300px, 1fr)`, intended to give every stacked panel a fair minimum height, but never cleared the inherited `grid-template-rows`. With two explicit tracks still in force, the first two stacked items (Fleet Motion, then Periscope) were placed into those pre-existing tracks (`minmax(0,1fr)` and `auto`) instead of picking up `grid-auto-rows`. Fleet Motion's track was still flexible enough to look fine; Periscope landed in the `auto` track and collapsed to intrinsic content size. Radio Console, the only panel to actually fall into an auto-generated row, was masked by its own hardcoded `height: 360px`, which is why this went unnoticed.

### Fix

`toys/bridge/style.css`, `@media (max-width: 900px)` block: added `grid-template-rows: none;` alongside the existing `grid-template-columns: 1fr` and `grid-auto-rows: minmax(300px, 1fr)`, so all three stacked panels are sized by the same auto-row rule with no leftover two-row definition to fall into.

### Validation Performed

- Playwright at 390×844 against a local static server, before and after the fix. Before: Fleet Motion/Radio Console articles 360px, Periscope article 215px (iframe 150px), Periscope's `.scope-frame` at `top: 319` inside a 1265px-tall document — confirmed off-screen and not reachable without an unadvertised in-iframe scroll. After: all three articles measured 360px, Periscope's iframe grew to 295px.
- Confirmed no horizontal overflow (`document.body.scrollWidth === window.innerWidth`) and zero console/page errors, both before and after.
- Called `selectShip("escort-alpha")` inside the embedded Fleet Motion iframe at mobile width: Bridge's status rail updated to "Escort Alpha," confirming the selection-sync logic itself was unaffected by the CSS bug (this was a layout-only defect, not a regression in Mk III/Mk IV's sync work).
- Scrolled inside Periscope's own iframe document post-fix and confirmed the scope view, bearing dial, and nearest-contact readout (`SCOUT ALPHA`, `252° / 140.7 nm`) are reachable.

### Known Remaining Gap

Even at its corrected 360px/295px height, Periscope's own internal document (1370px tall standalone, unchanged by this fix) still needs an in-iframe scroll to reach the scope view — Fleet Motion and Radio Console do not require this. Radio Console closed an equivalent problem for itself with an `is-embedded` body-class trim (see Mk V above); Periscope has no such embed-aware mode today. Giving Periscope the same treatment would touch `toys/periscope/app.js` and `style.css`, which is outside this sprint's stated boundary (Bridge-side layout and event-wiring only, no Fleet Motion/Periscope simulation or presentation changes) — recommended as the next follow-on sprint rather than folded in here.

## Mk V.2: Periscope Embed-Aware Mobile Trim

Closes the Mk V.1 Known Remaining Gap. Periscope's own document was still taller than its Bridge panel even after Mk V.1's grid fix gave it a fair share of height — reaching the scope view required an in-iframe scroll with no visible hint that it was there.

### Implementation Notes

- `toys/periscope/app.js`: added the same `window.self !== window.top` (try/catch-wrapped) check Radio Console already uses, applying an `is-embedded` class to `<body>`. Standalone `toys/periscope/` never sets this class and is visually unchanged.
- `toys/periscope/style.css`: added `body.is-embedded` overrides — hides the eyebrow label, shrinks the `<h1>` and bearing readout, collapses the optics bar back to a single compact row and drops its redundant magnification-text readout (the button group's `is-active` state already conveys the same information), reduces shell/bridge padding and gaps, and lets `.scope-frame` size itself to the embedded viewport (`min(70vw, 62vh)`) instead of the standalone sizing.
- These overrides deliberately win regardless of viewport width, unlike Periscope's existing width-based `@media` breakpoints. Those breakpoints assume a full phone screen's worth of vertical room and were found to make the embedded case *worse* at Bridge's ~348px panel width — e.g. `@media (max-width: 520px)` stacks the header into two rows instead of one, exactly the kind of regression Radio Console's own README already flagged for its analogous breakpoint problem (`toys/radio-console/README.md`'s embedding notes). `is-embedded` overrides are scoped by embedding context, not viewport width, so they apply cleanly on top without fighting those rules.

### Validation Performed

- Playwright, embedded inside Bridge at 390×844: `.scope-frame` moved from `top: 319px` (Mk V.1 baseline, unreachable without scroll) to `top: 112px`, `height: 183px` — fully inside the panel's 295px iframe viewport with no scroll needed. The contact strip starts just below the fold (`top: 303px`) rather than requiring the much longer scroll it did before.
- Playwright, embedded inside Bridge at 1440×900 (desktop): zero console/page errors.
- Playwright, standalone `toys/periscope/` at 390×844: confirmed `body.is-embedded` is never applied (`window.self === window.top`), and the page renders with its full header, full optics bar, and original sizing — unaffected by any of the above.
- Zero console/page errors captured across every run.

## Mk V.3: Command Token Field

Bridge's Status Board gained a Command Authority row (Granted/Read-Only/N/A) in the prior watch (see the Bridge Command Authority Rail log), but the only way to actually change it was editing the URL's `?commandToken=` param and reloading the entire page — a poor fit for a page that calls itself a unified command console.

### Implementation Notes

- `toys/bridge/index.html`: a `<form id="commandTokenForm">` with a `type="password"` input and an Apply button, placed in the Engineering panel right after the status list (adjacent to the Command Authority row it controls).
- `toys/bridge/app.js`: `applyCommandToken(token)` targets only `#liveFleetMotion iframe` — Radio Console also matches the existing `[data-instrument-src]` selector but ignores `commandToken` entirely, and reloading it on every token change would cut off whatever it's currently playing for no reason. It rebuilds that one iframe's `src` via `URL`/`searchParams` (preserving whatever `live`/`fleetcoreServer` params are already on it) and mirrors the token into Bridge's own address bar with `history.replaceState` so a refresh doesn't drop authority the operator just granted. Submitting an empty value clears the param and drops back to read-only, both on the iframe and in the URL.
- This is a deliberate, operator-triggered reload of one iframe, not the "never touch `.src` twice" case the initial-load code comment warns against (that one is specifically about avoiding an unwanted flash on first load).
- The token is exposed in the iframe's `src` and Bridge's own URL exactly as it already was via the manual `?commandToken=` URL param — this doesn't introduce a new exposure, just a more convenient way to set the same thing. The input still masks on-screen entry (`type="password"`).

### Validation Performed

Playwright against the real `fleetcore-serve` already running on this box (`--command-token bridge-3-0-lan`):

- Loaded Bridge with `?live=1` (no token): Command Authority read "Read-Only," Data Source read "FleetCore Live."
- Typed `bridge-3-0-lan` into the new field and submitted: Fleet Motion's iframe `src` gained `&commandToken=bridge-3-0-lan`, Bridge's own URL gained the same param via `replaceState`, Command Authority flipped to "Granted," and Fleet Motion's own Pause control (previously disabled read-only) became enabled — all without Bridge itself reloading.
- Cleared the field and resubmitted: iframe `src` and page URL both dropped `commandToken`, Command Authority reverted to "Read-Only."
- Zero console/page errors across the whole run.

## Recommended Next Watch

Radio Console's own v2 (live-fleet-state-aware chatter) and stretch goal (real broadcast source) remain fully deferred, per the original feature request's own priority note — see `toys/radio-console/README.md`. Periscope's contact strip can still grow tall enough to push the vessel detail panel below the fold when many contacts are present (it wraps to 3-column rows) — untouched by any recent watch and worth a look if it comes up again. The Command Token field has no client-side format validation and no feedback for a submitted-but-rejected token beyond the Command Authority row itself staying "Read-Only" a second later — acceptable for now since that's the same signal an invalid URL-param token already gave, but a more immediate "token rejected" cue would be a reasonable small follow-up.
