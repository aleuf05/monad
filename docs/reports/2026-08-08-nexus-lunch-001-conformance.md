# NEXUS-LUNCH-001 — Nexus Composition Contract conformance

**Date:** 2026-08-08
**Order:** NEXUS-LUNCH-001, Admiral, execute-now
**Result:** **PASS** — 13/13 conformance tests, plus 26/26 in the two reused components.
**Scope note:** implementation experiment only. No deployment, no network,
no auth/credential changes, no canon, doctrine, or policy edits.

## What was built

One seven-field envelope and two adapters. Nothing else.

```text
Identity → Intent → Authority → Capability → Action → Result → Evidence
```

The envelope lives in `tools/nexus-contract/nexus_contract.py`. It is not a
bus, router, or store — Monad already has those, and this experiment reuses
them rather than growing a parallel subsystem.

## The two components

The success condition requires *two independently represented* components.
Both already existed in the repo, were written for unrelated reasons, share
no code, and share no data representation. Neither knows Nexus exists.

| | Component | Native representation |
|---|---|---|
| **A — sender** | `tools/engineering-comms/schema.py` | `@dataclass EngineeringMessage`, with its own authority vocabulary (`lieutenant/captain/admiral/engineering/unspecified`) |
| **B — receiver** | `tools/mission-bus/mission_bus.py` | append-only SQLite event log, immutability enforced by table triggers |

Nexus does not invent a permission model. Component A's authority vocabulary
is *transported* into the Authority field, which is the point of the contract.

## The crossing

```text
EngineeringMessage → seal envelope → canonical JSON wire (706 bytes)
    → decompose into 3 native events → SQLite append-only record
    → fold events back → envelope → verify
```

Component B deliberately does **not** store the envelope whole. It writes
three events in its own schema — `mission_created`, `capability_invoked`,
`result_observed` — and reconstruction folds that log back into an envelope.
A stored blob would have proven only that SQLite can hold a string; there is
a test asserting the decomposition actually happens.

## Evidence is a check, not a claim

The Evidence field carries `sha256` over the other six fields (evidence
cannot cover itself). A receiver recomputes it on arrival. So "evidence
reconstructs the operation" is something the code verifies, not something the
document asserts about itself. `sealed()` always computes the digest and
never accepts one from the caller — a self-declared digest proves nothing.

## Observed output (run 1, verbatim)

```
identical: True
digest: sha256:e5d9a662c20b16ebcb4134bd644fa09be0b80a0a09361ad741d7e80e47b48409
events: ['mission_created', 'capability_invoked', 'result_observed']
wire_bytes: 706
event_ids: ['missionevent.09c48232653c594e', 'missionevent.4c0709283c6f2c90',
            'missionevent.62aa68f6c7a61e39']
```

Chain reconstructed by Component B **from its own storage alone**:

| Question | Reconstructed value |
|---|---|
| who acted | `captain.claude` (kind: agent) |
| what was intended | "Seven-field envelope crosses two components and reconstructs." |
| what authority permitted it | grant `admiral`, scope `engineering-queue` |
| what capability was invoked | `nexus-contract` v0.1 |
| what action occurred | `scaffold` → `tools/nexus-contract/nexus_contract.py` |
| what result occurred | `succeeded` |
| what evidence reconstructs it | `sha256:e5d9a662…8409`, refs → the test file |

`digest_sent == digest_reconstructed`, and the full dataclass comparison is
equal — the envelope survived the representation change byte-identically.

## Stability

- **Deterministic.** Two runs produced byte-identical JSON output (`diff` clean).
  No timestamps or random IDs enter the envelope.
- **Idempotent.** Re-running against the same record left **3 rows, not 6** —
  Component B derives event IDs from content and dedupes.
- **Append-only holds.** `DELETE` and `UPDATE` against the stored events both
  raise; asserted in test, not assumed.
- **Fails loudly.** A truncated crossing raises rather than returning a
  plausible envelope with fields quietly missing.

## Tests

```sh
python3 -m unittest discover -s tools/nexus-contract    -p 'test_*.py'   # 13 OK
python3 -m unittest discover -s tools/engineering-comms -p 'test_*.py'   # 17 OK
python3 -m unittest discover -s tools/mission-bus       -p 'test_*.py'   #  9 OK
```

Reproduce the exchange directly:

```sh
python3 tools/nexus-contract/nexus_contract.py --db /tmp/nexus-demo.sqlite3
```

## Two real defects found and fixed during the run

Both were in the new code, both caught by the tests rather than by reading.

1. **Empty `evidence.refs` was rejected.** Validation tested truthiness, so
   `refs: []` — a legitimate "no external references" — read as absent. Now
   checks presence; only `None` and blank strings count as missing.
2. **Uncatchable exceptions.** The by-path module loader re-executed
   `engineering-comms/schema.py` on every call, minting a fresh
   `ValidationError` class each time. A caller writing
   `except engcomms.ValidationError` would have failed to catch the error
   just raised — same name, different class object. The loader now caches.

## Remaining technical uncertainty

- **Digest covers content, not origin.** Anyone can seal a well-formed
  envelope. It detects tampering in transit, not impersonation. Binding
  Identity to a signer would need credential work, which this order
  explicitly walls off.
- **The `EVENT_MAP` split is one choice, not the choice.** Three events was
  the smallest decomposition that still proved the point. A different
  receiver would split differently, and the contract has nothing to say
  about that — which may be correct, or may be an underspecification that
  only shows up with a third component.
- **Two components, one crossing.** Conformance is demonstrated, not
  generalized. A third component with a genuinely different authority
  vocabulary is the next real test.
- `tools/nexus-contract/` is untracked; committing it is a separate step,
  not taken under this order.
