# Context Steward v0

Context Steward produces a compact, deterministic projection of the current
course. Repository sources cited by `docs/context/checkpoint-input.json`
remain authoritative.

## Checkpoint

```bash
scripts/context-checkpoint
```

This refreshes:

- `docs/context/current-brief.md`
- `docs/context/current-state.json`
- `docs/context/continuation.md`

Create an immutable milestone archive explicitly:

```bash
scripts/context-checkpoint --archive continuous-umap-passage
```

The tool refuses missing required sections, missing source paths, and likely
secrets. It excludes disposable repetition from all generated prose, retains
only a count in structured state, reports budget-driven optional omissions,
and never changes its cited sources.

## Test

```bash
python3 -m unittest tools/context-steward/test_context_steward.py
```
