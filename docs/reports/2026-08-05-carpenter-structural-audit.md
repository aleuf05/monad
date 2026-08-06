# Carpenter's structural audit

Date: 2026-08-05
Scope: the gap between what the repository says the system is and what the
host actually runs. Nothing here is about code correctness — the test suites
cover that. This is about the machine.

---

## Why this audit existed at all

No test in this repo checks whether the installed configuration matches the
committed one. Six suites pass and none of them look at
`/etc/systemd/system/`. That is a blind spot by construction, and it is
exactly where three separate errors were hiding.

## Finding 1 — one unit had drifted

`fleetcore-serve` was running with an **installed unit older than the repo
copy**. Active, enabled, behaving correctly.

The differences were comments only, and that is what makes them worth
recording. The installed copy described:

- `web-lan/` and its toys as current — retired 2026-07-13
- Bridge Station 2.0 as a live consumer — no longer exists
- the `/monad/fleetcore-ws/` proxy path — the `/monad/` prefix was fully
  retired and confirmed 404 on 2026-07-13

**No functional drift. Seven weeks of stale explanation.** A reader
inspecting the live unit to understand why it binds as it does would have
learned three things that stopped being true in June.

Corrected by copy and `daemon-reload`. Service never restarted — comments
only, zero risk.

## Finding 2 — four units were never installed, and one of them I misreported five times

`libfive-api`, `monad0-web-lab`, `npr-headlines-fetch`, and `rich-voice`
exist in `scripts/` and had **no unit on the host at all**.

`rich-voice` was reported as "inactive" repeatedly through the session, and
an argument was built about whether to bring it up or leave it down. Both
options were wrong, because there was nothing to bring up.

**Cause:** `systemctl is-active` returns `inactive` for a unit that does not
exist, identically to one that is stopped. One word, two conditions, no way
to tell them apart from the output alone.

This is the single clearest instance of the pattern in doctrine 018, and it
survived five readings because `inactive` was a plausible answer every time.

`rich-voice` has since been installed and started — active on 4775, budget
endpoint reporting $0.00 of $0.10, cost boundary intact. The other three are
left alone deliberately: nobody has missed them, and installing something
because it exists in a directory is how a repo arrives at thirty-five tool
directories with four orphans.

## Finding 3 — the fleet is more than twice the size we were reporting

Counted from `/etc/systemd/system/` rather than from any document:

**23 units installed. 19 active.**

Five had never appeared in any status report of the session:
`fleetcore-serve`, `monad-watchman`, `monad-dns-override`,
`living-captain-status`, `public-images-api`.

The four inactive units are all deliberate and accounted for:
`chat-captain-web` (legacy Chat Captain parked per `current-bearing.md`),
`monad-lan-web` (retired 2026-07-13), `public-docs-api` (superseded),
`living-fleet-memory-reflect` (`static` — a one-shot, not a failure).

18 ports held, 4771–4799.

**Cause:** every count came from the services table in
`OPERATION-RESUME.md`, which is correct for what it is — the services *this
Operation works on* — and was read as the services running on the host,
which it never claimed to be. Recorded as doctrine 021.

## What was built in response

`scripts/sound-the-ship.sh` — four checks nothing else performs:

1. every tracked Python file parses (`archive/` excluded, retired on purpose)
2. every unit `ExecStart` points at a file that exists
3. installed units match their repo copies
4. which units the repo defines that the host never installed

**It found finding 2 on its first run**, after a human had misread the same
signal five times in one day. The tool knows nothing extra. It simply cannot
skip the step.

`scripts/j` — one-keystroke state: fleet counted from the host, six suites,
hull sounding, tree state, Captain state, one screen.

## Current condition

```
19 of 23 units active   ·   18 ports held
six suites green
SHIP IS SOUND — no faults found
tree clean, 0 ahead, 0 behind
```

Two false alarms are worth recording alongside the real findings, because a
report listing only confirmed faults overstates the inspector.

**`MemoryCurrent` at 356 MB** on `live-captain-bootstrap` was raised as a
possible leak and retracted within a minute — that is the cgroup figure and
includes page cache. Actual RSS: 27 MB. Healthy.

**Three units reported as pointing at missing files** were an error in the
first version of the check, which read the second token of each `ExecStart`
as a path. On those units it is a flag (`--port`, `-m`, `-k`). Corrected to
test every absolute token.

## Standing recommendation

Run `bash scripts/sound-the-ship.sh` before trusting any status report,
including one written an hour earlier by the same session. Three of the four
findings above were invisible to every test suite and to careful reading,
and visible immediately to a mechanical check.
