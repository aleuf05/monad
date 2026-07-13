# Seed doctrine: Living Fleet authoritative seam

Curated excerpt of `docs/architecture/living-fleet-v0.1.md`, imported as
doctrine belief material (not firsthand experience).

- Living Fleet adds intent above FleetCore's existing deterministic movement,
  not a second simulation: a captain provider proposes intent, FleetCore
  validates it and derives a deterministic station target, and both the
  decision and its consequence become durable, replayable records.
- Captains never submit a raw route. The bounded posture vocabulary is:
  hold-station, advance-screen, widen-flank, cover-rear, investigate-contact,
  recover-formation, emergency-separation.
- A target on known land is deterministically corrected to recover-formation
  by FleetCore itself -- a captain's proposed posture is a request, not a
  guarantee of exact execution.
- If the captain runtime stops entirely, an intent simply expires at its own
  reconsider_at_tick and FleetCore resumes ordinary deterministic escort
  movement. No inference outage ever stops the world clock.
