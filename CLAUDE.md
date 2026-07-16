# HIGHEST PRIORITY

Read [`000_HIGHEST_PRIORITY_MONAD_CHARTER_2026-07-14.md`](000_HIGHEST_PRIORITY_MONAD_CHARTER_2026-07-14.md) before taking action in this repository.

## POLICY: Bold, rapid, workflow-improving execution

Prefer rapid, reversible implementation over exhaustive validation. Use the
smallest test set that gives reasonable confidence. Avoid repeated
re-checking unless a failure or ambiguity appears. Make localized changes,
commit early, and leave deeper hardening for a later pass. Flag risks
briefly, but do not block progress on low-risk issues. Do not spend more
time proving a change works than implementing it, unless the change affects
security, persistence, or shared state.

Take bold steps. When a task surfaces friction in the workflow itself --
a broken permission, a missing tool, a doc that no longer matches reality,
a manual step that should be automated -- fix or flag it as part of the
work rather than working around it quietly every time. Small, reversible
process improvements don't need a separate mandate to justify making them
alongside the task that revealed them.

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

- Every feature must be reachable by clicking through from the site root
  (`https://cameronlampley.com/`) -- a link on the homepage, or a link
  reachable from a link on the homepage, and so on. Typing a specific path
  from memory or a doc doesn't count as reachable, no matter how "clean"
  the URL is. If you ship something new, add the nav link/card that gets a
  visitor there by clicking, in the same pass -- not as a follow-up.
- No URL prefix other than the bare `https://cameronlampley.com/` root
  serves the app -- not `/monad/`, not any other segment. The old `/monad/`
  prefix is fully retired (see `docs/deployment/public-hatch.md`) and its
  Caddy routes are gone, confirmed 404 as of 2026-07-13. The one deliberate
  exception is `/monad/portainer/*` -- operator infrastructure, not part of
  the app, under standing protection ("the Portainer reverse proxy path
  must not be disturbed"). Don't recreate a second prefix/path for
  anything new; everything else lives at the bare root.
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

Optimize for the moment the Lt. actually sits down to test something: he
should never have to hunt, guess a path, or ask "where is it." Every new
or changed thing should be the obvious, easy thing to find and click on
from the page he lands on -- that's the whole point of the click-reachable
and on-page-marker rules below, not separate concerns from this one.

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

## POLICY: Work queue / report queue for non-privileged work

Two locations, kept strictly separate -- see [`AGENTS.md`](AGENTS.md)
for the full policy and claim protocol:

- **Work queue** -- [`docs/engineering-orders/queue.md`](docs/engineering-orders/queue.md).
  Active/blocked tasks only. Check this before starting non-privileged,
  git-only work so a Claude session doesn't duplicate or silently drop
  work another agent (e.g. Codex) already claimed. When a task is
  done, its entry is deleted from here, not marked done in place.
- **Report queue** -- not a separate file. It's `docs/reports/*.md`,
  the Feature Matrix, and `docs/doctrine/*.md`, where completed
  findings and evidence actually live.

One-line rule: action lives in the work queue; truth lives in the
report queue. Privileged work stays exclusively in `cmd.sh` per
`docs/commissioning-handoff.md` -- neither queue covers that.

## POLICY: One source of truth -- don't replicate it

Admiral's ruling, 2026-07-15 (see `LS-01`'s resolution in
`docs/reports/2026-07-15-inadequate-specs.md`): this project runs on a
single live database/state store per concern, deliberately. Don't
propose or build replication, backup daemons, or standby copies as a
default hygiene measure -- if a real need shows up (a specific
incident, a stated recovery requirement), it gets evaluated on its
merits then, not assumed as good practice now. Matches this repo's
existing "no staging, `web/` is production" posture: one source of
truth, not several copies to keep in sync.
