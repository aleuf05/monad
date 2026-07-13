d give it a standing instruction like:
Prefer rapid, reversible implementation over exhaustive validation.
Use the smallest test set that gives reasonable confidence.
Avoid repeated re-checking unless a failure or ambiguity appears.
Make localized changes, commit early, and leave deeper hardening for a later pass.
Flag risks briefly, but do not block progress on low-risk issues.
And maybe one sharper line:
Do not spend more time proving the change works than implementing the change unless the change affects security, persistence, or shared state.

## POLICY: Live tests, rapid iteration

There is no staging environment for this project -- `https://cameronlampley.com/`
is the test environment (see `docs/deployment.md`: no deploy step, editing
`web/` is editing production). Prefer shipping and verifying live over
building local test scaffolding first. Get the feature working and visible
on the real site, iterate from there, and don't let caution about "is this
safe to test live" slow that down -- it's the intended workflow here, not a
risk to be managed. This doesn't relax the URL/port policy below: "live"
always means the real domain, never a throwaway port filling in for it.

## POLICY: No strange URLs or ports

Every feature must be reachable by plainly browsing `cameronlampley.com` --
no non-standard ports, no bare IPs, no internal-only hostnames, no path a
visitor couldn't reach by clicking through the live site. `web/` is the one
deploy target (see `docs/deployment.md`) and there is no deploy step:
editing a file under `web/` changes production immediately. Concretely:

- Before calling any work on a public-facing toy done, verify it against the
  real `https://cameronlampley.com/...` URL, not just a local dev server.
  `toys/<name>/` is source; it is not live until copied into `web/toys/<name>/`.
- Never leave an ad hoc local server (`python3 -m http.server`, `npx serve`,
  a bound dev process, etc.) running against this repo unattended. This has
  already caused a real incident (see `docs/deployment.md`) -- kill it the
  moment you're done checking something.
- No temporary/throwaway deployments as a substitute for shipping for real --
  no "just for now" port, subdomain, staging path, or ad hoc process standing
  in for the real thing. If it's worth showing the Lt., it goes through the
  one real deploy target (`web/`, `https://cameronlampley.com/`) or it isn't
  done yet.
- Any backend a public toy depends on (FleetCore, etc.) must be reached
  through the existing Caddy reverse-proxy path, not a raw `host:port`.

## POLICY: If the Lt. can't see it on the live app, it doesn't exist

Deployed-but-buried does not count as done. New or changed functionality
must be plainly, obviously visible on the live page it belongs to -- not a
console log, not a value you have to inspect DOM/localStorage to find, not
something reachable only via a non-obvious click sequence. Assume the Lt.
will glance at the page for a few seconds, not read the diff.

- Give every new feature an obvious on-page marker when it first ships --
  a visible label/badge (e.g. "NEW"), a highlighted border/glow, or
  equivalent -- so it's immediately findable without a tour. It's fine to
  remove the marker in a later pass once it's not new anymore.
- Prefer surfacing state as visible page content (a readout, a status
  line, a label) over anything the Lt. would need devtools to observe.
- When reporting a feature done, say where on the live page to look, not
  just that it works.

## POLICY: Security hardening is not the priority here

This is a single-operator demo project (see `docs/deployment.md`'s
"Known limitation, accepted for now" -- no command-token gate, full write
authority open to anyone who can reach the server, an explicit informed
choice). Don't gate shipping a feature on security review, auth, or
hardening work, and don't spend time flagging the already-accepted tradeoffs
in `docs/deployment.md` as if they were new findings. The priority is
making things actually run and be reachable (see the URL/port policy
above). If something looks like it would leak this machine's own secrets
(credentials, tokens, private keys) rather than just being an open demo
world, that's still worth a one-line flag -- but the general posture here
is ship it, don't audit it.
