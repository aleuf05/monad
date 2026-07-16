# libfive Headless Pipeline 1.0

1. **Originating intent** — Lieutenant ordered all libfive wiring finished and a sudo handoff produced.
2. **Verified starting state** — libfive absent; upstream documents Guile plus `bin/export-meshes` as its minimal headless Studio path. Upstream inspected at `c9e97343e0af998cd1696e85583eccba95532b96`.
3. **Objective / problem** — Reproducible headless Scheme-to-STL generation with bounded Monad CLI, manifest, smoke test, installation, evidence, and rollback.
4. **Scope and exclusions** — Guile/kernel/stdlib/export-meshes only; no Qt Studio, public arbitrary-Scheme endpoint, daemon, or raw port.
5. **Constraints / authority** — Pinned upstream source; generated assets remain non-canonical; privileged install only through `/home/cgl/cmd.sh`.
6. **Acceptance criteria** — CLI status is honest before/after install; bounded primitive generation writes nonempty STL and manifest entry; installer smoke-generates sphere; upstream commit/evidence recorded.
7. **Tests / rollback** — Python tests with fake exporter; commissioned smoke test; rollback removes `/opt/monad/libfive` and `/usr/local/bin/monad-libfive-export` after preserving outputs.
8. **Assigned actor** — Codex; privileged execution assigned to Lieutenant through commissioning handoff.
9. **Evidence and completion state** — Repository wiring verified; commissioning pending Lieutenant execution of `/home/cgl/cmd.sh`.
