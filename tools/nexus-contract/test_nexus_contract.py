"""Conformance tests for the Nexus Composition Contract (NEXUS-LUNCH-001).

The load-by-path preamble matches tools/mission-bus/test_mission_bus.py --
these tools are scripts under tools/, not an installed package.
"""
import importlib.util
import sys
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

P = Path(__file__).with_name("nexus_contract.py")
S = importlib.util.spec_from_file_location("nexus_contract", P)
n = importlib.util.module_from_spec(S)
# Register before exec_module: nexus_contract defines a @dataclass, and
# dataclasses resolves annotations via sys.modules[cls.__module__], which
# is None for a spec-loaded module that was never registered.
sys.modules[S.name] = n
S.loader.exec_module(n)


def sample(**overrides):
    fields = dict(
        identity={"id": "captain.claude", "kind": "agent"},
        intent={"objective": "prove the envelope crosses a component boundary"},
        authority={"grant": "admiral", "scope": "engineering-queue"},
        capability={"name": "nexus-contract", "version": "v0.1"},
        action={"verb": "scaffold", "target": "tools/nexus-contract/"},
        result={"status": "succeeded", "detail": "scaffold exists and verifies"},
    )
    fields.update(overrides)
    return n.NexusEnvelope.sealed(**fields)


class TestEnvelope(unittest.TestCase):
    def test_all_seven_fields_are_the_contract(self):
        self.assertEqual(
            n.FIELDS,
            ("identity", "intent", "authority", "capability", "action", "result", "evidence"),
        )
        env = sample()
        for name in n.FIELDS:
            self.assertTrue(getattr(env, name), f"{name} must be populated")

    def test_wire_round_trip_preserves_every_field(self):
        env = sample()
        back = n.NexusEnvelope.from_wire(env.to_wire())
        self.assertEqual(asdict(env), asdict(back))

    def test_missing_field_is_rejected_not_defaulted(self):
        payload = asdict(sample())
        del payload["authority"]
        import json
        with self.assertRaises(n.NexusError):
            n.NexusEnvelope.from_wire(json.dumps(payload))

    def test_incomplete_field_is_rejected(self):
        with self.assertRaises(n.NexusError):
            n.NexusEnvelope.sealed(
                identity={"id": "x"},  # missing "kind"
                intent={"objective": "o"},
                authority={"grant": "g", "scope": "s"},
                capability={"name": "c", "version": "v"},
                action={"verb": "a", "target": "t"},
                result={"status": "ok", "detail": "d"},
            )

    def test_tampering_breaks_the_evidence_digest(self):
        """Evidence is a check, not a claim: altering any covered field
        after sealing must fail verification on the receiving side."""
        import json
        payload = asdict(sample())
        payload["authority"]["grant"] = "admiral-forged"
        with self.assertRaises(n.NexusError) as caught:
            n.NexusEnvelope.from_wire(json.dumps(payload))
        self.assertIn("digest mismatch", str(caught.exception))

    def test_chain_answers_the_four_questions(self):
        chain = sample().chain()
        self.assertEqual(set(chain), {"requested", "permitted", "performed", "observed"})
        self.assertEqual(chain["requested"]["identity"]["id"], "captain.claude")
        self.assertEqual(chain["permitted"]["authority"]["grant"], "admiral")
        self.assertEqual(chain["performed"]["action"]["verb"], "scaffold")
        self.assertEqual(chain["observed"]["result"]["status"], "succeeded")


class TestComponentA(unittest.TestCase):
    """Component A is engineering-comms: a real, separately-tested validator."""

    def setUp(self):
        self.engcomms = n.load_engineering_comms()

    def test_component_a_message_becomes_a_valid_envelope(self):
        msg = self.engcomms.EngineeringMessage(
            type="command", authority="admiral", action="scaffold",
            target="tools/nexus-contract/", done_criteria="envelope crosses and reconstructs",
        )
        env = n.from_engineering_message(
            msg, actor="captain.claude", capability="nexus-contract", version="v0.1",
            status="succeeded", detail="done",
        )
        env.verify()
        # A's own authority vocabulary is transported, not re-invented.
        self.assertEqual(env.authority["grant"], "admiral")
        self.assertIn(env.authority["grant"], self.engcomms.VALID_AUTHORITY)
        self.assertEqual(env.authority["scope"], "engineering-queue")

    def test_component_a_rejects_malformed_before_sealing(self):
        bad = self.engcomms.EngineeringMessage(type="command", authority="admiral")
        with self.assertRaises(self.engcomms.ValidationError):
            n.from_engineering_message(
                bad, actor="x", capability="c", version="v", status="s", detail="d",
            )


class TestExchange(unittest.TestCase):
    """The success condition: two independently represented components
    exchange the envelope, and the receiver reconstructs the whole chain
    from its own storage alone."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.db = Path(self.dir.name) / "nexus.sqlite3"

    def tearDown(self):
        self.dir.cleanup()

    def test_receiver_reconstructs_all_seven_fields(self):
        out = n.demo(self.db)
        self.assertTrue(out["identical"], "reconstructed envelope differs from the one sent")
        self.assertEqual(out["digest_sent"], out["digest_reconstructed"])
        rebuilt = out["envelope_reconstructed"]
        for name in n.FIELDS:
            self.assertTrue(rebuilt.get(name), f"{name} did not survive the crossing")

    def test_receiver_stores_events_not_the_envelope(self):
        """If B stored the envelope whole, this test would prove nothing --
        so assert it genuinely decomposed into B's own event schema."""
        out = n.demo(self.db)
        self.assertEqual(
            out["stored_event_types"],
            ["mission_created", "capability_invoked", "result_observed"],
        )

    def test_reconstruction_answers_who_what_authority_capability_result(self):
        out = n.demo(self.db)
        chain = out["chain"]
        self.assertEqual(chain["requested"]["identity"]["id"], "captain.claude")
        self.assertIn("reconstructs", chain["requested"]["intent"]["objective"])
        self.assertEqual(chain["permitted"]["authority"]["grant"], "admiral")
        self.assertEqual(chain["performed"]["capability"]["name"], "nexus-contract")
        self.assertEqual(chain["performed"]["action"]["verb"], "scaffold")
        self.assertEqual(chain["observed"]["result"]["status"], "succeeded")
        self.assertTrue(chain["observed"]["evidence"]["digest"].startswith("sha256:"))

    def test_receiver_store_is_append_only(self):
        """The evidence is only worth something if it cannot be edited after
        the fact. Component B enforces that with SQLite triggers."""
        mb = n.load_mission_bus()
        n.demo(self.db)
        record = mb.Record(self.db, mission_id="mission.nexus-lunch-001",
                           correlation_id="run.nexus-lunch-001")
        with self.assertRaises(Exception):
            record.db.execute("DELETE FROM mission_events")
        with self.assertRaises(Exception):
            record.db.execute("UPDATE mission_events SET payload_json='{}'")

    def test_partial_record_refuses_to_reconstruct(self):
        """A truncated crossing must fail loudly, not hand back a plausible
        envelope with fields quietly missing."""
        mb = n.load_mission_bus()
        record = mb.Record(self.db, mission_id="mission.partial",
                           correlation_id="run.partial")
        env = sample()
        record.append("mission_created", {
            "identity": env.identity, "intent": env.intent,
            "authority": env.authority, "status": "created",
        })
        with self.assertRaises(n.NexusError) as caught:
            n.reconstruct(record)
        self.assertIn("does not reconstruct", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
