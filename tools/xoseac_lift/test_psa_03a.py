import unittest

from lift import (
    AddState,
    apply_self_application,
    execute_using_self_representation,
    is_self_representation,
    operative_instance,
    operative_source_digest,
)
from test_lift import example


class PSA03ATests(unittest.TestCase):
    def test_operational_self_target_is_generated_from_live_module(self):
        target = operative_instance()
        self.assertTrue(is_self_representation(target))
        self.assertEqual(target.x.implementation_digest, operative_source_digest())
        self.assertEqual(target.x.identifier, "tools.xoseac_lift.lift")

    def test_arbitrary_valid_instance_is_not_self_target(self):
        self.assertFalse(is_self_representation(example()))

    def test_self_application_permits_one_trivial_s_edit(self):
        target = operative_instance()
        result = apply_self_application(target, AddState("self-audit-marker"))
        self.assertTrue(result.accepted)
        self.assertIn("self-audit-marker", result.successor.s.states)
        self.assertEqual(result.before.to_dict(), target.to_dict())
        self.assertEqual(result.provenance[0].phase, "self-target")

    def test_self_edit_changes_subsequent_execution_observably(self):
        target = operative_instance()
        edited = apply_self_application(target, AddState("self-audit-marker")).successor
        baseline = execute_using_self_representation(target, example(), AddState("later"))
        changed = execute_using_self_representation(edited, example(), AddState("later"))
        self.assertTrue(baseline.accepted)
        self.assertTrue(changed.accepted)
        self.assertNotEqual(
            [event.phase for event in baseline.provenance],
            [event.phase for event in changed.provenance],
        )
        self.assertEqual(changed.provenance[-1].phase, "runtime")
        self.assertIn("altered subsequent execution", changed.provenance[-1].claim)

    def test_hand_authored_target_with_wrong_digest_is_rejected(self):
        target = operative_instance()
        forged = target.__class__(
            target.x.__class__(target.x.kind, target.x.identifier, "0" * 64),
            target.o, target.s, target.e, target.a, target.c,
        )
        self.assertFalse(is_self_representation(forged))
        result = apply_self_application(forged, AddState("self-audit-marker"))
        self.assertFalse(result.accepted)
        self.assertIn("does not represent", result.error)


if __name__ == "__main__":
    unittest.main()
