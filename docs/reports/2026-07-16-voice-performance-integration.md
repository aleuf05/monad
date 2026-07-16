# Voice performance integration finding

## Existing foundation

The system does not need another character model. Living Fleet already owns the durable parts of character: seeded identity, bounded trait drift with reasons, relationships, reflection, recent narrative and purpose-scoped context bundles. Fleet posture/actions supply operational intent. `MonadVoice` already owns synthesis providers, voice profiles, fallback and playback lifecycle.

The missing seam was between those systems: a temporary performance state that translates character + current pressure + communicative intent into conservative provider controls, carries some state across turns, and explains its choice.

## Emerging path

`Living Fleet identity/context -> performance direction -> MonadPerformance -> MonadVoice profile -> provider -> audio`

`MonadPerformance` is deliberately ephemeral. It does not write identity, infer new durable traits or rewrite spoken text. Its continuous axes are tension, warmth, energy and restraint; named intents are authoring conveniences that produce mixed targets, not exclusive emotional states. The output includes axes, targets, intent and reasons alongside rate/pitch/volume.

Living Captain is the first experiment. A normal status is a measured operational report; a custody rejection or exhausted spend boundary becomes controlled urgency. Repeated reports carry prior state, and the page visibly shows the current performance label, tension, energy and reasons.

## Missing primitives after this experiment

- A shared adapter from Living Fleet's real identity/context bundle into a performance direction. The demo currently supplies a conservative local captain baseline because Living Captain's intentionally minimal status API does not expose Fleet memory.
- A provider with richer controls than browser rate/pitch/volume. This layer can plan subtle performances, but Browser Speech cannot reliably render all of them.
- Session-aware persistence policy. Ephemeral page-session continuity is correct for the experiment; longer continuity should be derived from existing memory, not a second store.
- Listening evaluation fixtures covering recognizability, social meaning, transition quality and resistance to caricature across providers.
- Provenance metadata when licensed or consenting custom voices are added. No real-person imitation is part of this layer.

## Next smallest experiments

1. Feed three real Living Fleet context bundles through the planner—routine report, sustained pressure, recovery—and have listeners compare intended versus perceived attitude.
2. Add one richer synthesis provider behind `MonadVoice`, then compare the same stored plans against Browser Speech without changing character or context code.
3. Only after those results, project performance into Fleet Radio. Radio traffic discipline should remain independent; expressive delivery must not increase airtime or event announcements.

## Evidence

- `node toys/shared/test_performance.js` proves inertia, sustained pressure, gradual recovery, inspectability and bounded delivery.
- Existing `test_voice.js` remains green.
- `tools/check-toy-drift.py` reports source/live synchronization.
- Live HTTPS exposes the performance marker, planner script and versioned Living Captain client.
