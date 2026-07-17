# Agent Registry V0.1

Priority: Medium

Scope: A derived report, not a new live service or a formal schema
enforced anywhere.

Doctrine: `docs/reports/2026-07-15-feature-matrix.md`'s `AG-01` row split
message validation/routing (verified existing, `tools/engineering-comms/`)
from a per-agent registry (confirmed absent — "no stored identity/role/
runtime/authority-envelope/tool-access/assignment/status/memory-rules/
cost-record/activity-record/failure-history per agent anywhere in the
repo"). This order closes the activity/status/assignment half with real
data; the rest (cost-record, enforced tool-access, memory-rules) has no
real, non-fabricated data source yet and is explicitly deferred, not
faked.

## Why this is derived from packets, not git

Every commit in this repository is authored under one local git identity
(`Cameron Lampley <cgl@granite.local>` or similar) regardless of which
agent — Claude, Codex — actually made it, confirmed directly (`git log
--format='%an <%ae>'` shows a single identity across 400+ commits from
both agents). Git authorship cannot answer "which agent did this," so it
isn't the registry's data source.

`docs/engineering-orders/packets/*.md` can: every packet self-declares an
`Assigned actor` (Master Packet §13, field 8) and an `Evidence and
completion state` (field 9), and this convention is used consistently —
33 real packets exist as of this order, 32 with a parseable actor. This
registry is built entirely from that self-declared record, not inferred
or guessed from anything else.

## What `tools/agent-registry/build_registry.py` does

Parses every packet in `docs/engineering-orders/packets/` (excluding
`README.md` and `template-refused.md`, which are process documentation,
not work records), tolerating the two real formatting conventions found
in the wild — the current numbered-list style (29 of 33 real packets)
and an older `## Heading` style (4 of 33) — and extracts:

- **Actor(s)**: regex-matched against `Claude`, `Codex`, `Lieutenant` in
  the `Assigned actor` section text. A packet can name more than one (the
  two-bot Radio packets name both; several voice packets name Codex for
  implementation plus Lieutenant for a privileged commissioning step).
- **Completion state**: `complete` / `in-progress` / `queued` / `refused`
  / `unknown`, pattern-matched against the `Evidence and completion
  state` text. Refusal is detected once, reliably, from the
  `*-REFUSED.md` filename / `[REFUSED]` title convention — never from
  text search, after a real false positive (below) proved text search
  for "refused" is unsafe.
- **First/last touched**: `git log --follow` on the packet file's own
  path — real timestamps for when the *packet document* was created and
  last edited, which is honest data even though it can't attribute
  authorship of the underlying work.

## Two real false positives, found and fixed before trusting this

Caught by directly inspecting the generated report against known ground
truth before writing this doc, not assumed correct from passing code:

1. An early version matched the word `"refused"` anywhere in a packet's
   evidence text. `DOCTRINE-001`'s own evidence cites `ENG1-REFUSED.md`
   as a real-time proof-of-use example ("the ENG-1 packet ... was refused
   using exactly this doctrine's standard") — a packet *describing*
   another packet's refusal is not itself refused. Fixed by dropping text
   search for refusal entirely in favor of the filename/title convention.
2. A later version matched `"claimed"` anywhere in the text as a weak
   "in-progress" signal. `DOCTRINE-001`'s evidence also says `BR-01` "was
   deliberately closed before switching to this packet rather than **left
   claimed** mid-work" — describing good process discipline on a
   *different* packet, not that `DOCTRINE-001` itself is still claimed.
   Fixed by restricting single-word weak signals (`claimed`, `building`,
   `executing`, `authorized`, `assigned`, `succeeded`) to a 60-character
   prefix window right after the section heading, where this repo's own
   convention actually places a real terminal-state word — full-text
   search is only used for multi-word phrases distinctive enough to be
   safe (`"verified complete"`, `"complete and recorded"`, `"landed in
   commit"`).

A handful of older, bullet-list-evidence packets (`DOCTRINE-001`,
`LC-STATUS-01`, and `MISSION-REVIEW-PROJECTION-1.0`, all real work with
real evidence, just no prose "Completion state:" opener) now correctly
report `unknown` rather than a forced guess. That's the honest outcome of
a parser without a confident signal, not a bug to paper over with a more
aggressive heuristic.

## Output

`docs/reports/2026-07-17-agent-registry.md` — a per-agent breakdown
(packet count, status counts, a table of every packet with status and
first/last-touched dates) plus an explicit "what this registry does not
cover" section. Linked from `web/ops.html`'s existing "Report Queue —
Findings" group (the same phone-readable doc-reader every other report in
this repo already uses) — this is meta-information about how the repo's
own engineering process runs, not a Fleet Monad narrative feature, so it
belongs in the ops surface, not a new public toy.

Regenerate with `python3 tools/agent-registry/build_registry.py` whenever
new packets land; not on a cron cycle, since packets change on the order
of hours/days, not minutes, matching how `docs/reports/*.md` documents
have always been produced (an agent runs the synthesis, not a service).

## Deferred (explicitly not in V0.1)

- **Cost/spend per agent.** No cross-system ledger exists. The one real
  spend ledger in this repo, `data/voice-engine/voice.sqlite3`'s `spend`
  table, is scoped to voice generation specifically (not per-agent), and
  empty at last check — nothing to attribute yet even if it were wired
  in.
- **Enforced tool-access / authority envelopes.** Packets document scope
  and exclusions in prose ("Bot 1 owns radio-console files"), which
  humans and agents are expected to honor. There's no runtime mechanism
  that actually prevents a violation, and building one is a much larger
  project than a reporting tool.
- **Memory rules.** Doesn't map onto Claude/Codex the way it does to
  in-fiction Living Fleet captains (`tools/living-fleet/memory/`); not
  attempted here.
- **Work-queue-only tasks** (`docs/engineering-orders/queue.md`) that
  never became a full packet. By design, per `packets/README.md`'s own
  distinction: synthesis/verification/documentation work with no
  runtime/repository-state change doesn't need a packet, so it has no
  structured actor/completion record for this registry to read.
