# Commissioning handoff protocol

This project has no CI/CD and no passwordless sudo for agent sessions (see
`docs/deployment.md`). Any change that needs a privileged action on
Granite -- restarting `fleetcore-serve` or `living-fleet`, installing a
systemd unit, deploying `/etc/caddy/Caddyfile` -- has to be staged by an
agent and actually run by the Lieutenant. `/home/cgl/cmd.sh` (outside the
repo, not version-controlled) is the one handoff point for that.

## The rule

**`cmd.sh` holds only the current, actionable batch of commands for the
task in front of the Lt. right now -- nothing else.** Not a template, not
a placeholder, not last week's commands with a comment saying they're
stale. If nothing is queued, the file says so in one line and exits 0. If
something is queued, it's the real, ready-to-run thing.

An agent handing off privileged work must never leave the Lt. looking at
a script that refuses to run, throws on a fillable placeholder, or
requires him to read prose to figure out whether it's safe to execute.
That reads as broken, not as a safety feature.

## What a real handoff script looks like

Every consolidated script (see the Effort B example, archived below) has
followed this shape and should keep following it:

1. **Pinned to a commit.** `EXPECTED_HEAD` is the exact git SHA the script
   was written against. The script refuses if `HEAD` has moved.
2. **Refuses on a dirty tree.** No privileged action runs against
   uncommitted local changes.
3. **Pre-flight health check.** Refuses if the service(s) it's about to
   restart aren't already healthy -- don't restart into failure.
4. **One evidence directory per rollout**, under
   `/home/cgl/commissioning/<name>-<UTC-timestamp>/`: git state, pre-change
   service status/journal, and for anything touching FleetCore's own
   process, a full backup of `data/fleetcore/{world.json,events.jsonl}`
   plus the latest checkpoint, sha256-hashed, before any change. Write
   `operator-notes.md` there with the rollback procedure spelled out, not
   just a description of what's changing.
5. **Completion marker.** Write a `restart.completed` (or similarly named)
   marker into the evidence directory on success, and refuse to run again
   if that marker already exists -- a spent script should not be re-runnable
   by accident.
6. **Idempotent where possible.** e.g. seed-data imports should upsert by
   stable id, not duplicate on a second run.

## After it runs

1. Copy the just-run script into its own evidence directory (it becomes
   part of the permanent record of that rollout), or into
   `/home/cgl/commissioning/cmd-sh-templates/` if it was a reusable
   template rather than a one-off pinned to a specific commit.
2. **Flush `cmd.sh`** back to a minimal, non-erroring "nothing queued"
   state. Don't leave the just-run script sitting there -- the Lt.
   shouldn't have to remember whether `cmd.sh` is stale, freshly written,
   or already executed.
3. If the rollout surfaced a real gap (a missing step, wrong ordering,
   whatever) fix the *next* script, and note the gap in that rollout's
   `operator-notes.md`. Don't quietly patch around it in a way that isn't
   recorded anywhere.

## Precedent

- `/home/cgl/commissioning/living-fleet-v0.1-20260713T231102Z/` -- original
  Living Fleet V0.1 FleetCore persistence/determinism restart. Two-phase
  (`first`/`second`) variant of this pattern; restart itself was completed
  later than this evidence capture (see the next entry).
- `/home/cgl/commissioning/living-fleet-v0.1-effort-b-20260714T000001Z/` --
  consolidated rollout: Caddy route, two new systemd units, and both
  `fleetcore-serve` + `living-fleet` restarts in one script. Single-batch
  variant (no phase split) at the Lt.'s request. Includes the operator-notes
  reconciling the open change-freeze from the first package with this one.
- `/home/cgl/commissioning/cmd-sh-templates/` -- reusable, unpinned
  template copies (fillable `EXPECTED_HEAD`/`EVIDENCE_DIR` placeholders)
  for starting the next script from, not meant to be run as-is.
