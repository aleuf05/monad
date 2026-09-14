# WhatsApp regression closeout — 2026-09-14

## Confirmed state

Cameron's fresh self-chat exchange completed the full path:

`messages.upsert -> self-chat gate -> serialized queue -> Codex -> WhatsApp send`

The live bridge is currently one process, connected, and using the preserved
reference authentication state. The current process has an established
WhatsApp HTTPS socket. No provider fallback or Codex usage-limit failure was
observed.

## Cause versus recovery

The confirmed outage condition was that no WhatsApp bridge process was
running. The historical reason that process stopped is not retained in the
available logs, so the root cause of the stop remains unknown.

Recovery was to start exactly one live bridge against the existing
`reference-auth-state`; no pairing or credential reset was performed. The
bridge code also now guards worker completion/timeout races and recovers the
serialized queue after a failed task. Focused bridge tests pass.

## Mike scope

Mike's supplied phone identity is loaded into the allowlist, with no group
identity. The current in-memory Mike pause set is empty: no Mike message,
manual takeover, or replay has been observed since this process started. The
activation cutoff is the live process start time; older messages are rejected.

The next new supported text message is eligible only when WhatsApp reports
the configured Mike phone identity, is not historical, and Mike has not sent a
manual outgoing takeover. A different LID would remain rejected until it is
explicitly verified and configured.

No retained sanitized evidence identifies a missed Mike message; the log has
no Mike event. No message was replayed or sent late.

## Verification

- Cameron route: connected and successfully replied.
- Mike route: configured and eligible under the conditions above; no real
  round-trip claimed.
- Cameron takeover isolation and Mike takeover behavior: covered by focused
  tests.
- Worker failure/queue release: covered by the regression test; all 20 bridge
  tests pass.
