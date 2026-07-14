"""Tests for the schema-governed communication system (2026-07-14
implementation directive). Required before operational release, per the
directive's own "verify the system through defined tests" line.

Run: python3 -m unittest tools/engineering-comms/test_schema.py
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from schema import EngineeringMessage, ValidationError, process, read_record, route, validate  # noqa: E402


class ValidCommandTests(unittest.TestCase):
    def test_well_formed_command_validates(self):
        msg = EngineeringMessage(
            type="command", authority="lieutenant",
            action="fix", target="tools/world-intake/world_intake.py",
            done_criteria="submission path reaches FleetCore, tests pass",
        )
        validate(msg)  # does not raise

    def test_well_formed_command_routes_to_engineering_queue(self):
        msg = EngineeringMessage(
            type="command", authority="lieutenant",
            action="fix", target="x", done_criteria="y",
        )
        self.assertEqual(route(msg), "engineering-queue")


class MalformedCommandTests(unittest.TestCase):
    def test_missing_action_is_rejected(self):
        msg = EngineeringMessage(type="command", target="x", done_criteria="y")
        with self.assertRaises(ValidationError) as ctx:
            validate(msg)
        self.assertIn("action", ctx.exception.missing_fields)

    def test_missing_multiple_fields_lists_all_of_them(self):
        msg = EngineeringMessage(type="command")
        with self.assertRaises(ValidationError) as ctx:
            validate(msg)
        self.assertEqual(set(ctx.exception.missing_fields), {"action", "target", "done_criteria"})

    def test_unknown_type_is_rejected(self):
        msg = EngineeringMessage(type="mutiny", action="a", target="b", done_criteria="c")
        with self.assertRaises(ValidationError):
            validate(msg)

    def test_unknown_authority_is_rejected(self):
        msg = EngineeringMessage(type="command", authority="the_beast", action="a", target="b", done_criteria="c")
        with self.assertRaises(ValidationError):
            validate(msg)

    def test_question_without_body_is_rejected(self):
        msg = EngineeringMessage(type="question")
        with self.assertRaises(ValidationError):
            validate(msg)


class SafetyEscalationTests(unittest.TestCase):
    def test_safety_priority_always_routes_to_safety_escalation_regardless_of_type(self):
        for msg_type, kwargs in [
            ("status", {"body": "hull breach reported"}),
            ("command", {"action": "seal", "target": "bulkhead 4", "done_criteria": "sealed"}),
        ]:
            msg = EngineeringMessage(type=msg_type, priority="safety", **kwargs)
            self.assertEqual(route(msg), "safety-escalation")

    def test_normal_priority_status_routes_to_status_log_not_safety(self):
        msg = EngineeringMessage(type="status", body="all clear", priority="normal")
        self.assertEqual(route(msg), "status-log")


class RecordTraceabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.record_path = Path(self.tmp.name) / "record.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_message_is_recorded(self):
        msg = EngineeringMessage(type="command", action="fix", target="x", done_criteria="y")
        process(msg, self.record_path)
        records = read_record(self.record_path)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["message"]["action"], "fix")
        self.assertEqual(records[0]["destination"], "engineering-queue")

    def test_malformed_message_raises_and_is_never_recorded(self):
        msg = EngineeringMessage(type="command")  # missing everything
        with self.assertRaises(ValidationError):
            process(msg, self.record_path)
        self.assertEqual(read_record(self.record_path), [])

    def test_record_is_append_only_across_multiple_accepted_messages(self):
        for i in range(3):
            process(
                EngineeringMessage(type="command", action="fix", target=f"file-{i}", done_criteria="done"),
                self.record_path,
            )
        records = read_record(self.record_path)
        self.assertEqual(len(records), 3)
        self.assertEqual([r["message"]["target"] for r in records], ["file-0", "file-1", "file-2"])

    def test_a_rejected_message_does_not_disturb_prior_accepted_records(self):
        process(
            EngineeringMessage(type="command", action="fix", target="good", done_criteria="done"),
            self.record_path,
        )
        with self.assertRaises(ValidationError):
            process(EngineeringMessage(type="command"), self.record_path)
        records = read_record(self.record_path)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["message"]["target"], "good")


if __name__ == "__main__":
    unittest.main()
