# FleetCore Replay

Replay is FleetCore v1's primary proof.

The guarantee:

```text
same seed world + same ordered events = same final snapshot
```

## Replay Inputs

- Seed world: `fleetcore/data/seed-world.json`
- Event log: `data/fleetcore/events.jsonl`
- Deterministic code version

## Replay Output

Replay rebuilds a world from seed plus events and compares its final browser-facing snapshot with the current saved world snapshot.

The CLI command:

```sh
cargo run --manifest-path fleetcore/Cargo.toml -- replay
```

Expected success:

```text
replay matched: N events, tick T
```

## Automated Test

The integration test is:

```sh
cargo test --manifest-path fleetcore/Cargo.toml
```

The test:

1. Loads the seed world.
2. Applies a fixed command sequence.
3. Advances deterministic ticks.
4. Appends each event to JSONL.
5. Reloads the seed.
6. Replays every event.
7. Compares final snapshot JSON exactly.

## What Replay Proves

Replay proves:

- commands are serializable,
- events are ordered,
- fixed ticks are deterministic,
- route progression is reproducible,
- snapshot export is stable for the same world state.

## What Replay Does Not Yet Prove

Replay v1 does not yet prove:

- cross-platform floating-point identity across every CPU and compiler,
- long-duration drift behavior,
- concurrent command intake,
- database recovery,
- network synchronization,
- browser rendering correctness.

Those are future concerns. FleetCore v1 proves the local deterministic core first.

## Operational Recovery

Current recovery strategy:

1. Load `world.json` for current operation.
2. Use `events.jsonl` plus seed for replay validation.
3. Use checkpoint files as inspectable recovery artifacts.

Future recovery should support:

- latest valid checkpoint selection,
- replay events after checkpoint,
- snapshot hashing,
- checkpoint manifest.

## Known Limitation

FleetCore v1 writes a checkpoint after every mutating command. That is simple and inspectable, but not efficient. A later version should checkpoint by cadence, for example every 1000 ticks or after significant command bursts.
