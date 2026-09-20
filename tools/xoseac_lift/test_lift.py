import unittest

from lift import AddEdge, AddState, apply_lift, instance_from_dict


def example():
    return instance_from_dict({
        "x": {"kind": "finite-state-machine", "identifier": "demo"},
        "o": {"labels": ["input-a", "input-b"]},
        "s": {"states": ["idle", "ready"]},
        "e": {"edges": [["idle", "ready", "activate"]]},
        "a": {"actions": ["activate"]},
        "c": {"initial": "idle", "terminal": ["ready"]},
    })


class LiftTests(unittest.TestCase):
    def test_boundary_rejects_malformed_instance(self):
        bad = {**example().to_dict(), "e": {"edges": [["idle", "missing", "bad"]]}}
        with self.assertRaises(ValueError):
            instance_from_dict(bad)

    def test_legal_s_mutation_emits_successor_and_trace(self):
        result = apply_lift(example(), AddState("paused"))
        self.assertTrue(result.accepted)
        self.assertEqual(result.before.s.states, ("idle", "ready"))
        self.assertEqual(result.successor.s.states, ("idle", "ready", "paused"))
        self.assertEqual(result.successor.e.edges, example().e.edges)
        self.assertEqual(result.provenance[-1].phase, "causal")
        self.assertEqual(result.provenance[-1].data["changed_component"], "s")

    def test_legal_e_mutation_emits_successor_and_trace(self):
        result = apply_lift(example(), AddEdge("ready", "idle", "reset"))
        self.assertTrue(result.accepted)
        self.assertIn(("ready", "idle", "reset"), result.successor.e.edges)
        self.assertEqual(result.provenance[-1].data["changed_component"], "e")

    def test_illegal_e_mutation_is_rejected_without_successor(self):
        result = apply_lift(example(), AddEdge("ready", "unknown", "broken"))
        self.assertFalse(result.accepted)
        self.assertEqual(result.before.e.edges, example().e.edges)
        self.assertIsNone(result.successor)
        self.assertIn("absent from S", result.error)
        self.assertEqual(result.provenance[-1].phase, "rejection")

    def test_trace_contains_before_and_after_digests(self):
        result = apply_lift(example(), AddState("paused"))
        boundary = result.provenance[0]
        successor = next(event for event in result.provenance if event.phase == "successor")
        self.assertEqual(len(boundary.data["before_digest"]), 64)
        self.assertEqual(len(successor.data["after_digest"]), 64)


if __name__ == "__main__":
    unittest.main()
