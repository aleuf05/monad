# Reaction-Diffusion Painter

A small single-page web toy for painting chemical seeds into a living Gray-Scott reaction-diffusion field. Drag or touch the canvas to add chemical B and watch spots, stripes, coral forms, and labyrinths evolve.

## Run

Open `index.html` directly in a modern browser. No server, install step, build step, package manager, account, or network access is required.

## Main Controls

- **Pause / Resume** stops and restarts simulation stepping. Painting still changes the visible field while paused.
- **Reset** clears the field, adds fresh seeds, and resumes unless the simulation was intentionally paused.
- **Randomize** keeps the current parameters and replaces the field with new seed regions.
- **Preset** applies named feed/kill values and reseeds the field.
- **Feed** and **Kill** change the Gray-Scott parameters immediately.
- **Brush size** changes the circular seed brush radius in simulation cells.
- **Speed** controls how many simulation steps run per animation frame.

## Model

The toy implements a two-chemical Gray-Scott system. Each cell stores concentrations `A` and `B`; diffusion spreads both chemicals, `A * B * B` converts A into B, feed restores A, and kill removes B. The simulation uses double-buffered `Float32Array` grids so each step reads from the current field and writes into a separate next field.

## File Structure

```text
reaction-diffusion-painter/
├── index.html
├── styles.css
├── app.js
└── README.md
```

## Implementation Choices

- Canvas 2D only, with no external assets or libraries.
- The visible canvas is device-pixel-aware, while the chemical grid runs at a lower resolution for performance.
- Edges wrap toroidally during the Laplacian calculation, avoiding hard border artifacts.
- Rendering maps chemical concentration to a restrained dark, cyan, pale-blue, and amber palette.
- Resizing may rebuild and reseed the simulation grid when the required internal resolution changes materially.

## Known Limitations

- The current image is not saved after reload.
- There is no export feature.
- Very old browsers without Pointer Events are not targeted.
- Large high-DPI displays are capped internally to keep animation responsive.
