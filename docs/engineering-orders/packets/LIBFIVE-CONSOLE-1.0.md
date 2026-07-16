# libfive Shape Foundry Console 1.0

1. **Originating intent** — Lieutenant asked whether the frontend was clear, confirmed current information was sufficient, and ordered implementation.
2. **Verified starting state** — A bounded CLI supported sphere, box, and torus STL generation, but no frontend/API/preview existed and the exporter was uncommissioned.
3. **Objective / problem** — Make libfive generation click-reachable, visibly honest about readiness, bounded at the generator boundary, and useful for catalog inspection before commissioning.
4. **Scope and exclusions** — Static console, dependency-free STL preview, manifest catalog, loopback API, validation, tests, service/Caddy handoff. No arbitrary Scheme or canonical-world authority.
5. **Constraints / authority** — Three named primitives only; safe output names; finite dimensions; generated assets remain non-canonical.
6. **Acceptance criteria** — Homepage card; visible offline/ready state; bounded form; generation errors; binary/ASCII STL preview; downloads; hashes/provenance; API rejects extra fields; final sudo handoff installs exporter/service/route and smoke-tests public HTTPS.
7. **Tests / rollback** — Python tests, JS syntax, live static markers, API unit tests. Rollback disables/removes `libfive-api.service` and its Caddy route; generated assets remain evidence.
8. **Assigned actor** — Codex; privileged commissioning deferred to Lieutenant's final `/home/cgl/cmd.sh` run.
9. **Evidence and completion state** — Repository implementation complete; privileged commissioning pending final accumulated sudo execution.
