# Periscope Station Mk IV Requirements

Mk IV replaces the Canvas 2D render layer with three.js, as a prerequisite
for a separately-scoped optical shader pass and a fabricated Quacken/"Rubber
Ducky" GLB contact (see `ENGINEERING_REPORT.md` for why this prerequisite
had to be built rather than assumed).

## Preserved behavior (must not regress)

- Drag-to-rotate bearing with momentum decay.
- Smooth bearing slew (not a jump-cut) when the selected contact changes
  externally (Fleet Motion, Bridge's contact roster, another Periscope
  instance).
- Three optics tiers (1x/4x/10x) changing field of view, contact scale, and
  re-centering on the nearest/selected contact.
- Reading contacts from `toys/shared/fleet-state.js` when Fleet Motion has
  written shared state, falling back to three local demo vessels otherwise.
- Click-to-select (scope, Details button, contact strip), with selection
  write-back into `MonadFleetState.selection` for shared-state-sourced
  contacts only.
- The `is-embedded` trim when Bridge Station iframes this page.
- Zero backend, database, authentication, networking, or AI summarization.
- No combat behavior, no weapon symbology.

## What changed under the hood

- Rendering is three.js (`WebGLRenderer` bound to the existing
  `#periscopeCanvas`), loaded via an import map pinned to `three@0.169.0`
  from unpkg -- the same CDN-dependency pattern `toys/fleet-motion` already
  uses for Leaflet. No npm, no bundler, no build step.
- The ocean backdrop is a real `CylinderGeometry` wrapped once around 360
  degrees with the existing `sea-horizon-mk2.png` sea plate. The camera
  yaws with bearing, so panning is real camera rotation, not a manual
  texture-offset trick -- this also means the old ambient "drift" scroll and
  the tiled-seam workaround are gone (the seam still exists once per
  revolution, same as before; see `ENGINEERING_REPORT.md`).
- Contacts are billboarded `THREE.Sprite`s using the existing per-class
  vessel PNGs, with a simple wake sprite. Range affects placement via real
  camera perspective rather than a hand-tuned screen-space curve.
- The reticle graticule and per-contact labels are drawn on a second, plain
  2D `<canvas>` (`#periscopeOverlay`) stacked on top of the WebGL canvas,
  using `Object3D.position.project(camera)` for label anchoring. This keeps
  crisp text/line rendering without fighting WebGL for it.
- A new interpolation layer in `state.js` smooths shared contacts between
  Fleet Motion's real update cadence (~1-1.2s, not the 10Hz once assumed)
  and the 60fps render loop, generic per-contact-id, not duck-specific.
- The old Canvas 2D renderer is deleted outright, not kept as a
  WebGL-unavailable fallback (see `ENGINEERING_REPORT.md` for why).

## Explicit simplifications (see ENGINEERING_REPORT.md for full rationale)

- No horizon haze/glare/grain atmosphere layer and no per-contact
  distance-blur/contrast-pocket filter -- the "optics glass" look is now
  Phase 1's job via a real `EffectComposer` pass, not reproduced in the base
  scene.
- No procedural-ocean fallback if the sea texture fails to load; a flat
  color stands in instead.
