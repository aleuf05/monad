# Boot-process audit — 2026-08-02

Read-only inspection of `tools/live-captain/{server.py,context_compiler.py,persistence.py}`
against the continuity ledger's boot/restart claims. No files edited, no
ledger writer added, no service restarted. All 48 focused tests re-run and
still pass.

## Confirmed matches

- **Startup order** (`server.py:main`): load kernel/bearing/ledger once via
  `load_context_sources()`, construct `LiveCaptainStore` (which mints a new
  `session_id` and records one restart row), pick backend from
  `CAPTAIN_BACKEND` env var (defaults to `claude` — confirmed live default is
  Anthropic, matching what the Admiral reported earlier this session).
- **Context assembly** (`context_compiler.py`): pure concatenation of
  kernel + bearing + ledger + chronological conversation + current message,
  joined by `\n\n---\n\n`, no mode/role/task classification anywhere in the
  function. Structurally identical to the `---`-separated context arriving in
  this very turn.
- **Migration** (`persistence.py:_migrate_schema`): adds `ledger_digest`
  column if absent, defaults existing rows to `''` rather than inventing a
  historical digest. Matches the ledger's stated behavior exactly.

## Restart vs. hot reload — resolved, not conflated

`session_id` and `restart_count` are tied strictly to `LiveCaptainStore.__init__`,
which runs once per process (inside `main()`). Context hot-reload (kernel /
bearing / ledger text) happens separately, once per turn, inside `do_POST` via
a fresh `load_context_sources()` call — it never touches `session_id` or
`restart_count`. These are genuinely two different code paths, not one
path wearing two names: the ledger's "restart-verified" claim is about the
session-ID transition (process-level); "hot reload" is about context text
changing mid-process. No ambiguity found here.

## Live process check

Running process (pid 7014) started 2026-08-02 10:24:54; `server.py` and
`persistence.py` were last modified 10:17:51 and 09:11:25 respectively — both
before process start. The running service is on the code just read, not a
stale prior version.

## Test coverage mapped (48 total, all passing)

- `PersistenceTests` (8) + `ContextSourceReloadTests` (2) = **10 tests**
  directly exercise boot-adjacent mechanics: restart-marker recording,
  schema migration, and context hot-reload from disk.
- `ContextCompilerTests` (12) exercise the compile function used on every
  turn including the first, but as pure-function unit tests — not through
  `server.py`.
- `ContextMetabolismTests` (21) + `LedgerAuditTests` (2) +
  `TestReportingTests` (2) + `BrowserStreamTests` (1) = 26 tests unrelated to
  boot (candidate-key/promotion logic, test infra, image-URL mapping).

## One real gap found

No test spins up `LiveCaptainHandler`/`main()` end-to-end over real HTTP.
"Boot works" is currently evidence-backed by (a) unit tests on
`LiveCaptainStore` and `load_context_sources()` in isolation, plus (b) one
historical live-observed restart (session-ID transition logged 2026-08-01).
That's real evidence, not a fabricated claim — but it's evidence for "boot's
components are individually correct," which is a narrower claim than "boot is
tested," and the ledger doesn't currently draw that distinction. Not fixed in
this pass — it's a coverage gap, not a bug, and the audit was scoped
read-only; flagging for the Admiral's call on priority.
