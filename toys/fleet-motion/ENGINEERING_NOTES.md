# Fleet Motion Engineering Notes

## Iteration 1: Motion Feel

Fleet Motion uses a lightweight browser-only interpolation model.

Position still moves along straight route legs, but speed no longer jumps directly to the time-warp target. Instead, the simulation keeps a `currentSpeedKmh` value and eases it toward a target speed using exponential smoothing:

```text
alpha = 1 - exp(-elapsedSeconds / responseSeconds)
currentSpeed += (targetSpeed - currentSpeed) * alpha
```

The target speed is reduced near the end of each leg using `smoothstep`, which creates a visible deceleration before arrival.

Heading is smoothed separately. Each frame computes the desired bearing to the active leg destination, then eases the displayed heading along the shortest angular turn. This prevents the visible heading indicator and telemetry from snapping instantly at route changes.

The model is intentionally not a physics simulation. It is a small visual-quality layer over the existing waypoint route system.

## Performance Notes

Marker icons now include a visible heading indicator. To avoid unnecessary DOM churn, marker icons are only re-rendered when the rounded heading or selected ship changes.

No backend, package manager, build system, or external simulation dependency was added.

## Iteration 2: Wake Polish

Wake trails are rendered as bounded segment layers instead of one flat polyline per ship.

Each vessel keeps a capped list of recent positions. When a new trail point is added, only that vessel's wake layer is rebuilt. Older segments use lower opacity and thinner stroke weight; newer segments are brighter and wider. This creates a simple tapered/fading wake without adding canvas rendering, shaders, external libraries, or a separate animation system.

The flagship wake uses the gold command accent. Escorts use cyan. All wake segments keep rounded caps and the existing glow treatment.

The tradeoff is that a fast-moving route can temporarily create more SVG path elements than the previous flat-line implementation. The trail cap keeps this bounded, and redraws are tied to new trail points rather than every animation frame.

## Iteration 3: Visual Identity

The presentation pass keeps the existing simulation and controls intact while making the surface feel more intentional.

Changes are CSS-first:

- command header now carries compact operational context chips
- page background uses a restrained chart-grid texture
- telemetry and ship detail cells have consistent borders and density
- status panel uses a stronger command-console surface
- controls have clearer active, hover, and disabled states
- spacing and text hierarchy are tightened across desktop and mobile

No new simulation features were added in this iteration.

## Iteration 4: Independent Escort Motion

Escorts now keep independent position, speed, heading, and blocked-state values.
They are no longer rendered as `flagship + fixed offset` every frame.

Each escort chases a nearby formation slot around MONAD. The slot has a small
deterministic drift component so escorts visibly work to keep station instead of
appearing welded to the flagship. Before accepting a slot, the escort checks the
same rough rectangular land boxes used by the route planner. If the primary slot
is blocked, it tries a small set of nearby alternate slots; if all are blocked,
the escort eases to a hold.

This is deliberately not independent global pathfinding. It is a lightweight
motion-quality step that makes the fleet feel more alive while preserving the
browser-only architecture.

## Iteration 5: Escort Screen Modes

The escort model now exposes three operator-visible screen modes:

- Tight Screen
- Loose Screen
- Patrol Weave

Each mode adjusts escort drift scale, acceptable slot radius, and catch-up speed.
This gives the operator a visible control over how tightly the screen works
around MONAD without introducing a tactics engine.

Faint formation links now draw from MONAD to each escort. These are intentionally
display aids, not physical constraints. They make it easier to see that escorts
are moving independently while still belonging to the same screen.

## Iteration 6: Route Editing

Waypoint routes can now be edited after staging. The operator can undo the newest
waypoint, click a waypoint marker to select it, remove the selected waypoint, and
cancel an active route while keeping MONAD at its current position.

After waypoint edits, the remaining staged waypoint legs are checked again
against the existing rectangular land boxes. If an edit creates an invalid direct
leg, the route is marked blocked and the blocked segment is shown.

This keeps manual planning forgiving without adding automatic pathfinding or a
larger route graph.
