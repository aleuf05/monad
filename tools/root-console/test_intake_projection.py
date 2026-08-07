import unittest

import intake_projection


class IntakeProjectionTests(unittest.TestCase):
    def test_combines_existing_services_and_prioritizes_cards(self):
        def fetch(url):
            if "pending" in url:
                return {"proposals": [
                    {"assertion_id": "a1", "subject": "Ada", "assertion_class": "assignment", "proposed_change": {"operation": "assign_role"}, "confidence": .9, "conflicts": [], "requires_individual_approval": False, "provenance": {"source_id": "s1"}},
                    {"assertion_id": "a2", "subject": "Vance", "assertion_class": "permission", "proposed_change": {"operation": "request_permission"}, "confidence": .8, "conflicts": [{"code": "authority"}], "requires_individual_approval": True, "provenance": {"source_id": "s1"}},
                ]}
            if "deferred" in url:
                return {"proposals": [{"assertion_id": "d1"}]}
            return {"entries": [{"name": "packet.md", "path": "docs/incoming/packet.md", "bytes": 12, "mtime": 1}]}
        result = intake_projection.build(fetch)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["world"]["pending"], 2)
        self.assertEqual(result["world"]["individual_approval"], 1)
        self.assertEqual(result["world"]["with_conflicts"], 1)
        self.assertEqual(result["packets"]["staged"], 1)

    def test_source_failure_is_degraded_not_false_empty(self):
        result = intake_projection.build(lambda url: (_ for _ in ()).throw(OSError("offline")))
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(set(result["errors"]), {"world_pending", "world_deferred", "packet_drop"})

    def test_bounded_cards_surface_individual_and_conflicting_proposals(self):
        routine = [
            {"assertion_id": f"routine-{index}", "subject": f"Routine {index}"}
            for index in range(7)
        ]
        conflict = {
            "assertion_id": "conflict",
            "subject": "Conflict",
            "conflicts": [{"code": "authority"}],
        }
        individual = {
            "assertion_id": "individual",
            "subject": "Individual",
            "requires_individual_approval": True,
        }

        def fetch(url):
            if "pending" in url:
                return {"proposals": routine + [conflict, individual]}
            return {"proposals": []} if "deferred" in url else {"entries": []}

        cards = intake_projection.build(fetch)["world"]["cards"]
        self.assertEqual([card["id"] for card in cards[:2]], ["individual", "conflict"])
        self.assertEqual(len(cards), 6)


if __name__ == "__main__":
    unittest.main()
