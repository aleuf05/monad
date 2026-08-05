# Doctrine 015 — Rust for the maths, Python for the I/O

**Authority:** Admiral cgl, 2026-08-05, direct chat: *"Rust for math
obviously"* and *"python only when performance not critical."*

Settled. Not open for re-litigation on taste grounds. What follows is the
measurement that supports it and the line the split actually falls on, so
that future work knows which side of the line it is on.

## The rule

- **Numeric kernels go in Rust.** Anything that touches every vertex,
  every triangle, or every element of a large corpus.
- **Python keeps everything else.** glTF parsing and writing, HTTP,
  orchestration, the console API, filesystem work — all of it I/O-shaped
  and measured in milliseconds regardless of language.
- **Python reference implementations stay** where a Rust kernel replaces
  one, and a parity test holds the two to identical output. A rewrite in a
  second language is only safe if something mechanical keeps them honest.

## The measurement

Taken 2026-08-05 on this corpus, same machine, same input, both engines
running union-find over the index buffer plus skeleton fit plus per-shell
weight solve. The Rust column includes the Python-side cost of packing the
arrays for the pipe, so it understates the gap:

| Asset | Vertices | Shells | Python | Rust | Speedup |
|---|---|---|---|---|---|
| `gasket.glb` | 29,378 | 395 | 136 ms | 22 ms | 6.2× |
| `the-monad.glb` | 315,157 | 4,676 | 1,515 ms | 228 ms | 6.6× |
| `kraken_tripo_v1.glb` | 1,076,978 | 1,831 | 5,793 ms | 799 ms | 7.2× |

Six seconds is a page that feels broken. Eight hundred milliseconds is a
button that feels like it worked. That is the whole argument, and it is
about the Admiral's experience of the live console, not about language
preference.

## Where the line falls, concretely

The rigging pipeline as built:

- **Rust** (`tools/aegis-rig/rust/`) — connected components, dominant-axis
  fit, slice centroids, per-shell rigid/blend decision, weight assignment,
  weight-sum validation.
- **Python** (`tools/aegis-rig/solver.py`) — GLB chunk splitting, accessor
  reading, buffer append, node/skin/scene construction, GLB writing.

The interface is a length-prefixed binary pipe over stdin/stdout, not
JSON. Handing 4.45M vertices across as JSON text would put the cost back
into the parsing the rewrite existed to avoid.

## The obligation that comes with a second language

`tools/aegis-rig/test_parity.py` runs both engines over the same input and
asserts they agree — shell counts, joint positions, every joint index,
every weight, and the sha256 of the written `.glb`. It includes a real
asset from the corpus, not only synthetic meshes, because synthetic parity
is easy and proves less.

It skips rather than fails when the Rust core is not built, so a checkout
without a toolchain still runs green on the Python path. That is
deliberate: the fallback has to keep working, or it is not a fallback.

One real finding from writing it: the pipe carries positions as f32,
because that is what glTF stores. A synthetic mesh built from Python f64
literals hands the two engines subtly different numbers and fails parity
for a reason that never occurs on a real asset. Quantise test inputs to
f32 first.

## Build

```
cd tools/aegis-rig/rust && cargo build --release
```

`target/` is gitignored. If the binary is absent the solver falls back to
Python and says so — the console prints the active engine in the corpus
summary, so which one is running is never a guess.
