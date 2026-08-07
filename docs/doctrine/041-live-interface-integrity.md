# Live Interface Integrity Policy

**Status:** Canonical operating policy  
**Authority:** Admiral Cameron Lampley  
**Scope:** Root Console and all Live Captain operator surfaces  
**Effective:** 2026-08-06

## Purpose

Prevent operational landmines: controls that technically work but require the
Admiral to discover hidden routes, distinguish stale versions, or infer what a
button or drop target actually does.

## Rules

1. **One canonical path.** Each operator task has one primary visible entry
   point. Do not present parallel boxes, duplicate routes, or competing names
   for the same action.
2. **The target is named in the control.** A control states what belongs there,
   where the action occurs, and what happens next. “Drop here” is insufficient
   without naming the file type and destination.
3. **No stale surface in the active workflow.** When a new path supersedes an
   old one, remove the old surface from the active station. Do not make the
   Admiral compare versions or remember which one is current.
4. **No hidden temporary mode.** Temporary, experimental, or legacy behavior
   must not be silently reachable through the main workflow. It is either
   explicitly labeled and isolated, or removed.
5. **Immediate confirmation.** Every upload, command, or state change reports
   success or failure in the same surface, in plain language, with the next
   actionable step.
6. **First-use test.** Before shipping a UI change, a fresh operator must be
   able to answer without explanation: “Where do I go, what do I do, and what
   should I expect next?”
7. **Live verification.** Test the deployed route, not only source files.
   A feature is incomplete while the browser still shows an older or ambiguous
   surface.

## Captain gate

Before calling an operator-facing change complete, the Captain verifies:

```text
CANONICAL PATH:
VISIBLE TARGET:
ACTION WORDING:
SUCCESS / FAILURE FEEDBACK:
STALE SURFACES REMOVED:
LIVE BROWSER CHECK:
```

If any field is uncertain, the change remains engineering work—not Admiral
training.

