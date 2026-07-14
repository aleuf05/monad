import unittest

from memory.salience import disposition_for, score_event


class SalienceTests(unittest.TestCase):
    def test_routine_telemetry_is_discarded(self):
        event = {
            "captain_id": "captain.alpha",
            "kind": "event",
            "category": "telemetry",
            "summary": "Routine position update.",
            "who": [],
            "payload": {},
        }
        recent = [dict(event) for _ in range(10)]  # this category has happened a lot lately
        score, factors = score_event(event, recent, [])
        self.assertEqual(disposition_for(score, factors), "discard")

    def test_near_collision_scores_high_and_forces_reflection(self):
        event = {
            "captain_id": "captain.alpha",
            "kind": "event",
            "category": "near-collision",
            "summary": "Nearest vessel closed to dangerous range.",
            "who": ["captain.alpha"],
            "payload": {"nearest_distance_m": 220, "posture": "emergency-separation"},
        }
        score, factors = score_event(event, [], [])
        self.assertGreaterEqual(factors["danger"], 0.9)
        self.assertEqual(disposition_for(score, factors), "episodic+reflect")

    def test_mission_complete_scores_high_via_social_and_narrative_factors(self):
        event = {
            "captain_id": "captain.alpha",
            "kind": "decision",
            "category": "mission-complete",
            "summary": "Rendezvous hold complete with QUACKEN, mission success.",
            "who": ["captain.alpha", "lieutenant.cgl"],
            "payload": {"outcome": "success"},
            "tags": ["quacken", "mission-complete"],
        }
        score, factors = score_event(event, [], [])
        self.assertGreater(factors["absurdity"], 0)
        self.assertGreater(factors["social_importance"], 0)
        # A Lieutenant-witnessed, QUACKEN-tagged mission completion must
        # reliably become a durable, reflect-worthy memory -- not merely
        # "summarized" -- even though no single weighted factor dominates.
        self.assertEqual(disposition_for(score, factors), "episodic+reflect")


if __name__ == "__main__":
    unittest.main()
