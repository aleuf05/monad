# Periscope Station Mk II Engineering Report

## Summary

Mk II transforms the Mk I procedural observation view into a photographic compositing prototype while preserving the station's static Canvas 2D architecture and interaction model.

## Scope

This packet owns:

- `toys/periscope/app.js`
- `toys/periscope/index.html`
- `toys/periscope/style.css`
- `toys/periscope/assets/sprites/`
- `toys/periscope/README.md`
- `toys/periscope/mk2/REQUIREMENTS.md`
- `toys/periscope/mk2/ENGINEERING_REPORT.md`

This packet must not touch:

- `toys/fleet-motion/`
- `toys/bridge/`
- `toys/shared/`
- `fleetcore/`
- top-level deployment files
- top-level `README.md`

## Created Artifacts

- `assets/backgrounds/sea-horizon-mk2.png`
- `assets/source/scout-sprite-chromakey.png`
- `assets/sprites/scout-alpha.png`
- `assets/sprites/vessel-scout.svg`
- `assets/sprites/vessel-tanker.svg`
- `assets/sprites/vessel-dhow.svg`
- `assets/sprites/vessel-pilot.svg`
- `assets/sprites/vessel-coaster.svg`
- `mk2/REQUIREMENTS.md`
- `mk2/ENGINEERING_REPORT.md`

## Modified Artifacts

- `app.js`
- `README.md`

## Implementation Notes

- Added image asset loading with `ready` and `failed` states.
- Added bearing-driven sea plate panning.
- Added Canvas atmosphere pass with haze, horizon glow, glare, and subtle deterministic grain.
- Replaced the visible contact glyph with a transparent scout sprite when assets load.
- Kept procedural ocean and geometric contact rendering as graceful fallbacks.
- Preserved scout projection, drag bearing controls, contact strip selection, Details button, and vessel panel updates.

## Vessel Asset Registry Checkpoint

This packet adds class-correct vessel rendering and horizon-aware placement:

- Added transparent SVG runtime sprites for scout, tanker, dhow, pilot boat, and
  coastal freighter/coaster contacts.
- Added a Periscope-side vessel profile registry that maps shared contact class
  text to sprite, apparent physical size, waterline, and haze behavior.
- Separated distance placement from physical vessel size: range now places a
  contact relative to the horizon, while class controls apparent vessel scale.
- Distant contacts now sit closer to the horizon instead of drifting down into
  foreground water.
- Tankers render larger than pilot boats or dhows at comparable range.
- Existing `scout-alpha.png` remains available as a fallback if a class sprite
  is missing or fails to load.

Validation performed:

- `node --check toys/periscope/app.js`.
- `git diff --check` on the modified Periscope files.
- Served the repository root with `python -m http.server 8790 --bind 127.0.0.1`.
- Seeded browser-local shared fleet state with scout, tanker, dhow, pilot boat,
  and coaster contacts.
- Loaded `http://127.0.0.1:8790/toys/periscope/` in Chrome through Playwright.
- Verified class contacts populated, tanker tracking worked, the canvas rendered,
  and no console errors or failed asset requests appeared.

## Validation Performed

- `node --check toys/periscope/app.js` passed.
- Served the repository locally and loaded `/toys/periscope/` in the browser.
- Verified the photographic sea background rendered with the transparent scout sprite.
- Verified the Details button and contact-card selection update the existing vessel details panel.
- Verified drag interaction changes bearing while keeping the panel state operational.
- Verified a 390px mobile viewport keeps the periscope and contact controls usable.
- Temporarily hid runtime assets and verified graceful fallback to procedural ocean and geometric contact glyphs.
- Browser console error logs were empty during normal render, interaction, mobile, and fallback checks.

## Recommended Next Sprint

Run an asset foundry sprint: generate cleaned sprite variants per scout, convert final runtime assets to size-optimized WebP/PNG, and tune range-specific haze, blur, and wake strength.

## Optics Upgrade Checkpoint

The next Mk II visual pass adds presentation optics without changing the
Periscope architecture:

- Added visible 1x, 4x, and 10x optics controls.
- Added explicit FOV tiers: 54 degrees, 28 degrees, and 14 degrees.
- Added optics-aware background zoom, reticle density, shimmer, sprite scale,
  and contact projection.
- Added acquisition assist so switching magnification recenters on the selected
  or nearest contact instead of dropping the vessel out of view.
- Added a short acquisition cue: selected or re-centered contacts receive a
  reticle pulse, and the field note names the acquired contact.
- Updated Mk II requirements with current asset dimensions and runtime naming
  conventions.

Validation performed:

- `node --check toys/periscope/app.js`.
- `git diff --check` on the modified Periscope files.
- Served the repository root with `python -m http.server 8790 --bind 127.0.0.1`.
- Loaded `http://127.0.0.1:8790/toys/periscope/` in Chrome through Playwright.
- Verified 1x starts active with visible contacts and a nonblank canvas.
- Verified 4x updates the readout and bearing marks.
- Verified 10x updates the readout, keeps a contact in field, keeps Details active,
  and reports no console errors.
