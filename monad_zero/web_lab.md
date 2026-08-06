# Monad-0 Web Laboratory

The web laboratory is a thin operator surface over the existing Python engine.
Monad's live site serves the operator page at
`/toys/monad0-lab/` and proxies its backend at `/monad0-lab-api/`. The
browser does not simulate resources, policies, contracts, or hypotheses; the
server owns those operations and exposes snapshots/events.

## Start

From the repository root:

```text
python3 -m monad_zero.web_lab
```

Open <http://127.0.0.1:8765>.

## Available operations

- create seeded runs;
- start, pause, step, reset, and change simulation speed;
- inject named ten-tick probes;
- compare all four existing architectures live;
- inspect resources, actions, parameters, hypotheses, graph state, and
  contracts;
- approve, reject, or modify pending Monad-0 contracts locally;
- archive telemetry under `data/monad0-lab/`;
- replay archived telemetry without re-running the simulation.

For direct engine development, the same server can be run on a local port. The
laboratory has no external-action capability; it is an observable research
surface inside Monad, not a separate project or simulation implementation.
