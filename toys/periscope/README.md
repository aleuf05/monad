# Monad Periscope Station

A standalone, client-side observation station for Fleet Motion's Scout Flotilla.

Periscope is not a game, combat simulator, targeting interface, or networked service. It is a browser window into the current Monad operating world.

Mk II adds a photographic rendering prototype: a panoramic sea plate, atmospheric Canvas effects, and a transparent scout sprite while preserving the Mk I controls and data model.

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
- Select a visible scout contact, use the Details button, or select a scout card to open the vessel information panel.
- Use the Details button when a scout is visible in the field.

## Mk II Rendering

- The ocean background is loaded from `assets/backgrounds/sea-horizon-mk2.png` and panned by bearing.
- Scout contacts render with `assets/sprites/scout-alpha.png` when available.
- If image assets are missing, the station falls back to the Mk I procedural ocean and geometric contact glyphs.
- Mk II requirements, rendering notes, and asset pipeline guidance live in `mk2/REQUIREMENTS.md`.

## Boundaries

- No combat behavior.
- No weapon symbology.
- No backend, database, authentication, networking, or AI summarization.
- Static scout data and local simulation only for Mk I.

## Future Integration

The JavaScript is organized around vessel definitions, simulation, rendering, and UI update functions so a later Fleet Motion adapter can replace the local scout simulation with shared operational state.
