import hashlib
import json
import unittest
from dataclasses import dataclass
from unittest.mock import patch

from lift import AddEdge, AddState, LiftedInstance, XOSEACInstance, apply_lift, instance_from_dict


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


class AdversarialLiftTests(unittest.TestCase):
    def test_extra_and_missing_top_level_components_rejected(self):
        raw = example().to_dict()
        with self.assertRaises(ValueError):
            instance_from_dict({**raw, "unexpected": {}})
        missing = dict(raw)
        del missing["a"]
        with self.assertRaises(ValueError):
            instance_from_dict(missing)

    def test_duplicate_state_insertion_rejected(self):
        result = apply_lift(example(), AddState("ready"))
        self.assertFalse(result.accepted)
        self.assertIsNone(result.successor)
        self.assertIn("duplicate state", result.error)

    def test_malformed_edges_rejected_at_boundary(self):
        raw = example().to_dict()
        raw["e"] = {"edges": [["idle", "ready"]]}
        with self.assertRaises(ValueError):
            instance_from_dict(raw)
        raw = example().to_dict()
        raw["e"] = {"edges": [["idle", "ready", "activate"], ["idle", "ready", "activate"]]}
        with self.assertRaises(ValueError):
            instance_from_dict(raw)

    def test_post_mutation_validator_rejects_invalid_successor(self):
        invalid = XOSEACInstance(
            x=example().x, o=example().o, s=example().s,
            e=type(example().e)((("idle", "missing", "broken"),)),
            a=example().a, c=example().c,
        )
        with patch.object(LiftedInstance, "instance", return_value=invalid):
            result = apply_lift(example(), AddState("paused"))
        self.assertFalse(result.accepted)
        self.assertIsNone(result.successor)
        self.assertIn("endpoint", result.error)
        self.assertEqual(result.provenance[-1].phase, "rejection")

    def test_provenance_is_ordered_and_digests_match_states(self):
        result = apply_lift(example(), AddEdge("ready", "idle", "reset"))
        self.assertEqual([event.sequence for event in result.provenance], list(range(len(result.provenance))))
        before_json = json.dumps(result.before.to_dict(), sort_keys=True, separators=(",", ":"))
        after_json = json.dumps(result.successor.to_dict(), sort_keys=True, separators=(",", ":"))
        self.assertEqual(result.provenance[0].data["before_digest"], hashlib.sha256(before_json.encode()).hexdigest())
        successor_event = next(event for event in result.provenance if event.phase == "successor")
        self.assertEqual(successor_event.data["after_digest"], hashlib.sha256(after_json.encode()).hexdigest())
        self.assertEqual([event.phase for event in result.provenance], ["boundary", "request", "mutation", "successor", "causal"])

    def test_mutation_of_unsupported_component_rejected(self):
        @dataclass(frozen=True)
        class ChangeObservation:
            label: str

        result = apply_lift(example(), ChangeObservation("new-observation"))
        self.assertFalse(result.accepted)
        self.assertIsNone(result.successor)
        self.assertIn("unsupported mutation type", result.error)
        self.assertEqual(result.provenance[-1].phase, "rejection")


if __name__ == "__main__":
    unittest.main()
