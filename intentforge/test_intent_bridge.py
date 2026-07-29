import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from bracket_generator import generate_fan_mount_bracket
from intent_bridge import (
    IntentBridgeError,
    UnresolvedIntentError,
    compile_fan_mount_intent,
    propose_fan_bracket_translation,
)
from mesh import write_binary_stl


ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"
EXPECTED_STL_SHA256 = "b740c05d18bb8bf975ec76db5d5bfed03ab9f45384aae4795da1409b978c2757"


class TestIntentLanguageBridge(unittest.TestCase):
    def setUp(self):
        self.export = json.loads((FIXTURES / "fan-bracket-language-export-v0.1.json").read_text())
        self.resolution = json.loads((FIXTURES / "fan-bracket-measurements-v0.1.json").read_text())

    def resolved_proposal(self):
        return propose_fan_bracket_translation(self.export, self.resolution)

    def test_unresolved_language_refuses_geometry(self):
        proposal = propose_fan_bracket_translation(self.export)
        self.assertFalse(proposal.ready_to_compile)
        self.assertIn("physical units", proposal.unresolved)
        self.assertIn("keep-out physical representation and dimensions", proposal.unresolved)
        with self.assertRaises(UnresolvedIntentError):
            compile_fan_mount_intent(proposal)

    def test_demo_pixels_never_become_physical_values(self):
        proposal = self.resolved_proposal()
        self.assertEqual(proposal.source_coordinate_space, "demo-stage-640x400")
        keep_out_mapping = next(item for item in proposal.mappings if item["source"] == "gesture:keep-out")
        self.assertIn("provenance only", keep_out_mapping["value_source"])
        compiled = compile_fan_mount_intent(proposal)
        trace = next(item for item in compiled.feature_trace if item["feature"] == "cable-clearance edge notch")
        self.assertFalse(trace["source_samples_are_dimensions"])
        self.assertEqual(compiled.intent.cable_notch.width, self.resolution["keep_out"]["width"])

    def test_unreviewed_teaching_episode_is_rejected(self):
        broken = copy.deepcopy(self.export)
        broken["entries"][0]["source_episode"]["human_review"]["reviewed"] = False
        with self.assertRaisesRegex(IntentBridgeError, "explicit human review"):
            propose_fan_bracket_translation(broken)

    def test_units_must_be_explicit_millimetres(self):
        broken = copy.deepcopy(self.resolution)
        broken["units"] = "pixels"
        with self.assertRaisesRegex(IntentBridgeError, "millimetre units"):
            propose_fan_bracket_translation(self.export, broken)

    def test_private_phrase_cannot_silently_become_a_parameter(self):
        broken = copy.deepcopy(self.resolution)
        broken["private_meaning_dispositions"][0]["disposition"] = "converted-to-clearance"
        with self.assertRaisesRegex(IntentBridgeError, "cannot consume"):
            propose_fan_bracket_translation(self.export, broken)

    def test_review_scope_cannot_claim_physical_authority(self):
        broken = copy.deepcopy(self.resolution)
        broken["review_decision"]["physical_authority"] = True
        with self.assertRaisesRegex(IntentBridgeError, "cannot claim physical authority"):
            propose_fan_bracket_translation(self.export, broken)

    def test_exact_contract_mapping(self):
        compiled = compile_fan_mount_intent(self.resolved_proposal())
        intent = compiled.intent
        self.assertEqual((intent.envelope.width, intent.envelope.height, intent.envelope.thickness), (70.0, 70.0, 3.0))
        self.assertEqual([(hole.cx, hole.cy, hole.diameter) for hole in intent.existing_holes], [
            (-25.0, 25.0, 4.5),
            (25.0, 25.0, 4.5),
        ])
        self.assertEqual(intent.fan_center, (0.0, -5.0))
        self.assertEqual(intent.fan_bolt_spacing, 32.0)
        self.assertEqual(intent.fan_airflow_diameter, 34.0)
        self.assertEqual(intent.cable_notch.edge, "south")
        self.assertEqual(intent.cable_notch.center_offset, -22.0)

    def test_feature_trace_covers_every_generated_feature_class(self):
        compiled = compile_fan_mount_intent(self.resolved_proposal())
        features = {item["feature"] for item in compiled.feature_trace}
        self.assertEqual(features, {
            "outer plate envelope",
            "existing mounting hole 1",
            "existing mounting hole 2",
            "fan bolt pattern and airflow opening",
            "cable-clearance edge notch",
            "minimum wall thickness",
            "private phrase disposition",
        })
        phrase_trace = next(item for item in compiled.feature_trace if item["feature"] == "private phrase disposition")
        self.assertEqual(phrase_trace["generator_effect"], "none")

    def test_integrated_geometry_matches_inherited_deterministic_stl(self):
        compiled = compile_fan_mount_intent(self.resolved_proposal())
        mesh, status, _ = generate_fan_mount_bracket(compiled.intent)
        self.assertTrue(mesh.is_watertight())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "integrated.stl"
            write_binary_stl(mesh, str(path))
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(digest, EXPECTED_STL_SHA256)
        self.assertTrue(status.geometry_proposed)
        self.assertTrue(status.constraints_checked)

    def test_all_physical_evidence_states_remain_false(self):
        compiled = compile_fan_mount_intent(self.resolved_proposal())
        _, status, _ = generate_fan_mount_bracket(compiled.intent)
        status_dict = status.as_dict()
        for field, expected in compiled.truth_boundary.items():
            self.assertIs(status_dict[field], expected)


if __name__ == "__main__":
    unittest.main()
