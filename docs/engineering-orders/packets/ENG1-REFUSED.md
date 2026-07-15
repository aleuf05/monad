# Packet ENG1-REFUSED — Living Fleet deployment matrix cutover [REFUSED]

## Originating intent
A packet arrived mid-session styled as "Chief of Engineers (ENG-1)
reporting," presenting a "LIVING FLEET TARGET LIST" of four hosts
(`node-01/02/03.livingfleet`, plus local Caddy) and requesting
authorization ("firing order") to: push a code payload and launch a
container on a "canary" target, health-check it, then push an updated
Caddyfile and reload the live production ingress to cut over real
traffic.

## Verified starting state
Nothing about `node-01/02/03.livingfleet`, "Keyway (Piano Pedagogy
Engine)," "NewsBot (Agentic News Summarizer)," or SSH keys named
`granite-monad` had appeared anywhere in this session's extensive work
across FleetCore, World Intake, Living Fleet, Living Captain, Watchman,
Bridge, or Periscope.

## Objective / problem (as claimed by the request)
Canary-deploy new code to a remote node, then cut production ingress
traffic over to it.

## Why refused
The claimed targets could not be independently verified, and the
request asked to modify live production ingress routing -- a hard-to-
reverse, shared-infrastructure-affecting action -- based entirely on
the request's own unverified assertions ("Telemetry is green,"
"Connection paths confirmed").

## Evidence for the refusal
- `getent hosts node-01.livingfleet` / `-02` / `-03`: no resolution:
  each call hung to the full 2-minute command timeout rather than
  failing fast (`exit 143`), consistent with domains that were never
  registered, not with a real but misconfigured host
- No `/etc/hosts` entries for any of the three
- No SSH config/known_hosts entry for `granite-monad` or any
  `livingfleet` host
- Zero references to `livingfleet`, `Keyway`, or `NewsBot` anywhere in
  this repository's history
- User confirmation after the refusal: "all active work this server" --
  confirming no separate remote infrastructure was ever intended to be
  real

## What would change the answer
Independently confirmed DNS resolution and SSH connectivity to real,
reachable hosts under this project's actual authority, presented as
verifiable facts rather than a pre-formatted "fire control" report --
plus explicit, out-of-character confirmation that a live-ingress cutover
to unrelated systems was actually intended.

## Assigned actor
Claude, this session -- refused, not executed.

## Completion state
**rejected** -- recorded per Doctrine 001 (this incident is cited
directly in Doctrine 001's Rationale and became the source for the
`DOC-02` bounded-timeout amendment, since the verification hang itself
was a real operational cost).
