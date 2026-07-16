# Phase I Sweep — Findings and a Correction to the Record

Date: 2026-07-15

Prepared for: Captain / Lieutenant

Scope: Master Packet §21 Phase I ground-truth sweep (toy source/deploy
drift, World Intake V0.1 baseline, FleetCore event-stream requirements,
Living Captain wake sequence), plus a correction to
[2026-07-15-captain-issue-report.md](2026-07-15-captain-issue-report.md)'s
deployment status.

## Correction: issues #6 and #13 are live, not pending

The 2026-07-15 captain issue report states "code and tests complete; the
running services still predate all three fixes" for issues #6, #13, #14,
and stages `/home/cgl/cmd.sh` to deploy them. Direct inspection now shows
this is no longer accurate for #6 and #13:

- **Issue #6** (FleetCore vessel_events retention): the live
  `/snapshot` endpoint right now returns `vessel_event_retention` and a
  `vessel_events` array bounded at exactly 2000 entries (event_seq
  446703-448702 at tick 189331) -- the fix (`acc5b21`, 2026-07-14
  05:51:45 UTC) is running.
- **Issue #13** (World Intake's `/adjudications` submitting to
  FleetCore): `world-intake.service` was last started 2026-07-15
  06:36:16 UTC, after the fix commit (`12555ff`, 2026-07-14 05:51:56
  UTC) -- since it's a plain Python process with no build step, that
  restart is sufficient to confirm the fix is live.
- Both services' last restart timestamp (06:36:16 UTC today) lines up
  with `fleetcore-serve`'s journal showing the same restart time --
  consistent with a host-level restart picking up already-built/fixed
  code, not with `/home/cgl/cmd.sh` having run. Its evidence directory
  (`/home/cgl/commissioning/issues-6-13-14-plus-living-captain-20260715T012256Z`)
  does not exist, and the script is now stale on its own terms: it's
  pinned to `EXPECTED_HEAD=267a8ba`, and HEAD has since moved to
  `6579b0f` (this session's `fleetcore-live`/`bridge` fixes) -- its own
  guard would refuse to run it as written.
- **Issue #14** (captain-memory reflection atomicity) was already noted
  in the same report as merged upstream of the pin -- unaffected by any
  of this.

**Still genuinely outstanding: Batch B, the Living Captain status API.**
No `living-captain-status.service` unit exists (confirmed against
`systemctl list-units --all` and `systemd/*.service`), so
`web/toys/living-captain/`'s live frontend card still has nothing to
fetch from. This part of the captain issue report's status stands.

## Living Captain wake sequence (Master Packet §9) -- Partial

Two components share "captain" in their name and should not be
conflated:

- **`tools/living-fleet/` (`CaptainRuntime`)** -- live, runs as
  `living-fleet.service`. Per-cycle, per-escort-vessel situational
  awareness (own vessel, flagship, contacts, recent decisions) pulled
  from a real FleetCore snapshot. This is Section 6/9's *Living Fleet*
  (plural, per-vessel) requirement, and it's real and tested.
- **`tools/living-captain/` (`LivingCaptain`)** -- the singular,
  persistent command-presence Captain that §9 actually describes. Not
  currently live (no systemd unit; exists as tested library code +
  demo scripts + a status viewer that is explicit in its own docstring
  that it never assembles a Captain or calls `observe()` -- it only
  reads whatever an operator last ran by hand). Its `observe()` method,
  where implemented, inspects exactly two of the eight things §9 names:
  a FleetCore snapshot (tick, event_sequence) and World Intake's pending
  count. It does not inspect repository state, wall-clock/environment
  context, mission state, or unresolved work.
- This is exactly the gap Batch B above would close (the status API
  makes the frontend show real state), but Batch B alone doesn't add
  the missing inspection dimensions -- it surfaces what `observe()`
  already collects.

**Correction (later the same day):** the narrow 2-of-8 scope is not an
open gap. `docs/engineering-orders/living-captain-v0.2.md` documents it
as deliberate: "V0.2's manifest permits exactly the two read endpoints
already in use... This is infrastructure for a boundary that has
nothing to bound yet in V0.2, and that is the point... A V0.3 order,
not this one, is where an actual narrow write path would be proposed,
and only after this gate is live and tested." Widening `observe()`'s
custody manifest now, on an unprompted basis, would jump that
project's own "prove the gate before widening what it bounds"
sequencing. Reclassifying from "Partial, worth a decision" to
**verified-intentional, no action warranted** -- same bucket as
`fleetcore-control` and `periscope` turned out to be.

## World Intake V0.1 baseline (Master Packet §8) -- Reverified, holds

- 12/12 tests pass (isolated run, `tools/world-intake`)
- Public page and the API's actual registered route (`/proposals`) both
  return HTTP 200; root `/` correctly 404s (no route registered there,
  not a bug)
- Disk: 19% used, 176G free
- Qdrant: `healthz` passes

## FleetCore event-stream requirements (Master Packet §5) -- Reverified, holds

- Retention default is exactly `2000` (`default_vessel_event_retention()`,
  tagged in source as "GitHub issue #6's approved default"), matching
  the Packet's "~2,000 recent events" baseline, and now confirmed live
  (see correction above, not just in source)
- Checkpoint + restart recovery is real and tested:
  `checkpoint_plus_event_tail_replays_to_current_world` and
  `checkpoint_retention_keeps_newest_and_genesis`
  (`fleetcore/tests/determinism.rs`), both passing

## Toy source/deploy drift sweep -- closed

Full detail in-session; summary:

- **Fixed & deployed:** `fleetcore-live` (real bug -- deployed copy used
  a stale array-length cursor against FleetCore's now-bounded
  `vessel_events`; replaced with the source's `event_seq` cursor,
  verified live + source's own 7/7 test suite) -- commit `2742e47`
- **Fixed (source-side):** `bridge` -- the deployed copy already had a
  correct, deliberate hotfix (dead `../watchbook/` iframe replaced with
  a Ship's Log redirect) that source never received; synced source to
  match -- commit `6579b0f`
- **Deferred, confirmed deliberate:** `watchbook` -- the "stale" link
  removal is explicitly recorded in
  [2026-07-14-captain-issue-report.md](2026-07-14-captain-issue-report.md);
  not shipping it is a decision, not an oversight
- **Cleared as expected divergence:** `fleetcore-control` (`#serverUrl`
  dev/prod split), `periscope` (documented `duck-model-path` dev/prod
  split, `mk2-4` are historical docs only), `bridge-station-3.0`
  (build output), `fleet-motion` / `radio-console` /
  `reaction-diffusion-painter` (docs-only diffs)

## Open items for the Lieutenant

1. `/home/cgl/cmd.sh` has been rewritten: re-pinned to HEAD `eecf16e`,
   scoped to Batch B only (Living Captain status API install), since
   Batch A is confirmed already live and re-running it would just be
   redundant service restarts. Not yet executed as of this update --
   needs to be run interactively for its `sudo` steps.
2. ~~§9's Living Captain wake sequence... worth a decision~~ --
   resolved above: confirmed intentional V0.2 scope, no action needed.
