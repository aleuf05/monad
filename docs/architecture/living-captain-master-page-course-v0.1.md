# Living Captain Master Page — Course v0.1

Status: Active implementation course; not canon by self-declaration  
Authority: Admiral direction, 2026-08-05  
Target: Existing `web/` front page and `/root/` Root Console

## Bold vision

Monad has one front door and one central operational presence: Living Captain.
Public and Root are not separate products. They are authority-shaped views of
one vessel. Instruments remain real and independently inspectable, but they
become capabilities Living Captain can see, explain, and operate rather than a
museum of disconnected links.

The Master Page answers four questions immediately:

1. Is the ship alive?
2. Is the Captain present?
3. What is happening now?
4. What can this viewer legitimately do next?

## Boundary already proved

Automatic selection by source IP is not reliable on the current router.
Hairpin NAT rewrites LAN traffic so it is indistinguishable from public
traffic at Caddy. Do not retry that mechanism without new network evidence.

Automatic capability detection is reliable: probe the authenticated Root
Console status boundary. A successful response means Root view is available;
an authentication response means the viewer remains Public. Detection reveals
no private content and never grants authority.

## Course

### Phase 1 — One identity, two views (engaged)

- Make `/` visibly the Monad Master Page.
- Put Living Captain at the center of the public hierarchy.
- Add a Public ↔ Root switch and Root-capability detection.
- Add the matching return control to Root.
- Preserve every existing URL and working instrument.

### Phase 2 — Captain surface

- Promote live conversation, Live Bridge, event sonification, current course,
  and Captain presence into the first screen of Root.
- Replace implementation-era labels with human command language.
- Keep raw telemetry available one layer down, not dominant.

**First slice shipped, 2026-08-05.** Root view now presents five Captain
stations over the existing live controls:

- **Bridge** — default full-width conversation, voice, Live Bridge, and barge-in.
- **Course** — dispatch, handoffs, Ship's Log, and M³ revision controls.
- **Intake** — the real Packet Drop workflow.
- **Research** — Semantic Text Metamorphosis plus the transition path to the
  still-working Research Cockpit.
- **Systems** — raw live execution telemetry and activity history.

This is attention-level integration, not copied functionality. Every station
uses the same DOM control and backend it used before the navigation change.

### Phase 3 — Capabilities become Captain modules

Move functions gradually, in this order:

1. Current course, alerts, and handoffs.
2. Conversation, voice, and interruption controls.
3. Documents, packet intake, and review.
4. Research cockpit and experiment state.
5. World/Fleet instruments and asset pipelines.

Each move must reuse the existing backend and canonical data source. No shadow
routes, copied state, or replacement services.

### Phase 4 — Continuity as the navigation model

- Let Living Captain explain what changed since the last visit.
- Present observed state, inference, pending decisions, and uncertainty as
  distinct layers.
- Make every major action recoverable and provenance-linked.

### Phase 5 — One vessel across devices

- Preserve the same Captain identity and course across desktop, phone, and
  future bridge hardware.
- Adapt interaction density to the device without creating separate Captains.
- Graduate continuous speech only after human acceptance under realistic use.

## Migration law

A function moves into Living Captain only when its real source, controls,
failure state, evidence, and rollback remain inspectable. Visual consolidation
without operational integration does not count.

## Next watch

Deepen **Course** first: assemble one Captain-readable current-course view from
the existing handoff, Ship's Log, and M³ sources. Do not add a new state store.
Once Course is coherent, deepen Intake, then Research. Systems stays available
but subordinate.

**Operator watch shipped, 2026-08-05.** Fleetnet now emits stable, actionable
alerts rather than periodic status theater. It checks installed Monad units,
five endpoint-specific contracts, monitored tests, disk, memory, load, and
voice observability. Each alert carries severity, evidence, and operator
action. The Master Page renders the watch directly; audio announces new or
changed alerts and closes recoveries. Healthy protected endpoints returning
401 are correctly distinguished from failure. This is the first operational
Course capability integrated into the Living Captain surface.

**Bridge command rail shipped, 2026-08-05.** The default Bridge view now keeps
four command facts visible above conversation: Captain action, operator watch,
human gate, and latest continuity handoff. An authenticated `/api/course`
projection assembles these from the existing Fleetnet, Watch Officer, speech
acceptance, handoff, and Ship's Log sources. It owns no state and writes
nothing. The detailed Course station consumes the same projection rather than
performing a second client-side interpretation. Alert recovery takes priority;
on a clear watch the next Captain action advances the declared Living Captain
course while a human-only acceptance gate remains visibly distinct and cannot
idle engineering.

## Celebration discipline

Celebrate demonstrated capability loudly. Label unfinished integration just
as loudly. Momentum is real; narrative follows reality.
