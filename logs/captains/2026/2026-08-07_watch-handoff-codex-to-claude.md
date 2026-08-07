# Watch Handoff — Codex → Claude, 2026-08-07

**Order (verbatim, Admiral):** "attempt canonical bring up system Living
Captain POSTURE this is a watch handoff Codex -> Claude"

**Disposition:** executed. The watch is Claude's on both Captain surfaces.
Nothing was proposed and left undone.

---

## What changed

| | Before | After |
|---|---|---|
| `CAPTAIN_BACKEND` (config) | `codex` | `claude` |
| `CAPTAIN_CLAUDE_MODEL` (config) | unset → in-code `sonnet` | `opus`, explicit |
| in-code fallback, both servers | `"codex"` | `"claude"` |
| `root-console.service` | pid 1219851 | pid 2216449 |
| `live-captain-bootstrap.service` | pid 1121196 | pid 2216453 |
| posture file | 458 lines, mission section live | 301 lines, standing posture |

Config lives at `/home/cgl/.config/monad/root-console.env`, shared by both
units. Backed up first to `root-console.env.bak-20260807-watch-handoff`;
the rollback is one line and one restart.

## Why the backend switch is doctrine, not preference

`docs/doctrine/010-api-usage-authority-policy.md` is CONFIRMED, Admiral
sign-off 2026-08-03, and says two things that bear directly:

- line 25 — "**Live Captain (root-console.service): Anthropic/Claude only,
  for now.**"
- lines 30-36 — "**OpenAI (Codex) API usage is strictly reserved for the
  Admiral.** No service, daemon, or agent process may call the OpenAI API
  ... without the Admiral's explicit, per-instance authorization."

Codex held the watch under that per-instance exception, commissioned by the
Admiral on 2026-08-05
(`logs/captains/2026/2026-08-05_first-codex-live-captain-ceremony.md`). That
authorization is what this order withdraws. The handoff therefore returns
both surfaces to the doctrine-default vendor rather than substituting one
preference for another.

**One defect repaired in passing.** Doctrine 010 lines 52-61 name the
pattern of a vendor choice "baked into the code" as out of policy, and cite
`os.environ.get("CAPTAIN_BACKEND", "claude")` as the example — noting that
at the time of writing the in-code default *happened* to match the ruling.
It no longer did: both servers had drifted to a `"codex"` fallback, so an
unset env var would have silently selected the Admiral-reserved vendor. Now
`tools/root-console/server.py:477-481` and `tools/live-captain/server.py:579-583`
default to `claude` with the reason in a comment beside it.

**Uncertainty preserved:** three Codex processes are still alive on this
host (pids 416985, 419342, 2199510). Every one has a `-bash` ancestor —
interactive terminals, the Admiral's own use, which doctrine 010 permits
without qualification. No *service* runs Codex. Verified by `ps -o ppid=`,
not assumed from the restart.

## Verification — observed, not inferred

Doctrine 022's rule applies: active is not routed is not reachable is not
working. Each line below is a separate measurement.

1. **Ship sounded before touching anything** — `bash scripts/sound-the-ship.sh`
   → `SHIP IS SOUND — no faults found`, 218 python files, 23 units, posture
   loads for both CLI embodiments.
2. **Focused test set** — `python3 -m unittest tools.root-console.test_codex_daemon
   tools.live-captain.test_live_captain` → **59 tests, OK**. Same set and
   same count Codex recorded in
   `docs/reports/2026-08-07-captain-standard-transition-observation.md:96`,
   so the baseline is preserved across the handoff, not merely passing.
3. **Headless auth proven before the switch, not after** — `claude -p` from a
   neutral cwd returned `is_error: false`, `--model opus` accepted.
4. **Both units restarted, new pids, ports rebound** — 4792 → pid 2216449,
   4778 → pid 2216453 (`ss -ltnp`).
5. **The live services' own children are Claude** — `pgrep -af` shows two
   `claude -p --input-format stream-json ... --model opus` processes owned
   by the two new service pids. The Codex daemon children died with the
   restart.
6. **One real turn, through the adapter the services run** — `ClaudeDaemon.send_and_wait`,
   cwd `/home/cgl/dev/monad`, completed in **3.7s**; status reported
   `{'backend': 'claude', 'model': 'opus', 'running': True}`; the reply
   correctly named the ship and `EDIT-THIS-ONE-FILE.md` as the posture
   source, so posture loaded into the daemon's context rather than the
   process merely starting.

**What is NOT verified, stated plainly:** the HTTP-auth → daemon leg on the
live surface. `/api/status` on both ports correctly returns
`{"error": "authentication required"}`, and the console password is the
Admiral's; the blind-holder has no way to mint a session. That leg is
unchanged code covered by item 2's 59 tests. **The Admiral closes it by
logging in at `https://cameronlampley.com/root` and sending one message.**
Until he does, treat the live HTTP path as tested-but-not-live-inspected.

## Posture brought up canonically

`EDIT-THIS-ONE-FILE.md` carried a 157-line `⚑ ACTIVE MISSION` section whose
own first line read *"Temporary. Delete this whole section when the mission
closes and standing posture resumes."* Research Object 001 landed and was
committed at `c142223`, so the mission is closed and the section is gone.
Standing posture now governs both embodiments, unmixed with a finished
mission's rules — including its `do NOT commit` hard stop, which expired
with it and would otherwise have read as live law to the next watch.

The mission's open items did not go with it. The highest-value one is now a
queue entry rather than a line in a closed record:

**`CANON-TRACK-01`** — ten doctrine files stamped `Status: Canon` are
untracked (023, 024, 025, 026, 027, 028, 029, 030, 031, 041). Re-verified
by `git ls-files --error-unmatch` at this handoff; still exactly ten. `git
clean -fd` deletes them, M³ has never governed one of them because `H_t` is
git and an untracked file never reaches `HEAD`, and
`023-true-live-captain-integrated-command.md` is the doctrine of record that
`EDIT-THIS-ONE-FILE.md` cites by name. Filed in
`docs/engineering-orders/queue.md`.

## Cost, since it is now metered differently

The smoke-test turn — nine output tokens — cost **$0.059969**. Opus is an
explicit choice, made because posture opens "maximum-capability baseline
experiment," and it is one line in the env file to change:
`CAPTAIN_CLAUDE_MODEL=sonnet`. Flagged rather than decided quietly, because
the Admiral pays for turns he did not ask for.

## Inherited, still standing

From the outgoing Live Captain's safe-shutdown note
(`tools/live-captain/context/claude-channel.md`):

- The server-owned free-running interaction loop is the stable baseline. Do
  not create a competing autonomous loop.
- `/home/cgl/cmd.sh` holds an older, unspent root-console restart batch.
  **Not run, not modified.** This handoff's restart used a fresh, explicit
  `sudo systemctl restart` of two named units; passwordless sudo is
  available on this host, so no `cmd.sh` staging was required.

— Claude, taking the watch.

## Commit boundary — deliberate, and a partial one

Three files committed: `EDIT-THIS-ONE-FILE.md`,
`docs/engineering-orders/queue.md`, and this record.

Three files **live on disk and running, but left uncommitted on purpose** —
`tools/root-console/server.py`, `tools/live-captain/server.py`,
`tools/live-captain/context/claude-channel.md`. Each already carried another
watch's substantial in-flight work when this one opened (context-image
upload, bridge-signal phases, speech acceptance, course/intake projection —
107 and 250 changed lines respectively). Committing them would have
attributed that build to this handoff. My edits in them are small and
described above by `file:line`.

**This is the sixth instance of the defect Research Object 001 named: this
repository mistakes "on disk" for "in git."** The backend fix is live and
correct right now, and it survives no `git clean -fd`. Whoever commits the
in-flight console work carries it; if that does not happen, `CANON-TRACK-01`
and this line are the trail back to it.
