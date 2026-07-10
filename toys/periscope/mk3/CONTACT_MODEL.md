# Shared Contact Model

The shared contact model should describe vessel truth first and display-specific projection second.

Fleet Motion should publish position, heading, speed, and operational state. Periscope should derive observed bearing and range from that state relative to MONAD.

## Contact Schema

Schema name: `monad.scoutContact.v1`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "monad.scoutContact.v1",
  "title": "Monad Scout Contact",
  "type": "object",
  "required": ["id", "callsign", "class", "bearing", "range", "lastUpdate", "confidence"],
  "properties": {
    "id": {
      "type": "string",
      "description": "Stable machine identifier for the vessel."
    },
    "callsign": {
      "type": "string",
      "description": "Operator-facing callsign."
    },
    "class": {
      "type": "string",
      "description": "Vessel class or role, for example scout, escort, flagship, relay."
    },
    "mission": {
      "type": "string",
      "description": "Short current mission label."
    },
    "status": {
      "type": "string",
      "description": "Short operational state."
    },
    "report": {
      "type": "string",
      "description": "Human-readable latest report for detail panels."
    },
    "latitude": {
      "type": ["number", "null"],
      "minimum": -90,
      "maximum": 90,
      "description": "Future geospatial latitude."
    },
    "longitude": {
      "type": ["number", "null"],
      "minimum": -180,
      "maximum": 180,
      "description": "Future geospatial longitude."
    },
    "bearing": {
      "type": "number",
      "minimum": 0,
      "exclusiveMaximum": 360,
      "description": "Observed bearing in degrees relative to north."
    },
    "range": {
      "type": "number",
      "minimum": 0,
      "description": "Observed range in nautical miles."
    },
    "course": {
      "type": ["number", "null"],
      "minimum": 0,
      "exclusiveMaximum": 360,
      "description": "Vessel course over ground in degrees."
    },
    "speed": {
      "type": ["number", "null"],
      "minimum": 0,
      "description": "Vessel speed in knots."
    },
    "lastUpdate": {
      "type": "string",
      "format": "date-time",
      "description": "UTC timestamp for this contact snapshot."
    },
    "confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "Confidence in this contact state."
    },
    "source": {
      "type": "string",
      "description": "State producer, for example fleet-motion, demo-fallback, replay."
    }
  },
  "additionalProperties": true
}
```

## Example Contact

```json
{
  "id": "escort-alpha",
  "callsign": "SCOUT ALPHA",
  "class": "scout",
  "mission": "Research Sweep",
  "status": "Nominal",
  "report": "Maintaining assigned observation pattern.",
  "latitude": 26.48,
  "longitude": 56.11,
  "bearing": 24,
  "range": 7.3,
  "course": 271,
  "speed": 37,
  "lastUpdate": "2026-07-10T22:00:00Z",
  "confidence": 0.92,
  "source": "fleet-motion"
}
```

## Mapping From Fleet Motion

Fleet Motion currently stores:

- flagship position,
- flagship heading,
- flagship speed in km/h,
- escort positions,
- escort headings,
- escort speeds in km/h,
- escort blocked state,
- active route and escort mode.

Adapter responsibilities:

- Convert `escort-alpha` to `SCOUT ALPHA`, and similarly for Bravo and Charlie.
- Convert km/h to knots if the contact contract uses nautical units.
- Compute bearing from MONAD position to escort position.
- Compute range from MONAD position to escort position in nautical miles.
- Carry heading as `course`.
- Set `confidence` to `1` for simulated authoritative state.
- Preserve local Periscope reports until Fleet Motion publishes richer mission text.

## Periscope Consumption Shape

Periscope should accept the shared contact shape and adapt it to its existing renderer:

```js
{
  id,
  name: callsignTitleCase,
  callsign,
  mission,
  status,
  report,
  color,
  bearing,
  range,
  course,
  speed,
  confidence
}
```

The existing `projectContact()` function can remain responsible for:

- field-of-view filtering,
- x/y projection,
- range scaling,
- visibility state.

## Contract Principles

- Keep the shared contact model display-neutral.
- Do not embed Periscope-specific fields like `x`, `y`, `scale`, `relative`, or `visible`.
- Do not embed Fleet Motion UI fields like selected marker, route controls, or Leaflet layer state.
- Allow `additionalProperties` so future instruments can add non-breaking fields.
- Version the schema before changing meanings or units.
