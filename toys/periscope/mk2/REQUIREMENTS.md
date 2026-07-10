# Periscope Station Mk II Requirements

Mk II keeps the Mk I interaction architecture and investigates whether the station can feel like a photographic observation instrument without adding a backend, WebGL, networking, or Fleet Motion integration.

## Preserved Architecture

- Static HTML, CSS, JavaScript, and Canvas 2D.
- Existing scout data model in `app.js`.
- Existing bearing math, field-of-view projection, drag controls, contact cards, Details button, and vessel details panel.
- Existing mobile layout behavior.
- No combat, weapons, targeting, backend, networking, WebGL, Three.js, or game engine conversion.

## Rendering Architecture

Canvas rendering now follows this stack:

1. Panoramic sea background image.
2. Atmospheric effects: horizon haze, subtle glare, vignette supplied by CSS glass overlay, and deterministic grain.
3. Wake layer around visible contacts.
4. Transparent scout sprite scaled by range and moved by subtle vertical bob.
5. Canvas optics and contact labels.

The old procedural sea and geometric contact glyph remain as graceful fallbacks when assets are missing or fail to load.

## Asset Directory Proposal

```text
toys/periscope/assets/
├── backgrounds/
│   └── sea-horizon-mk2.png
├── source/
│   └── scout-sprite-chromakey.png
└── sprites/
    └── scout-alpha.png
```

`source/` stores generated or foundry source plates. Runtime code should reference optimized assets from `backgrounds/` and `sprites/`.

## Asset Pipeline Proposal

The offline asset foundry should stay outside runtime code:

1. Generate or photograph a vessel-free panoramic sea background with a stable horizon.
2. Generate or photograph scout vessels separately on flat chroma-key or neutral backgrounds.
3. Segment/remove backgrounds and inspect alpha edges at mast rails, antennas, and hull silhouettes.
4. Clean alpha fringes and normalize lighting against the chosen sea plate.
5. Produce range variants only if runtime scaling begins to look soft or noisy.
6. Export runtime assets as PNG when alpha quality matters, or WebP when file size becomes the priority.
7. Keep original source plates under `assets/source/` and final runtime assets under `assets/backgrounds/` or `assets/sprites/`.

Model selection is deferred. Mk II only proves the compositing architecture.

## Rendering Notes

- Background panning is tied to normalized bearing so drag motion feels connected to the optics.
- The horizon ratio is fixed at `0.45`, matching the generated sea plate and Mk I visual composition.
- Scout scale still comes from existing range projection.
- Wake rendering is intentionally light and non-physical; it is a depth cue, not a fleet simulation.
- Atmospheric effects are generated in Canvas so the experience remains self-contained.

## Known Limitations

- All visible scouts currently share one prototype sprite.
- The panoramic background is not a true seamless 360-degree environment.
- Alpha cleanup is acceptable for prototype scale but should be refined before close-up presentation.
- Distant blur is simulated with Canvas `filter`; older browsers may ignore it and fall back to a sharper sprite.

## Recommended Next Sprint

Create a small asset foundry pass with three scout-specific sprite variants, one optimized background plate, and documented export settings. Then tune range-specific visibility, wake strength, and label placement against those final assets.
