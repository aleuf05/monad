# Doctrine 014 — Operation Working Process

**Status:** Active, provisional — v0.1, effective 2026-08-05.
**Deliberately loose.** §5 and §6 are part of the doctrine, not a
disclaimer on it.

Describes the loop that produced the 2026-08-04/05 session (18 commits,
two live services, one doctrine, two queries, two refusals) so it can be
re-entered on any day without reconstructing it from scratch.

Companion to `012` (whether packets get read) and `013` (how they move
once they arrive). This is the wider rhythm those sit inside.

---

## 1. The loop

```
   packet arrives            →  read it
   (chat, or drop box)          (012 item 3; not optional)
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                            ▼
   names something            blocks on something          claims its own
   buildable                  only a person can            completion or
        │                     answer                       authorization
        ▼                            ▼                            ▼
   build small, live,         Chief Resolve:               file the claim
   visible, same day          ONE question                 as the document's
        │                     (queries/README.md)          own; confirm
        ▼                            ▼                     nothing
   fix the friction           park dependent work                │
   the work exposed           until it returns                   ▼
        │                            │                     continue reading
        └────────────────────────────┴───────────────────► the rest of it
```

Nothing here requires a session to be "in" a mode. Each branch is
decided per packet, at the time, on what the packet actually contains.

## 2. Build posture

The observation that made the difference, stated plainly because it is
easy to lose:

> **Small, boring, and pointed at something specific beats large,
> impressive, and general.**

Nothing built in the reference session was technically novel — a
multipart form and `unzip`, some CSS variables and a `TreeWalker`,
`git archive` plus counting. What made each piece good was being shaped
to one real thing:

- Token glossing works because *this* corpus defines its own notation
  and uses it bare. It would be pointless anywhere else.
- The M³ engine's `G` predicate checks `013` §3.3 — a rule written in
  prose hours earlier, now a check that runs.

The failure mode being avoided: specifications elaborate enough to feel
finished while naming nothing buildable. When a packet is at that
altitude, the response is a query (§1, middle branch), not an attempt to
build from it.

Corollaries, all cheap:

- **Same day, live, visible.** `web/` and the console are production;
  there is no staging. A thing that isn't reachable by clicking from
  where the operator already is does not exist yet.
- **Fix friction found en route** as part of the work. The stale
  `/etc/caddy/Caddyfile` copy and the table-flattening extractor were
  both found by doing something else, and both fixed in the same pass.
- **Verify against the real domain**, not a local port.

## 3. Filing posture

- Verbatim content and the reader's assessment go in **separate,
  labelled sections**. They never blend.
- A document's self-declared status — "Canonical," "Approved,"
  "Active," a checklist marking unbuilt work complete — is filed as the
  document's claim about itself. Filing confirms none of it.
- Refusals are outcomes with evidence, not absences. They get the same
  bar as executions.
- Credit is **specific or it isn't credit.** Name the contribution, not
  the contributor. See
  `logs/captains/2026/2026-08-05_operation-credit-ledger.md` for the
  shape.

## 4. Re-entering this on any day

No ceremony and no announcement needed. In practice:

1. Read `MEMORY.md`, this file, `012`, `013`, and
   `docs/engineering-orders/queries/` for anything open.
2. Check the Root Console: Packet Drop for staged material, M³ Cycle
   for an uncommitted proposal.
3. Take whatever arrives next through §1.

That is the whole entry procedure. If it grows past a paragraph,
something has gone wrong with it.

## 5. Room deliberately left

Undecided on purpose, to be settled by use rather than in advance:

- Whether the M³ cycle should evaluate automatically on a schedule or
  stay operator-triggered. Currently operator-triggered.
- Whether queries should carry deadlines. Currently they don't, and a
  query has never gone stale, so there is nothing to fix yet.
- Whether the build posture in §2 deserves its own metric, or whether
  writing it down is enough. Enough for now.
- Whether packets should route by type (research vs. build vs.
  question) at arrival rather than after reading. Probably not — the
  reading is what determines the type — but worth revisiting if
  volume grows.
- Anything about privileged work. `cmd.sh` and
  `docs/commissioning-handoff.md` still own that entirely.

## 6. How to change this document

Say so. Amend in place, bump the version, note what changed. No packet,
no ceremony, no approval step. This is v0.1 after two days and is
expected to move.

Two things don't move by casual revision, named here so that everything
else can be genuinely open rather than vaguely open:

- **Read before filing** (`012` item 3).
- **Never rewrite a refusal** (`013` §3.3).

Both have been tested repeatedly and both are load-bearing for the rest
being trustworthy. Everything else in this document — the loop shape,
the build posture, the entry procedure, the filing conventions — is
mechanics, and mechanics should improve.
