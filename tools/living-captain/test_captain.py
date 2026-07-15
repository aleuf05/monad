import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).parent

spec = importlib.util.spec_from_file_location("captain", ROOT / "captain.py")
captain_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(captain_module)

spec = importlib.util.spec_from_file_location("action_log", ROOT / "action_log.py")
action_log = importlib.util.module_from_spec(spec)
spec.loader.exec_module(action_log)


class LivingCaptainTest(unittest.TestCase):
    def test_record_proposal_appends_proposal_note(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir)
            captain = captain_module.LivingCaptain.assemble(
                state_dir,
                fleetcore_url="http://example.invalid/snapshot",
                world_intake_url="http://example.invalid/proposals",
            )

            with patch.object(captain_module.sight, "fetch_fleetcore_snapshot") as fleetcore, patch.object(
                captain_module.sight, "fetch_world_intake_pending"
            ) as intake:
                fleetcore.return_value = {
                    "tick": 17,
                    "event_sequence": 42,
                }
                intake.return_value = [{"id": "proposal-1"}]

                observation = captain.observe()
                proposal = captain.record_proposal(
                    "Hold the line while review catches up.",
                    detail={"pending": 1},
                )

            self.assertEqual(observation["kind"], "observation")
            self.assertEqual(proposal["kind"], "proposal_note")
            self.assertEqual(proposal["detail"], {"pending": 1})
            self.assertEqual(captain.actions()[0]["kind"], "observation")
            self.assertEqual(captain.actions()[1]["kind"], "proposal_note")

            state_path = state_dir / "state.json"
            persisted = json.loads(state_path.read_text())
            self.assertEqual(persisted["last_seen_fleetcore_tick"], 17)
            self.assertEqual(persisted["last_seen_world_intake_pending_count"], 1)


if __name__ == "__main__":
    unittest.main()
