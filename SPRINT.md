# Instructions: Commander Claude — FleetCore Command Center v0.1

**New layer, not another toy. Sits above Bridge Station, drives FleetCore through its own official contracts — never touches state directly.**

```
FleetCore Command Center   ← world administration (new)
        ↓
Scenario / world configuration
        ↓
FleetCore authoritative state   ← truth (existing)
        ↓
Bridge, Fleet Motion, Periscope, Radio   ← in-world command (existing)
```

## v0.1 Scope — Small and Real
1. **One scenario only.** Recommend "Mumbai Harbor Departure" — pilot launch, tugs, outbound traffic, radio coordination. It fits the world data you already have (Mumbai references exist in Periscope Station).
2. **Three operations, nothing more:**
   - **Preview** — show what the scenario will set up (starting vessels, region, time, weather) before committing
   - **Launch** — instantiate the world through FleetCore's existing API/write contract. Do not write to any database or state store directly — if FleetCore doesn't yet expose a "load scenario" endpoint, that's a small addition to FleetCore's contract, not a bypass around it.
   - **Reset** — return to a clean starting state, same way: through the contract, not a manual wipe.
3. **Scenario manifest format** — a simple config (JSON/YAML) describing region, time, vessels/routes/schedules, weather, traffic density, sim speed. Keep it data, not code — the manifest describes a world, it doesn't script one.

## Explicitly Out of Scope
- No general slider panel — no arbitrary live-tunable parameters. This is not a god-panel.
- No second or third scenario yet — prove the pattern with one before templating it.
- No incident/trigger-condition system yet, no victory/completion criteria yet — those are later refinements once Preview → Launch → Reset is solid.
- No changes to Bridge, Fleet Motion, Periscope, or Radio to support this — Command Center is a new consumer of FleetCore, not a reason to touch instruments that already work.

## Hard Rule
Command Center talks to FleetCore the same way Bridge Station does — through official contracts. If a needed capability doesn't exist in FleetCore yet (e.g. scenario loading), that's a small, explicit addition to FleetCore's API, proposed and reasoned about the same way the WebSocket telemetry work was — not a shortcut into the database.

## Sequencing
This runs alongside, not instead of, the current Fleet Motion → FleetCore integration work. Don't let Command Center development pull focus from finishing that. If FleetCore's write contract isn't ready to support "launch a scenario" cleanly yet, Command Center can build its Preview UI against mock data first — same pattern as every other instrument's MOCK state.

## Reporting
Standard Ship's Log. Flag the moment Command Center needs any new capability from FleetCore that doesn't exist yet — that's a design decision worth naming explicitly, not something to add quietly.
