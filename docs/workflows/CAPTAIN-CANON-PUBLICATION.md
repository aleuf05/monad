# Captain Canon Publication Workflow

The Admiral does not manage Git. The Captain owns the publication seam for
durable process documentation.

## Automatic sequence

```text
meeting event
  → append Wardroom ledger
  → update readable meeting/canon record
  → validate explanations and provenance
  → stage only canonical documentation
  → commit with a descriptive message
  → push the active branch
  → report the resulting state in plain language
```

The Wardroom Clerk supplies the packet step directly:

```bash
python3 tools/wardroom/wardroom.py \
  --ledger data/wardroom/<meeting>.jsonl \
  export \
  --output docs/wardroom/meetings/<meeting>.packet.md
```

The exported packet is the handoff artifact: it combines meeting purpose,
Captain readback, current and historical rulings, actions, gates, and the
evidence trail in one human-readable file.

The standard post-meeting routine is now:

```bash
scripts/wardroom-continuity-pass.sh data/wardroom/<meeting>.jsonl \
  docs/wardroom/meetings/<meeting>.packet.md
```

This validates the Clerk before refreshing the packet.

## Publication boundary

The automatic documentation set is limited to:

- `docs/doctrine/`
- `docs/wardroom/`
- `docs/workflows/`
- `admiralty/archive/canon/`

Private incoming material, runtime data, credentials, experiments, and live
code remain outside automatic publication unless separately commissioned.

## Captain gate

The Captain pauses only when publication would expose private material, change
repository scope, publish to an unintended branch, or encounter a failed
verification. Ordinary commit and push mechanics are not returned to the
Admiral.
