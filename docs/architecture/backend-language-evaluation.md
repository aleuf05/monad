# FleetCore Backend Language Evaluation

This document evaluates Rust, Go, C#, and C++ for FleetCore, the future canonical stateful world model for Monad.

The evaluation is against Monad's needs:

- deterministic execution,
- memory safety,
- operational reliability,
- dependency footprint,
- maintainability,
- debugging,
- Linux deployment,
- browser interoperability,
- long-term sustainability.

## Summary Recommendation

Recommended language: Rust.

Rust is the strongest long-term fit for FleetCore because it combines memory safety, low operational footprint, precise control over deterministic simulation code, excellent Linux deployment characteristics, and strong serialization/networking ecosystem support without requiring a large runtime.

Go is the strongest fallback if implementation speed and operational simplicity outweigh the need for strict memory and state modeling. C# is viable but brings a larger runtime and less natural fit for small static Linux deployment. C++ should not be selected unless FleetCore later requires specialized performance that Rust cannot provide.

## Evaluation Matrix

| Criterion | Rust | Go | C# | C++ |
| --- | --- | --- | --- | --- |
| Deterministic execution | Strong | Good | Good | Strong but fragile |
| Memory safety | Strong | Strong | Strong | Weak by default |
| Operational reliability | Strong | Strong | Good | Depends heavily on discipline |
| Dependency footprint | Low | Low | Medium | Low to medium |
| Maintainability | Good with discipline | Very good | Good | Risky over time |
| Debugging | Good, improving | Very good | Very good | Powerful but complex |
| Linux deployment | Excellent | Excellent | Good | Excellent but build-sensitive |
| Browser interoperability | Strong via JSON/WASM options | Strong via JSON/HTTP | Strong via JSON/HTTP | Possible but heavier |
| Long-term sustainability | Strong | Strong | Strong | Risky for small team |

## Rust

Strengths:

- Memory safety without garbage collection.
- Strong type system for world state, events, commands, and schema versions.
- Good fit for deterministic fixed-timestep simulation.
- Excellent serialization support through `serde`.
- Small single-binary Linux deployments.
- Can expose HTTP, WebSocket, file snapshots, or future WASM helpers.
- Encourages explicit ownership boundaries, which matches FleetCore's role as canonical truth.

Costs:

- Higher learning curve than Go or C#.
- Borrowing and lifetime constraints can slow early iteration.
- Async ecosystem choices require discipline.

Fit for FleetCore:

Rust is best where correctness, state integrity, and long service life matter more than fastest first implementation. FleetCore is exactly that kind of component.

Recommended Rust posture:

- Start with a synchronous deterministic core library.
- Keep async/network adapters outside the core.
- Use simple data structures first.
- Avoid macro-heavy framework design.
- Treat `serde` JSON as the initial browser contract.

## Go

Strengths:

- Simple language and fast development.
- Excellent Linux deployment as static-ish single binaries.
- Strong standard library for HTTP, JSON, logs, and services.
- Easy operational debugging.
- Good concurrency primitives.

Costs:

- Garbage collection can introduce latency variance, though likely acceptable for Monad's early scale.
- Type system is less expressive for strict domain invariants.
- Determinism requires careful avoidance of maps or nondeterministic iteration in simulation-critical paths.

Fit for FleetCore:

Go is a credible pragmatic choice if FleetCore begins as a small local service exposing snapshots over HTTP. It may be the fastest reliable implementation path.

Why not the primary recommendation:

FleetCore is meant to become the keel of the project. Rust provides stronger state modeling and long-term correctness guarantees for the canonical world.

## C#

Strengths:

- Mature language and runtime.
- Excellent tooling, debugging, profiling, and JSON support.
- Good cross-platform Linux support with modern .NET.
- Strong maintainability for teams familiar with object-oriented service design.

Costs:

- Larger runtime footprint than Rust or Go.
- Deployment can be simple, but less minimal.
- The runtime and ecosystem may be heavier than FleetCore needs at first.
- Long-term model can drift toward framework-shaped architecture if not constrained.

Fit for FleetCore:

C# is viable if Monad later wants rich tooling, extensive service infrastructure, or a team already invested in .NET. It is not the best first choice for a small deterministic core.

## C++

Strengths:

- Maximum control over memory, performance, and runtime footprint.
- Mature toolchains and libraries.
- Strong fit for deterministic simulation in experienced hands.

Costs:

- Memory safety burden remains high.
- Undefined behavior risk is unacceptable for canonical state unless engineering controls are very mature.
- Build systems and dependency management can become expensive.
- Long-term maintainability risk is high for a small evolving project.

Fit for FleetCore:

C++ is not recommended for Mk I FleetCore. It solves problems Monad does not yet have and introduces risks that Rust avoids.

## Browser Interoperability

All four languages can serve browsers through JSON over HTTP, event streams, WebSockets, or generated static snapshots.

The browser contract should remain language-neutral:

- JSON snapshots,
- JSON events,
- schema version fields,
- stable entity IDs,
- explicit units,
- no language-specific serialized objects.

This keeps Fleet Motion, Periscope, and Bridge independent of the FleetCore implementation language.

## Final Recommendation

Choose Rust for FleetCore's core domain engine.

Recommended split:

```text
fleetcore-core      deterministic world model, no networking
fleetcore-storage   snapshots and append-only event log
fleetcore-api       optional local HTTP/event-stream adapter
fleetcore-tools     replay, validation, snapshot export
```

The first implementation sprint should not begin with a web server. It should begin with a small Rust core that can:

1. load a seed world,
2. run fixed deterministic ticks,
3. emit a JSON snapshot,
4. replay from an event log to the same snapshot.

That proves FleetCore's central promise before adding operational surface area.
