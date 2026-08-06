# Mike's Variable-Exhaust Rocket Lab

A static, playable rendering of the core comparison in Mike's
[`mds2/rocketry`](https://github.com/mds2/rocketry) notebook.

## Status

**Captain's Reverie — unofficial preview.** Mike has not yet participated in,
reviewed, or endorsed this interpretation. The artifact remains deliberately
portable so he can later revise, reject, or publish it anywhere he chooses.

Version 1 deliberately includes only:

- inputs for initial mass, final mass, and specific energy;
- a synchronized burn-state control;
- constant and optimal exhaust schedules under the same ideal energy budget;
- live delta-v and exhaust-velocity plots;
- the final mass-ratio-only gain factor;
- explicit assumptions and URL-encoded shareable state.

No build step or backend is required. Open `index.html` through an HTTP server
or use the production path at `/toys/mike-rocketry/`.

The numerical inputs label mass in tonnes, specific energy in MJ/kg, and
velocity in km/s. Those unit choices are mutually consistent because
`1 MJ/kg = 1 km²/s²`.
