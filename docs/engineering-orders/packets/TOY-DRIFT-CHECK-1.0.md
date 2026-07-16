# Toy Drift Check 1.0

1. **Originating intent** — The 2026-07-16 Architecture Engine inventory found repeated undocumented drift between `toys/` source and live `web/toys/` files.
2. **Verified starting state** — `diff -qr toys web/toys` confirmed both documented deployment transformations and real Radio Console drift. Asset Viewer and Cognition Graph repairs were already present as unrelated uncommitted work and were not touched.
3. **Objective / problem** — Add one repeatable command that distinguishes known deployment exceptions from unexpected source/live drift.
4. **Scope and exclusions** — Add a standard-library checker and this record. Do not edit toy runtime files, deploy, alter services, or resolve drift owned by another in-flight change.
5. **Constraints / authority** — Non-privileged repository work authorized by the Lieutenant's 2026-07-16 instruction to take available work. Preserve the dirty worktree and the Portainer path.
6. **Acceptance criteria** — The checker exits zero when public plain-copy runtime files match; exits nonzero with readable paths for unexpected missing, extra, or changed files; ignores source documentation, non-public Watchbook, historical Periscope versions, Bridge Station build inputs, and documented deployment-specific files.
7. **Tests / rollback** — Run the checker against the current tree and verify it identifies the known Radio Console drift. Run `py_compile`. Roll back by reverting the checker and packet commit.
8. **Assigned actor** — Codex.
9. **Evidence and completion state** — Verified complete and recorded. `python3 -m py_compile tools/check-toy-drift.py` passed. `python3 tools/check-toy-drift.py` exited nonzero and identified only the independently known `radio-console/app.js` mismatch in the current tree. The implementation commit contains only the checker and this packet.
