# Living World Intake V0.1 — Integration Findings

**Date:** 2026-07-14
**Scope:** Code-review findings from live end-to-end testing of the committed
`c5228a2 "Build Living World Intake V0.1"` against a real `fleetcore-serve`
process. This is separate from
`docs/incidents/2026-07-14-world-intake-concurrent-session-collision.md`
(the process/workspace-collision writeup) — these are defects found in the
feature itself, not in how it was built.

## Method

The *running* production `fleetcore-serve` (PID 1038) is on a stale binary
that predates the canon work entirely — see Finding 4. To get a real signal,
I built the current source fresh and ran it as a standalone process on a
scratch port (`127.0.0.1:4779`) and scratch state directory (not production
`data/fleetcore/`), then drove the actual fixture through the real
`Intake` class end to end: `ingest → extract → review → compile → commit`,
with `commit()`'s `submit()` posting real HTTP requests to that fresh
server — not a mock, not a hand-typed JSON fixture. Torn down after; nothing
touched production state.

## Findings

### 1. `alias_reference` compiles into a real command without requiring the `link` decision

**Severity: Medium-High (confirmed, currently masked by fixture data)**

`tools/world-intake/world_intake.py:133-134`:

```python
elif pred == "alias_reference":
    change={"change":"add-alias","entity_id":value.get("entity_id") or "crew."+slug(value["possible_canonical"]),"alias":row["subject"]}
```

This branch runs for *any* compilable decision (`approve`, `amend`,
`unverified`, `link` — see the `if row["decision"] not in {...}` gate a few
lines above, which doesn't further restrict by predicate). A bare `approve`
on the "Chief Claude" alias assertion compiles cleanly:

```json
{"change": "add-alias", "entity_id": "crew.claude", "alias": "Chief Claude"}
```

**Failure scenario:** this directly contradicts the acceptance fixture's own
requirement — "'Chief Claude' is treated as a possible alias, not silently
created" — and the order's rule "Alias ambiguity causes review; there is no
silent merge or duplication." In *this* fixture the bug is inert: no entity
named `crew.claude` exists (no recruit is named Claude), so FleetCore itself
rejects it (`unknown canon entity 'crew.claude'`), which happens to save the
day. But that's a coincidence of this fixture's data, not a guarantee — in
any report where the guessed canonical name happens to match a real existing
entity, this would silently attach an unreviewed alias to it. Confirmed via
direct execution, not inferred: `compile()` returned a valid payload, no
exception raised, for a plain `w.review(id, "approve")` with no `edit`.

**Fix:** compile() should reject (raise `ValueError`) unless
`row["decision"] == "link"` for `predicate == "alias_reference"`, mirroring
how `test_04_alias_possible_not_created` already asserts `resolve()` never
merges/creates silently — `compile()` needs the same guarantee for its own
code path, which no existing test currently exercises.

### 2. The compiled alias text is wrong even when a link is present

**Severity: Medium (correctness bug, compounds Finding 1)**

Same line: `"alias": row["subject"]`. The assertion's `subject` field is
`"Chief Claude"` — an arbitrary label the extractor chose to represent "this
identity assertion about the Claude/Commander Claude/Chief Claude
confusion" (`world_intake.py:57`). The actual alias text extracted from the
source line ("Commander Claude reports...") is `value["alias"]` =
`"Commander Claude"`. So even once Finding 1 is fixed to require `link`, the
compiled command would still record the wrong alias string
(`"Chief Claude"` instead of `"Commander Claude"`) against whatever entity
the Captain links it to.

**Fix:** use `value["alias"]`, not `row["subject"]`.

### 3. The reactor `authorization_request` has no valid canon subject and is always rejected

**Severity: Low-Medium (fails closed — not unsafe, but incomplete)**

Verified directly: approving and compiling the "Request Captain authorization
to start the reactor" assertion produces
`{"change":"record-authorization","authorization":{"subject_id":"crew.reactor",...}}`,
which the real server rejects with `422 unknown authorization subject
'crew.reactor'` — because nothing in the fixture ever creates a `crew.reactor`
(or any reactor/vessel) canon entity; only the 9 crew recruits get
`CreateEntity`d. Every attempt to compile this specific assertion will
reject, permanently, regardless of what the Captain decides, until a valid
subject entity exists.

**This does not violate the fixture's safety requirement** — "no
reactor-start event is created" holds trivially, since the command never
succeeds at all — but it also means "Startup authorization remains pending"
isn't really *recorded* anywhere in FleetCore canon; it only exists as a
rejected command in the local intake SQLite DB (still provenance-queryable
there, just invisible to anything reading FleetCore's `canon_authorizations`).

**Open question, not a quick fix:** V0.1's entity model only ever creates
`crew` entities from `propose_entity` assertions. There's no path today to a
valid subject for "the reactor" or "the vessel" — it doesn't cleanly fit
`crew`/`agent`, and might belong as a `station` (there's already a "Deck 7
Reactor Console" station name in play) or a `vessel` entity, but nothing
currently proposes creating one. Needs a design decision, not a one-line
patch.

### 4. The live `fleetcore-serve` process cannot accept any canon command right now

**Severity: Blocking for any live/production use, zero code risk**

`fleetcore-serve` (PID 1038) has been running continuously since boot
(01:36:32), on a binary that predates all of the canon work — confirmed via
`/proc/1038/exe` pointing at a `(deleted)` inode, and a direct `curl` to
`/command` returning `400 unknown variant 'apply-canon-change', expected one
of 'set-route', 'set-escort-mode', ...` (the pre-canon command list). The
on-disk binary at `fleetcore/target/release/serve` *is* current (rebuilt at
03:03, correctly recognizes `apply-canon-change` when run standalone — that's
what Finding 1-3's testing used). Restarting the systemd unit is what's
missing, and that needs `sudo`, which no session in this repo currently has
— it's exactly what `scripts/install-world-intake.sh` stages for the
Lieutenant to run. Until that happens, the feature is fully inert against
the real shared world no matter how correct the code is.

## What held up under real testing

- All 9 `CreateEntity` commands for the fixture's recruits: accepted.
- Role/station assignment and capability attachment for tested recruits
  (Ada, Vance): accepted, and capabilities landed with `verified: false` in
  every case — the "capabilities default to unverified" rule holds at the
  FleetCore layer, not just as a UI convention.
- Vance's `request_permission` compiles to `record-authorization` (status
  `pending`) — **`canon_permissions` stayed empty** after the full run; no
  `GrantPermission` was ever produced anywhere in the pipeline. Vance gets no
  scram authority, confirmed by direct inspection of the resulting snapshot,
  not just by the absence of an error.
- Idempotent retry: re-`commit()`ing an already-committed adjudication made
  zero additional real HTTP calls — the local `canon_events` short-circuit
  works even across separate script invocations reusing the same
  deterministic IDs.
- `cargo test` (10/10, including a new
  `intake_compiler_wire_shape_deserializes_as_a_canon_command` wire-contract
  test) and the Python acceptance suite (12/12) both stay green — neither
  suite exercises the `compile()` path with a bare `approve` on an alias
  assertion, which is why Findings 1-2 weren't caught before this pass.

## Update on Finding 4

A real, protocol-compliant commissioning package exists at
`/home/cgl/cmd.sh`, with evidence capture and rollback data. It restarts
`fleetcore-serve` on the current binary, installs `world-intake.service`, and
wires the Caddy route. Finding 4 closes when the Lieutenant runs that package;
the exact-HEAD and clean-tree guards prevent stale commissioning.

## Recommendation

Findings 1–3 are resolved and regression-tested. Finding 4 is now purely the
privileged activation gate. Current advice is **HOLD FOR COMMISSIONING**, not
for additional feature correction: do not claim live intake until the pinned
handoff completes and its public/API evidence passes.

## Integration resolution

Before commissioning, the commander resolved Findings 1–3:

- `alias_reference` compilation now requires the `link` adjudication and an
  explicit existing entity ID; bare approval fails closed.
- The compiled alias is the extracted `value.alias` (`Commander Claude`), not
  the assertion's display subject.
- Reactor-start authorization targets FleetCore's existing canonical
  `vessel.monad`; FleetCore permits authorization records to reference its
  native vessels as well as intake-created canon entities. The status remains
  `pending`, and no watch/reactor-start event is created.

Regression tests cover all three. Finding 4 remains the intentionally gated
sudo commissioning step.
