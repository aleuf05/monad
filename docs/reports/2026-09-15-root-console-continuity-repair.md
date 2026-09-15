# Root Console Continuity Repair

**Date:** 2026-09-15  
**Status:** implemented and verified locally; backend activation pending  
**Access URL:** `https://cameronlampley.com/root/`

## Result

Root Console now has a server-owned continuity path over the existing Live
Captain SQLite database. An authenticated browser retrieves saved Admiral and
Captain messages, execution state, errors, and persisted tool/result events.
Reload and SSE reconnect restore that state without submitting a turn. Browser
requests carry stable UUID request IDs; the backend atomically reserves each ID
and replays its durable result instead of executing it again.

The current authentication, URL, context compiler, model backends, and all 691
pre-existing message rows are preserved.

## Implementation

### Persistence

`tools/live-captain/persistence.py` adds two tables without changing the
existing `messages` table:

- `executions`: request ID, Live Captain session, interaction mode, input,
  Admiral/Captain message sequence links, status, backend thread ID, result,
  error, timing, and metadata.
- `execution_events`: ordered JSON events tied to one execution, including
  completed tool/result events and terminal status.

`begin_execution()` reserves the browser request and stores its Admiral message
in one SQLite transaction. The unique `request_id` constraint is the final
duplicate-execution guard, including concurrent requests. Reusing an ID with
different text is rejected. Reusing it with the same text returns the existing
running, completed, or failed record.

If the service restarts with an execution still marked `running`, startup marks
it `failed` with an `interrupted` event. A process that no longer exists is
therefore never presented as still working.

### API and execution adapters

`GET /api/history?limit=1000` returns chronological saved messages and linked
execution/event records under the existing Root Console authentication.
`GET /api/status` also includes recent execution state.

`POST /api/turn` accepts `request_id`, checks for an existing execution before
turn admission, and returns the existing durable record for retries. New turns
record start, backend events, tool results, completion, errors, and response
metadata. AGY, Claude, and Codex adapters now emit the same execution ID and
accept the same event recorder callback.

### Browser behavior

`console/assets/js/root-console.js` now:

- loads up to 1,000 saved messages after authentication and every SSE connect;
- renders saved Admiral/Captain messages with original timestamps;
- restores recent tool results, running execution state, and saved errors;
- deduplicates by message sequence, execution ID, and event ordinal;
- reconciles a streamed reply with its later durable message instead of
  painting it twice;
- never submits work as part of reconnect/history restoration;
- generates one UUID per submission and reuses it through the explicit
  retry-last-request control;
- reports whether history was restored while retaining the existing live
  progress, activity, and error displays.

`console/index.html` adds a compact, responsive history status/retry strip. The
existing desktop row layout and sub-760px stacked phone layout remain intact.

## Database protection

Before schema work, the live SQLite database was backed up with SQLite's online
backup API:

`/home/cgl/dev/monad/data/live-captain/live-captain.db.pre-continuity-repair-20260915T075706Z.bak`

The backup contains 691 messages and 40 restart markers. It was used as the
source for an isolated migration rehearsal; the backup itself was not migrated.

## Verification evidence

- `python3 -m unittest discover -s tools/live-captain -p 'test_*.py'`:
  **114/114 passed**.
- Root Console daemon adapter tests: **11/11 passed**.
- Dedicated continuity tests prove:
  - two concurrent/browser-like callers with one request ID create exactly one
    execution and one Admiral message;
  - completed results and tool events survive retrieval;
  - failures survive retrieval and retry remains replay-only;
  - a restart converts abandoned running work into a durable interrupted error;
  - legacy messages remain readable.
- Real HTTP-socket tests prove:
  - a second authenticated session sees the first session's saved conversation;
  - a repeated HTTP request ID returns the same execution and invokes the fake
    backend exactly once;
  - history remains authentication-protected.
- A copy of the 691-message production backup was opened through the new store:
  all 691 messages remained readable, both new tables were present, and
  `PRAGMA integrity_check` returned `ok`.
- Python compile, JavaScript syntax, and `git diff --check`: passed.
- Headless Chromium at 1366×768 and 412×915: no horizontal overflow; terminal,
  prompt, and history status remained visible. At Android width, repeated
  history restoration rendered the saved Admiral message, Captain reply, tool
  result, failure, and running state exactly once, with no page errors.

No real Captain turn was sent and no physical-device check is claimed.

## Live activation

The frontend under `console/` is served directly and therefore already sees
file changes. It degrades safely while the old backend is still running: the
ordinary Captain bridge remains usable and the strip reports that saved-history
activation is pending.

One controlled backend restart is required to load the new schema and API:

```text
sudo systemctl restart live-captain-bootstrap.service
sudo systemctl is-active live-captain-bootstrap.service
```

Then authenticate at `https://cameronlampley.com/root/` and confirm the strip
reads `History restored`. `root-console.service` and Caddy do not require a
restart for this change.

## Windows → Android → Windows acceptance procedure

Use one harmless, read-only task:

1. On Windows, open `https://cameronlampley.com/root/`, authenticate, and send:
   `Captain, report the current UTC time and label this continuity check HARBOR-LANTERN. Do not modify anything.`
2. Wait for the reply and any execution summary. Reload the Windows page once;
   confirm the command, reply, and `History restored` remain visible once.
3. On Android, open the same URL and authenticate. Confirm HARBOR-LANTERN and
   its result are present. Send: `Continue HARBOR-LANTERN: state whether this is the Android leg. Do not modify anything.`
4. Reload Android once. Confirm both legs and their results remain visible once,
   with usable scrolling and the input above the virtual keyboard.
5. Return to Windows and reload. Confirm both legs, replies, execution/tool
   summaries, and any errors match Android and occur only once.

The Admiral performs this physical-device check; it has not been claimed as
passed here.

## Remaining limitations

- The browser loads the newest 1,000 messages. The API reports how many older
  messages are omitted, but cursor pagination is not yet exposed in the UI.
- Only the newest 20 executions have detailed tool/result events painted into
  the transcript on restore; all linked conversation messages within the
  1,000-message window are restored.
- An intentional rerun requires a new submission/request ID. Retry-last is
  deliberately replay-only for the previous ID.
- Physical Android virtual-keyboard, background-tab, cookie-retention, and
  Windows/Android handoff behavior still require the Admiral acceptance pass.
