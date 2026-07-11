# Bridge Station Architecture

Bridge Station Mk I is a composition layer. It proves that Monad's independent instruments can be presented as one command deck without rewriting those instruments.

## Philosophy

The Bridge is not a dashboard. It is a command surface for a vessel.

The layout should communicate:

- one ship,
- multiple instruments,
- one operational picture,
- disciplined engineering boundaries.

## Composition Model

Mk I composes existing instruments with static iframes:

```text
toys/bridge/
  index.html
  style.css
  app.js

embedded instruments:
  ../fleet-motion/
  ../periscope/
  ../watchbook/
```

This keeps each instrument independently useful and avoids coupling Bridge Station to their internal DOM, rendering loops, or control logic.

## Shared Operational Picture

Bridge Station reads Fleet Motion's current browser-local state from:

```text
localStorage["monad.fleetMotion.state"]
```

This state is authored by Fleet Motion and observed by the Bridge. Bridge Station does not write to it.

Current observed fields:

- flagship position,
- route leg count,
- waypoint count,
- passive contact count,
- time warp,
- motion status,
- last navigation message.

This is practical shared-state observation, not full integration. Periscope still uses its local contacts until the Mk IV shared-state extraction proposed in `toys/periscope/mk3/` is implemented.

## Why Iframes

Iframes are deliberate for Mk I:

- existing instruments remain standalone,
- rendering contexts stay isolated,
- Fleet Motion's Leaflet map is not rehosted or rewritten,
- Periscope's Canvas 2D rendering stays untouched,
- Watchbook keeps its own manifest and log loading behavior.

The cost is limited cross-instrument communication. That is acceptable for Mk I because the sprint objective is composition.

## Engineering Status Panel

The Engineering Status panel is Bridge-owned. It reports real local application state where practical and uses honest placeholders otherwise.

It currently shows:

- current sprint,
- branch,
- runtime mode,
- commander status,
- observed Fleet Motion state,
- route summary.

The commit field is a static runtime placeholder because a static page has no direct Git metadata unless a build step writes it.

## Future Expansion Points

Recommended Mk II:

1. Add `toys/shared/fleet-state.js`.
2. Move pure Fleet Motion state schema helpers into the shared layer.
3. Let Bridge Station, Periscope, Radar, and future status boards read a shared contract.
4. Keep Fleet Motion as the state writer.
5. Replace iframe-only status coupling with explicit shared-state adapters.

Future instruments can join the Bridge as additional framed panels first, then graduate to shared-state consumers when their contracts stabilize.

## Non-Goals

- No backend.
- No database.
- No authentication.
- No multiplayer.
- No WebGL migration.
- No visual redesign of Fleet Motion, Periscope, or Watchbook.
- No direct Fleet Motion to Periscope runtime coupling in Mk I.
