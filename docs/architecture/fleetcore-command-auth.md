# FleetCore command authentication and authorization

FleetCore's live server is read-only by default. `GET /snapshot` and an
unauthenticated WebSocket connection remain available for observation. Every
external command on `POST /command` or `/ws` must pass two separate gates
before JSON parsing or domain handling:

1. authentication identifies a bearer token or short-lived browser session;
2. authorization confirms that principal has command authority.

Start a development server with `--command-token <secret>` to create one
command principal. `--observer-token <secret>` is optional and exists to make
the distinction testable and operationally explicit: it authenticates a
caller but grants no mutation authority. Omitting `--command-token` denies all
external mutations regardless of what a caller presents.

Header-capable HTTP and WebSocket clients send `Authorization: Bearer
<secret>`. Browser clients first `POST /auth/session` with the command bearer
and an exact allowlisted `Origin` configured by a repeated `--browser-origin
<https-origin>` flag. The response sets a five-minute
`__Host-fleetcore_session` cookie with `HttpOnly`, `Secure`, `SameSite=Strict`,
and `Path=/`. Browser WebSocket upgrades authenticate only with that cookie;
an upgrade containing `Origin` never falls back to Bearer. Browser command
POSTs may use the same cookie and must retain the exact allowlisted Origin.
Cross-origin session creation and mutation are denied, and mutation preflight
returns `403` without permissive CORS headers. Query-string tokens are
unsupported because URLs leak into logs, browser history, and referrers.

An anonymous or invalid caller receives HTTP `401`; an authenticated observer
receives `403`. WebSocket connections remain useful as read-only observers and
receive a targeted error for attempted commands. Rejection occurs before the
existing schema, domain, canon, idempotency, event, world, checkpoint, or
broadcast path, so rejected callers cannot cause mutation.

There is no maintenance bypass in this slice. Internal clock ticks continue
through the server-owned tick loop; adding a local maintenance principal later
requires a named command allowlist, loopback/peer constraints, audit events,
and separate tests. Do not reuse the command token as a general service
credential.

Generate independent, fresh, high-entropy command and observer tokens for each
environment; startup rejects identical values. Presented secrets are SHA-256
hashed to fixed length and compared with the vetted `subtle` constant-time
primitive. Sessions use 256 random bits from the operating-system RNG and only
their hashes are retained in memory. Restarting expires all sessions.

Threat assumptions: bearer secrecy, TLS, and correct exact Origin allowlisting
are supplied by the operator and edge; host/root compromise, token theft,
denial of service, rate limiting, and token rotation without restart are out
of scope. Command-line tokens may be visible to local process inspection, so
production integration should load secrets from a protected descriptor or
credential store. The in-memory session table is opportunistically pruned and
is not size-capped; rate limiting/session quotas are a follow-up before hostile
public exposure. This change installs no credentials or deployment config.

Authentication does not override a read-only/degraded persistence mode;
integration must preserve that later guard after authorization and before
world mutation.
