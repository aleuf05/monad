# Periscope Station Mk IV Engineering Report

## Summary

A work packet requested two additive upgrades -- an `EffectComposer` optical
shader pass and a fabricated Quacken/"Rubber Ducky" GLB contact -- on top of
a stated prerequisite: "canvas to three.js migration complete, functional
parity confirmed." That prerequisite did not exist anywhere in this
repository. Mk IV builds it for real, verifies parity, then the shader pass
and duck integration follow as Mk IV's own later phases.

## The bad premise, and why it mattered

Before writing any code, the following were checked directly rather than
assumed:

- `git log --all`, `git branch -a`, `git stash list`, and `git grep` for any
  `THREE`/WebGL reference: none, anywhere. `mk2/REQUIREMENTS.md` had in fact
  explicitly banned "WebGL, Three.js, or engine conversion" for Mk II.
  `remotes/origin/packet/periscope-optics` exists but is a stale
  pre-Bridge-Station snapshot, not related prior work.
- The packet's cited "10Hz telemetry to 60fps interpolation pattern used in
  the canvas migration": no such interpolation existed anywhere, and
  FleetCore's real tick rate (`fleetcore/src/bin/serve.rs`) defaults to
  1000ms (~1Hz, `--tick-ms` configurable), pushed over WebSocket -- not
  10Hz, and not HTTP polling.

Both claims were surfaced to the operator before implementation started.
The decision made was to treat the three.js port as an implicit Phase 0:
build it for real, confirm it holds the documented behavior, then build the
originally-requested shader and duck work on that real foundation instead of
on an assumption.

## Architecture

`app.js` (pre-Mk-IV, ~1100 lines, Canvas 2D) split cleanly into a
state/decision layer and a render layer. Mk IV keeps the state layer
(`state.js`) close to verbatim and replaces only the render layer
(`scene.js`, three.js). This is what made "parity" a checkable claim rather
than a vibe -- the bearing/momentum/selection/shared-state code is
essentially unchanged; only how it gets drawn changed.

Camera math: the ocean cylinder and every contact are placed in world space
at their real bearing angle (`radius*sin(angle), y, -radius*cos(angle)`),
and the camera's yaw is set to `-bearing` in radians every frame. Given a
square canvas (already true pre-Mk-IV via `resizeCanvas()`), horizontal FOV
maps directly onto `camera.fov` with no aspect conversion. This makes the
old manual `relative = shortestDelta(bearing, contact.bearing)` /
`x = 0.5 + relative/fov` screen-projection math in the old `projectContact()`
unnecessary for actual rendering -- three.js's own camera does it -- though
`shortestDelta`/`visible` are still computed in `state.js` because the
contact strip and details button need "is this in field" independent of
where three.js decides to draw it.

## A real bug caught during verification, not assumed away

The selection/acquisition ring (a billboarded dashed-circle sprite meant to
sit clearly above a contact) initially rendered as scattered rotated
rectangle fragments at 10x optics instead of a clean ring. Isolating the
canvas-drawing code in a standalone test page confirmed the ring texture
itself was correct -- the bug was in `scene.js`'s 3D placement: the ring's
vertical lift was computed as a small fraction of the ship sprite's
*half-height* (a `THREE.Sprite` is centered on its position), so the ring's
center landed inside the ship's own sprite bounding box, near the
mast/superstructure artwork, rather than clearing above it. Only the parts
of the ring that fell outside the ship's silhouette were visible, reading as
disconnected blobs at high zoom where both the ship and the misplaced ring
were large on screen. Fixed by lifting the ring well clear of the sprite's
full half-height (`scale.y * 0.78`) and shrinking it to a modest, fixed
fraction of the ship's width (`scale.x * 0.26`-`0.38`) instead of a value
that scaled up alongside an already-oversized ship sprite at close zoom.

## Verification performed

Served the repository root locally, drove it with headless Chromium via
Playwright (matching this repo's existing verification style for Periscope
work):

- Standalone load: zero console/page errors, correct initial bearing/data
  source, ocean + contact labels render correctly (screenshot-verified).
- Drag-to-rotate: bearing changed during drag and continued decaying via
  momentum after release (034 deg -> 060 deg over ~1s post-release).
- Click-to-select via `THREE.Raycaster` hit-testing: correctly resolved the
  clicked contact and populated the vessel panel.
- Optics tier switching (1x/4x/10x): FOV/reticle spacing changed correctly,
  camera re-centered on the nearest/selected contact with a field-note cue.
- Bearing slew on external selection change: synthesized shared state with
  two escorts 90 degrees apart, selected the first (settled at 000 deg),
  flipped `selection.selectedShipId` to the second, sampled
  `#bearingReadout` across frames: 031 -> 056 -> 071 -> 079 -> 084 -> 086 ->
  088 -> 089 deg -- a smooth settle, no jump-cut, matching the pre-Mk-IV
  documented behavior exactly.
- Selection write-back: clicked a contact's card in Periscope, confirmed
  `MonadFleetState.selection.selectedShipId` updated immediately and held
  (rechecked at +4s and +8s) without reverting.
- Embedded in Bridge Station (390x844 and 1440x900): `is-embedded` applied
  correctly in both, `#scopeFrame` sized/positioned consistent with the
  pre-Mk-IV embed-trim log's own numbers (top: 112px at the phone
  viewport). Also happened to catch this running live against real
  FleetCore-Live data (Bridge's own dev instance was connected), rendering
  correctly end to end with zero console/page errors.

No pixel-perfect visual comparison was performed or is warranted here --
the brief calibrated verification to real scrutiny for shared-state behavior
(done above) and a smoke check for the render swap itself (also done).

## Known limitations / deliberate simplifications

- No horizon haze/glare/grain atmosphere layer, no per-contact
  distance-blur/contrast-pocket filter. These were cosmetic polish on top of
  the photo backdrop, not documented behavior; the "optics glass" look they
  approximated is Phase 1's real job now.
- No procedural-ocean fallback if the sea texture fails to load (a flat
  color substitutes) -- the elaborate wave-gradient fallback from Mk I
  predates the photographic assets Mk II shipped and was already arguably
  obsolete.
- The sea plate is still not a true seamless 360-degree panorama (documented
  since `mk2/REQUIREMENTS.md`); wrapping it once around a cylinder means one
  visible seam per revolution, same tradeoff the old tiled `drawImage` pan
  already had.
- Bridge Station's own Engineering Status Board still displays the static
  copy "Canvas 2D static instruments" -- that string lives in
  `toys/bridge/*`, which is explicitly out of scope for this work (the
  packet excluded changes to Bridge Station). Flagged here, not fixed.
- The old Canvas 2D renderer was deleted outright rather than kept as a
  WebGL-unavailable fallback. Recoverable from git history if ever needed;
  maintaining two render backends in lockstep for a toy bridge instrument
  wasn't judged worth it.

## Recommended Mk V (if picked up later)

- Draco-compress the duck GLB (Phase 2 explicitly deferred this).
- Consider syncing this rewrite into the manually-mirrored `web/`/`web-lan/`
  copies of Periscope (out of scope here -- separate deploy decision).
- If the atmosphere/haze look from the old renderer is missed after seeing
  Phase 1's shader pass in practice, it's a reasonable follow-up shader
  layer of its own -- explicitly out of scope for this packet.
