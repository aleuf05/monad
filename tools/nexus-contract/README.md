# Nexus Composition Contract — v0.1

One seven-field envelope that survives a crossing between two components
that share no code and no data representation.

```text
Identity → Intent → Authority → Capability → Action → Result → Evidence
```

Evidence carries a `sha256` over the other six fields, so the receiving side
*verifies* the chain it reconstructed rather than trusting it.

```sh
# run the exchange end to end
python3 tools/nexus-contract/nexus_contract.py --db /tmp/nexus-demo.sqlite3

# conformance tests
python3 -m unittest discover -s tools/nexus-contract -p 'test_*.py'
```

Sender is `tools/engineering-comms/schema.py`; receiver is the append-only
record in `tools/mission-bus/mission_bus.py`. Neither knows this module
exists — that is what makes the test meaningful.

Evidence and findings: `docs/reports/2026-08-08-nexus-lunch-001-conformance.md`.
