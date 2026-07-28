# Engineering Packet — Live Captain Site Integration — Version 1

Status: blocked on privileged commissioning

## 1. Originating intent

The Admiral authorized Commander Codex to integrate Live Captain into the
live Project Monad site, proceeding autonomously except for necessary human
conference and privileged `cmd.sh` handoff.

## 2. Verified starting state

The public Living Captain page and read-only status API are already live.
The new terminal conversation client is functional and a human-operated
instance was running during inspection. Conversation persistence currently
assumes one writer. Caddy already proxies the read-only status API to
loopback port 4774. Port 4776 was unused.

## 3. Objective

Add an authenticated Private Conference panel to the live Living Captain
page while preserving the independent public status instrument and the
terminal client's restart continuity.

## 4. Scope and exclusions

In scope: one single-owner conversation engine, terminal compatibility,
authenticated loopback HTTP service, browser login/conversation panel,
persistent usage boundary, clear degraded states, service/Caddy handoff,
tests, and live verification.

Excluded: anonymous public chat, shell, tools, uploads, arbitrary file
access, autonomous work, background model calls, canon mutation, voice
conversation, multiple operators, and production systems outside the
existing Monad site.

## 5. Constraints and authority

The existing terminal Captain must not be interrupted. Commissioning must
fail closed while a terminal instance is active. The Gemini key and
conference password must remain outside Git and logs. The web service binds
only to 127.0.0.1. The public read-only status service remains separate so
conversation failure cannot take down the instrument.

## 6. Acceptance criteria

- The terminal and web interfaces share one engine and one durable transcript.
- Only one process can own conversation state.
- The browser must authenticate before reading or writing conversation.
- Authentication uses an HttpOnly, Secure, SameSite=Strict cookie.
- Cross-origin writes, oversized requests, missing authentication, and
  concurrent model calls fail closed.
- The API key and password never appear in output, transcript, or logs.
- Gemini failure preserves history and produces no invented reply.
- The existing public status page remains useful if conversation is offline.
- The service binds to loopback and survives restart through systemd.
- The real site exposes a clear Private Conference panel.

## 7. Tests and rollback

Offline tests cover authentication, origin checks, request limits, secret
handling, single ownership, transcript continuity, and provider failure.
Live verification uses the real domain after commissioning.

Rollback disables and removes the new service, removes its Caddy route,
restores the previous static toy files, and reloads Caddy. Existing transcript
data is preserved unless the Admiral separately authorizes deletion.

## 8. Assigned actor

Commander Codex implements and verifies. The Lieutenant performs the
privileged handoff and privately chooses the conference password.

## 9. Evidence and completion state

- 2026-07-28: authorized.
- 2026-07-28: starting state inspected; implementation executing.
- 2026-07-28: shared engine, exclusive ownership lock, authenticated loopback
  service, private browser panel, service unit, Caddy route, password setup,
  and reversible installer implemented.
- 2026-07-28: 25 Living Captain tests pass, including authentication,
  signed-session expiry, origin rejection, bounded login attempts,
  single-owner enforcement, persistence, cost boundary, and provider failure.
- 2026-07-28: Python, shell, JavaScript, whitespace, and Caddy validation pass.
- 2026-07-28: commissioning correctly remains blocked while PID 29244 is
  running the human's terminal Live Captain. No process was interrupted.

Next state: the Lieutenant exits the terminal Captain with `/quit`, chooses
the Private Conference password through the hidden prompt in `cmd.sh`, and
returns control to Codex for live UI deployment and real-domain verification.
