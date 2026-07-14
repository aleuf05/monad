# Living Fleet Captain Runtime

One shared process hosts Alpha, Bravo, and Charlie. It reads the same
authoritative FleetCore snapshot for every captain, asks a provider for one of
FleetCore's bounded escort postures, and submits the result through
`POST /command`. It never writes FleetCore state or vessel routes directly.

With no provider configured, `doctrine-fallback-v1` makes conservative,
role-specific decisions. Set `MONAD_CAPTAIN_PROVIDER_COMMAND` to an executable
that accepts one JSON request on stdin and returns one structured decision on
stdout to connect any model/provider. Invalid output, timeout, or provider
failure automatically falls back to doctrine.

Runtime identity, objectives, assessments, provider failures, and the last 20
decisions per captain persist under `data/living-fleet/runtime.json`. FleetCore
itself durably owns the authoritative accepted/rejected history and translated
consequences.

For a single real cycle:

```sh
python3 tools/living-fleet/captain_runtime.py --once
```

Production runs through `scripts/living-fleet.service`; it opens no port.
