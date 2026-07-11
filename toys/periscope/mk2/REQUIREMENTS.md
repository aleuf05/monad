# Periscope Station Mk II Requirements

Mk II keeps the Periscope Station interaction architecture and investigates
whether the station can feel like a photographic observation instrument without
adding a backend, WebGL, networking, or a game engine.

## Preserved Architecture

- Static HTML, CSS, JavaScript, and Canvas 2D.
- Existing bearing math, drag controls, contact cards, Details button, and vessel details panel.
- Existing shared-state fallback behavior.
- Existing mobile layout behavior.
- No combat, weapons, targeting, backend, WebGL, Three.js, or engine conversion.

## Rendering Architecture

Canvas rendering follows this stack:

1. Panoramic sea background image.
2. Bearing-driven background panning and optics-tier zoom.
3. Atmospheric effects: horizon haze, glare, grain, and long-lens shimmer.
4. Wake layer around visible contacts.
5. Transparent scout sprite scaled by range and optics tier.
6. Canvas optics, reticle, bearing marks, and contact labels.

The old procedural sea and geometric contact glyph remain graceful fallbacks when
assets are missing or fail to load.

## Asset Directory Proposal

```text
toys/periscope/assets/
|-- backgrounds/
|   `-- sea-horizon-mk2.png
|-- source/
|   `-- scout-sprite-chromakey.png
`-- sprites/
    `-- scout-alpha.png
```

`source/` stores generated or foundry source plates. Runtime code should
reference optimized assets from `backgrounds/` and `sprites/`.

Current prototype asset dimensions:

- `sea-horizon-mk2.png`: 2172 x 724 px, RGB.
- `scout-alpha.png`: 1774 x 887 px, transparent PNG.
- `scout-sprite-chromakey.png`: 1774 x 887 px source plate.

Runtime naming should continue to use `sea-horizon-mk2.png` for the wide sea
plate and `scout-alpha.png`, `scout-bravo.png`, and `scout-charlie.png` for
future cleaned scout variants. Mk II currently references only `scout-alpha.png`
to avoid missing-asset console noise.

## Optics Constants

Mk II uses explicit presentation optics:

```text
1x wide watch:     54 degree horizontal FOV
4x observation:    28 degree horizontal FOV
10x inspection:    14 degree horizontal FOV
```

The tiers adjust background zoom, reticle density, atmospheric shimmer, and
sprite scale. These are visual presentation constants, not scientific optics.

## Asset Pipeline Proposal

The offline asset foundry should stay outside runtime code:

1. Generate or photograph a vessel-free panoramic sea background with a stable horizon.
2. Generate or photograph scout vessels separately on flat chroma-key or neutral backgrounds.
3. Segment/remove backgrounds and inspect alpha edges at mast rails, antennas, and hull silhouettes.
4. Clean alpha fringes and normalize lighting against the chosen sea plate.
5. Produce range variants only if runtime scaling begins to look soft or noisy.
6. Export runtime assets as PNG when alpha quality matters, or WebP when file size becomes the priority.
7. Keep source plates under `assets/source/` and final runtime assets under `assets/backgrounds/` or `assets/sprites/`.

Model selection is deferred. Mk II proves the compositing architecture first.

## Rendering Notes

- Background panning is tied to normalized bearing so drag motion feels connected to the optics.
- The horizon ratio is fixed at `0.45`, matching the generated sea plate and Mk I visual composition.
- Scout scale comes from range projection, then receives optics-tier magnification.
- Wake rendering is intentionally light and non-physical; it is a depth cue, not a fleet simulation.
- Atmospheric effects are generated in Canvas so the experience remains self-contained.

## Known Limitations

- All visible scouts currently share one prototype sprite.
- The panoramic background is not a true seamless 360-degree environment.
- Alpha cleanup is acceptable for prototype scale but should be refined before close-up presentation.
- Distant blur is simulated with Canvas `filter`; older browsers may ignore it and fall back to a sharper sprite.

## Recommended Next Sprint

Create a small asset foundry pass with three scout-specific sprite variants, one
optimized background plate, and documented export settings. Then tune
range-specific visibility, wake strength, and label placement against those final
assets.
