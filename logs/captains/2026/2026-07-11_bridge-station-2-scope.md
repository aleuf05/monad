# Bridge Station 2.0 Watch Log

Date: 2026-07-11
Operator: Commander Claude, Engineering Watch
Scope packet (verbatim, as received):

> # Bridge Station 2.0 — Scope
>
> ## Objective
> Replace the current tab-switched collection of toys with a single, coherent landing experience. One page, one view, not half a dozen separate instruments a visitor has to click between.
>
> ## What This Replaces
> The current Bridge Station pattern of separate toys (Fleet Motion, Periscope, others) living behind tabs/iframes, each feeling like a standalone demo rather than one unified system.
>
> ## Core Idea
> Fleet Motion and Periscope observing the *same* live world simultaneously, composited into one view — not two apps sharing a nav bar. The coherence itself is the pitch: this is what makes Monad look like a unified system instead of a pile of browser experiments.
>
> ## In Scope
> - Single-page layout compositing Fleet Motion + Periscope into one simultaneous view
> - Shared state source — both views render from the same live data, proving the "every instrument observes the same world" principle in the UI itself
> - Lean by default: cut anything that doesn't serve the core view (extra toys, redundant nav, tab-switching UI)
>
> ## Out of Scope (for now)
> - Additional toys beyond Fleet Motion + Periscope
> - Write/command authority from this view (read-only observer, matches toy default)
> - Deciding yet whether this is internal-facing or public-facing — worth a quick call before visual/copy work starts, but doesn't block the compositing work
>
> ## Dependency Check
> This can be built two ways depending on where FleetCore API 1.0 stands:
> - **If FleetCore's read API is ready:** both Fleet Motion and Periscope pull from it directly — this becomes the first real proof of the API contract.
> - **If not ready yet:** build the compositing/UX work now against existing mock/local state, swap the data source once the API lands. Keeps this deliverable unblocked either way.
>
> ## Deliverables
> 1. Single landing page, one simultaneous view (not tabs)
> 2. Fleet Motion and Periscope composited together, sharing one state source
> 3. Stripped-down nav/UI — nothing extraneous competing with the core view
>
> ## Success Check
> A first-time visitor lands on one page and immediately sees a live, coherent world — not a menu of experiments to explore.

## Reconciling scope against current state

The packet's "What This Replaces" describes Fleet Motion and Periscope as still living behind separate tabs — that was already fixed by the Bridge Mk III sprint (composited side-by-side in one Live Console). What's actually new in this packet is narrower and sharper than "composite them": **a single page with nothing else on it** ("Out of Scope: Additional toys beyond Fleet Motion + Periscope," "nothing extraneous competing with the core view"), which the current `toys/bridge/` doesn't satisfy — it now also carries Radio Console, a Watchbook tab, an engineering sidebar, and standalone links.

Two real decisions were open before writing any code, both resolved with the operator directly rather than assumed:

1. **Redesign `toys/bridge/` in place, or build separately?** → Build separately. The existing Bridge Station stays exactly as-is; this is a new artifact, `toys/bridge-2/`.
2. **Data source, given FleetCore's read API exists but nothing has ever consumed it?** → Wire the real integration now, not the local-state fallback the packet itself explicitly permits. This page has no local simulation at all — it renders live `WorldSnapshot` data from `fleetcore-serve` directly.

## Integration

- New toy at `toys/bridge-2/`: `index.html`, `app.js`, `style.css`, `README.md`. No iframes, no reuse of `toys/fleet-motion/` or `toys/periscope/` source — a from-scratch renderer for both panels, sharing a single WebSocket connection and a single `state.snapshot` object.
- Map panel: Leaflet, one marker per vessel from the live snapshot, positioned and colored by `kind` (flagship/scout/passive-traffic) — same visual language as `toys/fleetcore-live/`'s map for consistency across Monad's live-data toys.
- Optics panel: canvas-drawn bearing/horizon view, computed from the *same* snapshot object the map just rendered — bearing and range to every non-flagship vessel via `window.MonadFleetState.utils.bearingDegrees`/`distanceKm` (reused from `toys/shared/fleet-state.js`, which already exposed these as pure geometry functions independent of the localStorage contract they were originally built for). Drag-to-rotate with simple momentum decay, matching Periscope's established interaction feel.
- Deliberately no photographic sea-plate or vessel sprite assets (`toys/periscope/`'s Mk2/Mk3 visual investment) — flat gradient sky/sea and colored dots, matching "lean by default." This keeps the page's only asset dependency on the Leaflet CDN tiles and `toys/shared/fleet-state.js`.
- Read-only: connects to `/ws` without a `?token=`, never constructs or sends a `Command`. No pause/resume/time-scale controls exist in this UI at all — a stricter read-only stance than `toys/fleetcore-live/`, which does have (auth-gated) write controls.

## Caught during verification: label collision, twice

First pass had contact labels in the optics panel rendered in snapshot order (vessel id, alphabetical) rather than screen position, so two contacts close in bearing after a drag produced fully overlapping, unreadable text — caught from an actual screenshot after dragging the view, not from reading the code. Fixed by sorting visible contacts by screen x and staggering rows for anything within a collision threshold.

The first threshold/row-height combination (95px threshold, 34px row spacing) looked staggered but still overlapped: the vertical gap between one row's range-below-dot text and the next row's name-above-dot text was only ~2px, because row spacing (34px) was smaller than the combined offsets those two text draws already use (12px above + 20px below = 32px). Increased row spacing to 46px, which gives the labels honest clearance — verified in a follow-up screenshot showing three fully distinct, non-overlapping rows for three vessels within 5° of the same bearing.

## Verification

`node --check` on `app.js`. Playwright against a local server pointed at the actual running `fleetcore-serve` process (read-only, no token) at both 1400×900 and 390×844: link status reaches "Live," 8 map markers render matching the live seed world (flagship + 3 scouts + 4 passive contacts), the optics canvas renders non-empty content, dragging changes the bearing readout and visibly rotates the contact scale, no horizontal overflow on mobile. Zero console errors across every run. (Playwright's network listener flagged several `tile.openstreetmap.org` requests as "failed" — confirmed via screenshot that these are normal Leaflet tile-abort-on-pan noise, not real failures; the map tiles render correctly.)

## Follow-up

Not deployed anywhere — the packet's own "Out of Scope" explicitly leaves internal-vs-public undecided, and this watch didn't resolve it. If it goes public, the same pending step from FleetCore Live's deployment applies: a Caddy reverse-proxy block for `fleetcore-serve`'s WebSocket (still loopback-only, still running ad hoc rather than via the `scripts/fleetcore-serve.service` systemd unit — neither has changed since that watch log).
