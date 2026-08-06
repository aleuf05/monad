import tempfile
import unittest
from pathlib import Path

import wardroom


class Args:
    pass


class WardroomClerkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ledger = Path(self.temp.name) / "meeting.jsonl"
        a = Args(); a.ledger = self.ledger; a.meeting = "Test"; a.purpose = "Decide"; a.muster = "Admiral · Captain"
        wardroom.command_init(a)

    def tearDown(self):
        self.temp.cleanup()

    def candidate(self):
        a = Args(); a.ledger = self.ledger; a.candidate_id = "RG-01"; a.text = "Bounded rule"; a.scope = "Test"; a.destination = "Doctrine 030"; a.explanation = "Explains the candidate."
        wardroom.command_candidate(a)

    def test_ledger_is_append_only_and_sequenced(self):
        a = Args(); a.ledger = self.ledger; a.kind = "observation"; a.text = "Observed"; a.evidence = None; a.explanation = "Explains the observation."
        wardroom.command_add(a)
        data = wardroom.events(self.ledger)
        self.assertEqual([1, 2], [event["seq"] for event in data])
        self.assertEqual("UNVERIFIED", data[1]["evidence"])

    def test_unknown_candidate_cannot_be_ruled(self):
        a = Args(); a.ledger = self.ledger; a.candidate_id = "missing"; a.ruling = "CANON"; a.authority = "Admiral"; a.note = ""; a.explanation = "Explains the ruling."
        with self.assertRaises(SystemExit):
            wardroom.command_rule(a)

    def test_readback_separates_rulings_actions_and_gates(self):
        self.candidate()
        r = Args(); r.ledger = self.ledger; r.candidate_id = "RG-01"; r.ruling = "HOLD"; r.authority = "Admiral"; r.note = ""; r.explanation = "Explains why the candidate is held."
        wardroom.command_rule(r)
        a = Args(); a.ledger = self.ledger; a.owner = "Captain"; a.text = "Test"; a.acceptance = "Evidence"; a.explanation = "Explains the action."
        wardroom.command_action(a)
        text = wardroom.readback(wardroom.events(self.ledger))
        self.assertIn("RG-01 — HOLD", text)
        self.assertIn("Captain", text)

    def test_adjournment_refuses_unresolved_candidate(self):
        self.candidate()
        a = Args(); a.ledger = self.ledger; a.authority = "Admiral"; a.note = ""; a.allow_unresolved = False
        with self.assertRaises(SystemExit):
            wardroom.command_adjourn(a)

    def test_readback_hides_resolved_gate(self):
        a = Args(); a.ledger = self.ledger; a.kind = "gate"; a.text = "Need ruling"; a.evidence = "Meeting"; a.explanation = "Explains the gate."
        wardroom.command_add(a)
        gate = Args(); gate.ledger = self.ledger; gate.seq = 2; gate.authority = "Admiral"; gate.note = "Ruling supplied"; gate.explanation = "Explains why the gate is resolved."
        wardroom.command_resolve_gate(gate)
        self.assertNotIn("Need ruling", wardroom.readback(wardroom.events(self.ledger)))

    def test_readback_separates_superseded_disposition(self):
        self.candidate()
        r = Args(); r.ledger = self.ledger; r.candidate_id = "RG-01"; r.ruling = "SUPERSEDED"; r.authority = "Captain"; r.note = "Replaced"; r.explanation = "Explains the supersession."
        wardroom.command_rule(r)
        text = wardroom.readback(wardroom.events(self.ledger))
        self.assertIn("## Historical dispositions", text)
        self.assertNotIn("RG-01 — SUPERSEDED", text.split("## Historical dispositions")[0])

    def test_explanation_event_repairs_legacy_event_without_rewriting_it(self):
        a = Args(); a.ledger = self.ledger; a.kind = "observation"; a.text = "Legacy"; a.evidence = "Meeting"; a.explanation = ""
        wardroom.command_add(a)
        explanation = Args(); explanation.ledger = self.ledger; explanation.seq = 2; explanation.explanation = "This explains the legacy event."
        wardroom.command_explain(explanation)
        data = wardroom.events(self.ledger)
        self.assertEqual("Legacy", data[1]["text"])
        self.assertIn("All durable events", wardroom.readback(data))

    def test_packet_export_combines_context_readback_and_evidence(self):
        a = Args(); a.ledger = self.ledger; a.kind = "observation"; a.text = "Observed"; a.evidence = "Fixture"; a.explanation = "Explains the observation."
        wardroom.command_add(a)
        output = Path(self.temp.name) / "packet.md"
        args = Args(); args.ledger = self.ledger; args.output = output
        wardroom.command_export(args)
        text = output.read_text(encoding="utf-8")
        self.assertIn("# Meeting Packet — Test", text)
        self.assertIn("#2 · meeting_record", text)
        self.assertIn("## Evidence trail", text)


if __name__ == "__main__":
    unittest.main()
