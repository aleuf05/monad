import unittest

from captain_runtime import DoctrineProvider, validate_decision


def snapshot(contact_distance=False):
    vessels = [
        {"id": "vessel.monad", "kind": "flagship", "callsign": "MONAD", "position": {"lat": 0, "lng": 0}},
        {"id": "vessel.scout-alpha", "kind": "scout", "callsign": "ALPHA", "position": {"lat": 0.02, "lng": 0}},
        {"id": "vessel.scout-bravo", "kind": "scout", "callsign": "BRAVO", "position": {"lat": 0, "lng": 0.02}},
    ]
    if contact_distance:
        vessels.append({"id": "contact.test", "kind": "passive-traffic", "callsign": "TEST", "position": {"lat": 0.03, "lng": 0}})
    own = vessels[1]
    return {
        "own_vessel": own,
        "flagship": vessels[0],
        "contacts": [item for item in vessels if item["kind"] == "passive-traffic"],
        "other_vessels": [item for item in vessels if item["id"] != own["id"]],
    }


class DoctrineProviderTests(unittest.TestCase):
    def test_alpha_advances_screen_without_contact(self):
        decision = DoctrineProvider().decide(
            snapshot(), {"captain_id": "captain.alpha"}, {}
        )
        self.assertEqual(decision["posture"], "advance-screen")

    def test_alpha_investigates_near_contact(self):
        decision = DoctrineProvider().decide(
            snapshot(contact_distance=True), {"captain_id": "captain.alpha"}, {}
        )
        self.assertEqual(decision["posture"], "investigate-contact")
        self.assertEqual(decision["target_contact_id"], "contact.test")

    def test_invalid_provider_posture_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_decision({"posture": "teleport", "objective": "x", "assessment": "y"})


if __name__ == "__main__":
    unittest.main()
