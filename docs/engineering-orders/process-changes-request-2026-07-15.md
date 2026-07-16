# Process Changes Request — Queue Naming Simplification

**Date:** 2026-07-15
**Status:** Proposed
**Requested by:** Lieutenant CGL, via engineering chat
**Scope:** Documentation / process only

## Request

Simplify the two queue concepts used in the engineering workflow to:

- `work queue` — active tasks still being executed
- `report queue` — completed findings, evidence, and status records

## Motivation

The current wording around `Q`, `queue`, `task queue`, and `report queue`
is easy to confuse in chat. A two-name scheme keeps the distinction
clear:

- work queue = action still pending
- report queue = action complete, evidence preserved

## Rules

1. One item belongs to one queue at a time.
2. Completed work moves out of the work queue immediately.
3. Report items are read-only records, not work items.
4. No duplicate IDs across the two queues.
5. If an item needs implementation, it stays in the work queue.
6. If an item only preserves or summarizes findings, it belongs in the
   report queue.

## Requested outcome

Adopt this naming scheme in future workflow references and chat summaries,
unless a more specific document intentionally overrides it for a narrow
case.
