# FleetCore Architecture Study Mk I Engineering Report

## Summary

FleetCore Architecture Study Mk I defines the proposed canonical stateful world model for Monad.

The study concludes that FleetCore should become a persistent deterministic simulation service that owns world truth while browser instruments remain display and interaction surfaces.

The recommendation is to design FleetCore around a Rust deterministic core, JSON snapshots, append-only event logs, fixed simulation ticks, and incremental migration from the current browser-local Fleet Motion state.

## Created Artifacts

- `docs/architecture/fleetcore.md`
- `docs/architecture/backend-language-evaluation.md`
- `docs/architecture/simulation-model.md`
- `docs/architecture/migration-plan.md`
- `docs/architecture/engineering-report.md`

## Modified Artifacts

None outside `docs/architecture/`.

## Validation Performed

- Inspected current Fleet Motion, Bridge Station, and Periscope Mk III architecture documentation.
- Verified current repository branch and working tree before writing documents.
- Reviewed documents for internal consistency across:
  - FleetCore responsibility boundary,
  - language recommendation,
  - simulation clock model,
  - persistence strategy,
  - browser interface,
  - migration sequence.
- Confirmed the study does not require runtime code, networking, database, browser UI, or rendering changes.

## Key Findings

- FleetCore should answer: "What is true right now, even if no browser is open?"
- FleetCore should own world truth, event history, deterministic ticks, persistence, and snapshots.
- Browsers should render and observe; they should not own canonical state once FleetCore exists.
- Rust is the recommended implementation language for the core.
- Go is the practical fallback if implementation speed becomes more important than strict state modeling.
- JSON snapshots and JSONL event logs are sufficient for the first implementation.
- A database should be deferred until query, scale, or deployment needs justify it.
- The next implementation step should still be shared browser-state extraction, not FleetCore code.

## Open Architectural Questions

- What exact schema name should replace the current `monad.fleetMotion.state` browser-local shape?
- Should FleetCore express speed canonically in km/h, m/s, or knots?
- Should early ports and harbors be static entities or loaded from separate scenario files?
- What is the first command interface: CLI, local HTTP, or file-based command intake?
- How much event history should browser instruments receive by default?
- Should replay hashes include presentation-neutral derived fields or only core state?

## Recommended Next Implementation Sprint

Shared Fleet State Extraction Mk I.

Recommended scope:

1. Create `toys/shared/fleet-state.js`.
2. Move Fleet Motion schema constants and pure normalization helpers into the shared file.
3. Add a display-neutral contact adapter.
4. Update Bridge Station to read through the shared helper.
5. Update Periscope Station to consume shared contacts with local fallback.
6. Keep all toys static and independently runnable.

FleetCore implementation should wait until that shared contract has been exercised by multiple instruments.

## Known Limitations

- This sprint produced architecture documentation only.
- No FleetCore prototype was implemented.
- No language toolchain was installed or tested.
- No benchmark or runtime comparison was performed.
- The Rust recommendation is architectural, not based on repo-local prototype measurements.

## Commit And Push

The exact Git commit hash and push confirmation are recorded in the mission completion response. A commit cannot contain its own final hash without changing that hash.
