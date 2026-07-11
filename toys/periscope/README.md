# Monad Periscope Station

A standalone, client-side observation station for Fleet Motion's Scout Flotilla.

Periscope is not a game, combat simulator, targeting interface, or networked service. It is a browser window into the current Monad operating world.

Mk II adds a photographic rendering prototype: a panoramic sea plate, atmospheric Canvas effects, and transparent vessel sprites while preserving the Mk I controls and data model.

Mk III adds an optics-glass visual pass: stronger distance haze, range-stable horizon placement, class-aware wake treatment, selected-contact focus, lens edge darkening, subtle chromatic fringe, and dust/glass overlays.

## Run locally

From the repository root:

```sh
python -m http.server 8080
```

Then open:

```text
http://localhost:8080/toys/periscope/
```

The artifact uses only static HTML, CSS, JavaScript, Canvas 2D, and local image assets.

## Controls

- Drag left or right inside the circular observation window to rotate bearing.
- Use the 1x, 4x, and 10x optics controls to change field of view and contact scale.
- Select a visible scout contact, use the Details button, or select a scout card to open the vessel information panel.
- Use the Details button when a scout is visible in the field.

## Mk II Rendering

- The ocean background is loaded from `assets/backgrounds/sea-horizon-mk2.png` and panned by bearing.
- Scout contacts render with `assets/sprites/scout-alpha.png` when available.
- Class-specific vessel sprites render scout, tanker, dhow, pilot boat, and coaster contacts.
- Range controls horizon placement, while vessel class controls apparent size and waterline behavior.
- Optics tiers adjust horizontal FOV, reticle density, long-lens shimmer, background zoom, and sprite scale.
- If image assets are missing, the station falls back to the Mk I procedural ocean and geometric contact glyphs.
- Mk II requirements, rendering notes, and asset pipeline guidance live in `mk2/REQUIREMENTS.md`.

## Mk III Optics Glass

- Far contacts fade through a distance veil instead of disappearing or floating over foreground water.
- Selected contacts receive a sharper contrast pocket and a restrained reticle focus cue.
- Wake width and strength vary by vessel class.
- The final Canvas pass adds vignette, edge glass, chromatic ring offset, glint, and lens dust.
- No WebGL, shader, backend, or data-contract change is required.

## Boundaries

- No combat behavior.
- No weapon symbology.
- No backend, database, authentication, networking, or AI summarization.
- Static scout data and local simulation only for Mk I.

## Shared State

When Fleet Motion has written browser-local shared state, Periscope derives
contacts from `toys/shared/fleet-state.js`. When no shared state exists, it falls
back to local demo contacts so the station remains independently runnable.

When the shared selection changes — from Fleet Motion, from Bridge's contact
roster, or from another Periscope instance — Periscope turns (slews) its
bearing toward the newly selected contact over about 2-3 seconds rather than
cutting to it instantly, the same motion a manual drag produces. This matters
more since selections can now originate from Bridge's own roster, which can
jump to any contact regardless of how far its bearing is from whatever
Periscope was already pointed at.
