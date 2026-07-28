# Durable Kraken — Milestone 1

Date: 2026-07-28

Status: complete

Live URL: `https://cameronlampley.com/toys/periscope/`

## Result

The real Tripo blue Kraken is:

- clearly framed at bearing 000°;
- textured and lit;
- selected and tracked on initial load;
- selected and tracked again after reload;
- described by `toys/periscope/creatures.json`;
- loaded through the reusable resolver in `toys/periscope/creatures.js`.

The source and deployed Periscope trees contain matching manifest and loader
implementations. The only deployment-specific manifest difference is the
relative asset path required by their different filesystem locations.

Screenshot:
`docs/reports/assets/2026-07-28-durable-kraken-milestone-1.png`

## Live evidence

Headless Chromium observed:

- `creatures.json`: HTTP 200;
- `kraken_tripo_v1.glb`: HTTP 200;
- `KRAKEN — NEW`: in field and selected;
- detail panel: `Tripo Blue Kraken`;
- bearing: 000°;
- the same selected contact and panel after a full page reload;
- no console errors, page errors, or failed requests.

## Truth boundary

The creature manifest owns presentation metadata: model path, render
transform, enablement, and contact label. Its current position is explicitly
reported in the UI as `Presentation-staged 3D contact`.

FleetCore does not yet assert that the Kraken exists. Moving existence,
position, motion, and state into FleetCore is Milestone 2. Periscope will then
consume those facts and keep only render metadata in the creature manifest.
No claim of FleetCore ownership is made in Milestone 1.

## Reusability

Adding another staged creature no longer requires another bespoke JavaScript
loader. A manifest entry supplies identity, display name, model path,
enablement, position, rotation, scale, and contact label. The generic loader
caches, centers, rotates, scales, and resolves any enabled model.
