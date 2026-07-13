# Periscope Mk IV: three.js Migration, Optics Shader, Quacken GLB

Date: 2026-07-13
Operator: Lt. cgl
Objective: execute a work packet requesting an `EffectComposer` optical shader pass and a fabricated Quacken/"Rubber Ducky" GLB contact for Periscope, on a stated prerequisite of "canvas to three.js migration complete, functional parity confirmed."

## The bad premise, caught before writing any code

The prerequisite did not exist. Checked directly rather than assumed:

- No `THREE`/WebGL reference anywhere in this repository -- not on `main`, not on any remote branch (`fleet-motion-mk2`, `packet/periscope-optics`, `packet/periscope-vessel-assets`), not in the one stash. `remotes/origin/packet/periscope-optics` looked like it might be relevant by name but is actually a stale pre-Bridge-Station snapshot missing ~150 commits, unrelated to this work.
- `toys/periscope/mk2/REQUIREMENTS.md` had in fact explicitly banned "WebGL, Three.js, or engine conversion" for Mk II -- this would have been a hard regression of a stated boundary, not an oversight, had it been skipped.
- The packet also cited a "10Hz telemetry to 60fps interpolation pattern used in the canvas migration." Also false: FleetCore's real tick loop (`fleetcore/src/bin/serve.rs`) defaults to 1000ms (~1Hz, `--tick-ms` configurable), pushed over WebSocket, and no client-side interpolation existed anywhere in `toys/periscope` or `toys/fleet-motion`.

Surfaced both findings to the operator before any implementation. Decision: build the three.js migration for real as an implicit Phase 0, verify it holds the documented behavior, then build the packet's actual requested work on that real foundation. All three phases landed as separate commits.

## Phase 0 -- three.js migration, functional parity

`toys/periscope/app.js` (Canvas 2D, ~1100 lines, no modules) split into a state/decision layer and a render layer. Carried the state layer over near-verbatim into new `state.js`; replaced only the render layer with new `scene.js` (three.js scene/camera/ocean cylinder/contact sprites) and a thin `app.js` orchestrator. Library loaded via import map pinned to `three@0.169.0` from unpkg -- the same CDN-dependency pattern `toys/fleet-motion` already uses for Leaflet, no npm/bundler introduced. The old Canvas 2D renderer was deleted outright rather than kept as a WebGL-unavailable fallback.

Camera math: contacts and the ocean cylinder are placed in world space at their real bearing angle; camera yaw is set to `-bearing` each frame. A second, plain 2D `<canvas>` overlay stacked on top of the WebGL canvas handles the reticle graticule and per-contact labels (crisper as flat 2D, positioned via `Object3D.position.project(camera)`).

Added a small generic interpolation layer in `state.js`, keyed per contact id, sized to the real ~1-1.2s update cadence (not the packet's incorrect 10Hz) -- closes a real pre-existing gap (shared contacts previously had no smoothing between Fleet Motion's writes at all) and is what let Phase 2's duck ride the same path as every other contact with no special-cased motion code.

**Bug caught during verification, not assumed away:** the selection/acquisition ring rendered as scattered rotated blobs at 10x optics instead of a clean ring. Isolated the canvas-drawing code in a standalone test page first to rule out a drawing bug (it wasn't one) before finding the real cause: the ring's lift was a small fraction of the ship sprite's *half-height*, so it landed inside the ship's own sprite bounding box instead of clearing above it -- only the parts poking outside the ship's silhouette were visible. Fixed by lifting well clear of the full half-height and shrinking the ring to a fixed fraction of ship width instead of one that grew with an already-oversized close-zoom sprite.

Verification (served locally, driven with headless Chromium via Playwright, matching this repo's existing style for Periscope work): standalone load (zero errors), drag-to-rotate with momentum, click-to-select via `THREE.Raycaster`, optics tier switching, bearing slew on external selection change (re-ran the exact pre-Mk-IV methodology: two escorts 90 degrees apart, flip selection, sample `#bearingReadout` -- settled smoothly 031 to 089 degrees over ~2.4s, no jump-cut), selection write-back (clicked in Periscope, confirmed `MonadFleetState.selection.selectedShipId` held without reverting at +4s/+8s), and Bridge Station embed at 390x844 and 1440x900 (matched the pre-existing embed-trim log's own numbers, and happened to run live against real FleetCore-Live data with zero console/page errors).

## Phase 1 -- optics shader pass

New `effects.js`: `EffectComposer` with `RenderPass` into one combined `ShaderPass` (vignette + fresnel-style edge rim + chromatic aberration, one shader rather than three separate passes) into `OutputPass`, layered over the scene rather than baked into materials. Re-ran the full Phase 0 verification suite with the shader active: no regressions, zero errors.

Framerate: this environment's headless Chromium renders WebGL via SwiftShader (software rasterizer, confirmed via `WEBGL_debug_renderer_info` -- vendor string names it explicitly), so a measured ~12fps here is not a meaningful stand-in for real hardware and was reported as such rather than claimed as a pass/fail number. A real-device spot-check is still the only way to actually clear the packet's phone-performance acceptance criterion.

## Phase 2 -- Quacken/Rubber Ducky GLB

New `duck.js` resolves the one FleetCore contact with the stable id `tools/mission-director/mission_director.py`'s `DUCKY_ID` assigns it (`contact.rubber-ducky` -- confirmed this survives `toys/shared/fleet-state.js`'s mapping unchanged, unlike the derived "Quacken" display name, which is a title-cased callsign and not something to match on) to a lazily-loaded `GLTFLoader` model. `scene.js` always shows the normal sprite placeholder immediately regardless, and only swaps in the model if/when the fetch resolves, so no contact ever blocks on the ~29MB load and a failure just leaves the placeholder.

Added basic ambient + directional lighting to the scene for this: sprites are unlit (`SpriteMaterial` ignores scene lights) so nothing needed it before, but the GLB's PBR material rendered solid black with no light source once it was actually in the scene -- caught via screenshot, not assumed.

Verified via a synthesized shared-state write: zero GLB requests fire with no duck present anywhere in world state (confirms the lazy-load genuinely avoids the ~29MB cost in the common case); writing a duck contact triggers exactly one GLB request (200), the model loads fully textured (better than the "untextured white mesh" the original asset commit described -- the shipped GLB has color), and positions/labels itself through the same path every other contact uses. Re-ran the full Phase 0/1 regression suite again: no regressions, zero console/page errors.

No Draco compression pass on the duck asset -- out of budget for this work, flagged as a known limitation. A real mobile-network cold load of the model when a duck is actually present is still genuinely slow; the placeholder mitigation only avoids paying that cost in the no-duck case, not the worst case.

## Updated

- `toys/periscope/state.js`, `scene.js`, `app.js`, `effects.js`, `duck.js` (new/rewritten)
- `toys/periscope/index.html`, `style.css` (import map, overlay canvas)
- `toys/periscope/README.md`, `mk4/REQUIREMENTS.md`, `mk4/ENGINEERING_REPORT.md` (new)

## Known follow-ups (not done here, out of this packet's scope)

- Draco-compress the duck GLB.
- Bridge Station's own Engineering Status Board still displays the static copy "Canvas 2D static instruments" -- lives in `toys/bridge/*`, explicitly out of scope for this packet (no changes to Bridge Station). Flagged, not fixed.
- Syncing this rewrite into the manually-mirrored `web/`/`web-lan/` copies of Periscope is a separate deploy decision, not implicit scope.
