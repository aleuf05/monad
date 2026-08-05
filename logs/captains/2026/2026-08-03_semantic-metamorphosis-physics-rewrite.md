# Semantic Text Metamorphosis — Physics Rewrite (v0.2)

Date: 2026-08-03
Follow-up to: `2026-08-03_semantic-metamorphosis-wired-live.md` (wired the
v0.1 fixed five-phase macro into the real Captain loop). Admiral's review
of that version: "cheap trick... nowhere near enough... must be under full
captain control, not a cheap trick... feel live, smooth, physical
coherent."

## What was actually wrong

v0.1's `perform(spec)` was one hardcoded animation (fixed WAAPI keyframes:
9 discrete points on a circle, linear interpolation). The "spec" only let
the Captain swap in different words/glyphs into that same fixed shape —
not a real capability, a parameterized skin on one trick. And the motion
itself read as mechanical because it *was* mechanical: a pre-computed path
traced open-loop, not a simulation.

## What changed

Full rewrite of `console/assets/js/semantic-metamorphosis.js`:

- **Real physics, not keyframes.** Every actor is a critically-underdamped
  spring body (position, rotation, scale, brightness, opacity) integrated
  every `requestAnimationFrame` tick via semi-implicit Euler, chasing a
  target that primitives set (and, for `orbit`, continuously move). This
  is what produces organic ease-in/overshoot/settle for free, instead of a
  fixed interpolation curve.
- **Composable primitive vocabulary**, not one macro: `orbit`, `scatter`,
  `converge`, `shed`, `morph`, `merge`, `pulse`, `crystallize`, `trail`,
  `land`. Chainable in any order via `SemanticMetamorphosis#run(steps,
  opts)`. The Captain picks the shape of the moment, not just its words.
- **"Feels physical" specifics**: per-body mass/stiffness/damping jitter
  (+-15-20%) so a group never moves in lockstep; velocity-driven
  squash-and-stretch (classic animation principle — elongate along
  heading, compress perpendicular, proportional to speed) computed every
  frame from real velocity, not scripted; velocity carried across
  primitives with no reset, so one move flows into the next with real
  follow-through (e.g. `merge` inherits the mean velocity of the bodies it
  combines); orbit radius/speed wobble per body so circles aren't
  CAD-perfect.
- **New trigger DSL**: `⟦fx: phrases="a, b" | op1(args) | op2(args) |
  ...⟧`, documented in `captain-kernel.md` with the full primitive list
  and an example chain. The old `⟦metamorphose: phrases="a,b" =>
  "result"⟧` still works, now implemented as sugar for one particular
  chain (`orbit→shed→morph→crystallize→land`) over the new engine —
  nothing already-shipped regressed.
- `console/index.html` sidebar demo updated to a 9-step chain
  (`scatter→orbit→trail→shed→converge→merge→pulse→crystallize→land`)
  showing the actual range now available.

## Honest scope note on "fully arbitrary"

This is composable choreography over a real physics engine, not literal
arbitrary code execution. It covers a wide space (any order/combination of
10 primitives, each generously parameterized), but it is not "the Captain
writes and runs any motion program whatsoever." That would be a different,
larger, and separately-risky feature (a sandboxed scripting hook executing
Captain-authored code against the DOM). Deliberately not built this pass —
flagged as the next escalation if this primitive set turns out to still be
insufficient, per the Admiral's own framing ("try first... if doesn't
work will get aid").

## Bugs found and fixed during verification

1. A second `⟦fx: ...⟧`/`⟦metamorphose: ...⟧` trigger arriving while a
   previous one is still animating is correctly dropped (the engine only
   runs one choreography at a time) but the rejected promise was
   unhandled, surfacing as a console error. Fixed: `runMetamorphosisTrigger`
   now catches it. The tag is still stripped from the visible message
   either way, so raw syntax never leaks into the transcript even when
   dropped.
2. The anchor glyph element created by `lift` was appended to the overlay
   but never removed on either the success or cancel path — a permanent
   per-run DOM leak. Fixed: folded into the existing `restoreFns` cleanup
   array used by both paths.

## Verification (real, not narrated)

No Live Captain session password this session (same standing limitation).
Verified against the real, unmodified, live files with headless-Chromium
(`puppeteer-core` + `/snap/bin/chromium`, scratch dir, not part of the
app), isolated per scenario (fresh page load each):

- **Real continuous motion**: sampled an in-flight actor's CSS transform
  across 6 animation frames during an `orbit` — 6/6 distinct values,
  squash-stretch scale visibly ramping with speed (1.01 → 1.5), rotation
  tracking heading — confirms genuine per-frame simulation, not
  instant-snap-to-final-value.
- **Full 9-primitive pipeline** (scatter→orbit→trail→shed→converge→
  merge→pulse→crystallize→land): lands correct text
  ("testable recursive hypothesis ◆"), tag stripped from display, zero
  leftover actor/overlay DOM (confirmed both immediately and 500ms later,
  to rule out a transient trail-ghost read).
- **Reduced motion**: same 5-step structural sequence, correct
  `ExecutionResult`, collapses to ~11ms instead of seconds — motion
  skipped, structure and announcements preserved.
- **Cancel mid-flight**: resolves `cancelled:true`, source text restored
  exactly, zero leftover DOM.
- **Concurrent triggers**: second trigger while first is still running is
  dropped cleanly, no console errors, no half-applied state.
- **Legacy tag**: `⟦metamorphose: ...⟧` still produces correct output
  through the new engine.

`node --check` clean on both touched JS files; capability JSON valid.

## Two more bugs found and fixed after the Admiral's follow-up question

Asked directly: "can he move emoji and special symbols?" Tested it rather
than assuming -- and the honest answer was "not correctly, yet":

3. `buildCharSpans` split text with plain `.split("")`, which cuts by raw
   UTF-16 code unit, not by human-perceived character. Any emoji above the
   Basic Multilingual Plane (almost all modern emoji, e.g. a compass) is a
   surrogate pair and got shattered into two broken/invisible glyph
   fragments mid-flight; a ZWJ compound emoji (e.g. a family sequence)
   exploded into seven meaningless fragments. Final landed text was
   unaffected (that path reuses the original whole string), but the
   animation itself would visibly break on real emoji. Fixed with a
   grapheme-aware splitter (`Intl.Segmenter` grapheme mode, `Array.from`
   fallback) -- verified before/after: a compass and a three-person family
   emoji each now render and move as exactly one span instead of 2 and 7
   broken fragments respectively.
4. `land` on more than one remaining phrase auto-merges them, but if the
   chain never called `morph`/`merge`/`crystallize` to set a result text,
   it merged into an empty string -- not data loss (the source phrases are
   always separately restored in the message text) but an anticlimactic
   invisible landed marker. Fixed: falls back to the joined found phrases
   instead of blank text. Verified: `hope`/`fear` with no result-setting
   step now correctly lands "hope fear" instead of nothing.

Full regression suite (pipeline/reduced/cancel/back-to-back/legacy) re-run
clean after both fixes: zero console errors, zero leftover DOM in every
scenario.

## Completion state

**live** — same files `cameronlampley.com/root` serves, no separate
deploy step. Structurally and behaviorally verified end-to-end via
headless browser against the real files. Not yet observed through a real
authenticated Captain turn, and — the one thing no amount of automated
testing can confirm — whether the *motion itself* actually reads as
"physical" to a human watching it, as opposed to merely being
physically-simulated under the hood. That judgment needs the Admiral's own
eyes on `cameronlampley.com/root`.
