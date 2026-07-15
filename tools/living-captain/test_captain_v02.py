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

# Reuse the exact sight module instance captain.py already imported (via its
# own sys.path insertion), rather than loading a second, separate copy of
# sight.py -- two independently loaded copies of the same file define two
# distinct CustodyViolation classes, and assertRaises would silently fail to
# match the one captain.py actually raises.
sight = captain_module.sight


class LivingCaptainV02Test(unittest.TestCase):
    def test_custody_manifest_is_persisted_and_rejection_is_logged(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir)
            captain = captain_module.LivingCaptain.assemble(state_dir)

            state = json.loads((state_dir / "state.json").read_text())
            self.assertEqual(state["custody_manifest"], sight.custody_manifest())

            bad_captain = captain_module.LivingCaptain.assemble(
                state_dir,
                fleetcore_url="http://example.invalid/snapshot",
            )

            with patch("urllib.request.urlopen") as urlopen:
                with self.assertRaises(sight.CustodyViolation):
                    bad_captain.observe()

            urlopen.assert_not_called()
            actions = bad_captain.actions()
            self.assertEqual(actions[-1]["kind"], "custody_rejection")
            self.assertIn("blocked GET http://example.invalid/snapshot", actions[-1]["summary"])

    def test_spend_budget_persists_across_restart(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir)

            with patch.object(captain_module.sight, "fetch_fleetcore_snapshot") as fleetcore, patch.object(
                captain_module.sight, "fetch_world_intake_pending"
            ) as intake:
                fleetcore.return_value = {"tick": 7, "event_sequence": 11}
                intake.return_value = [{"id": "proposal-1"}]

                captain = captain_module.LivingCaptain.assemble(state_dir)
                captain.observe()
                self.assertEqual(captain.spend_status()["remaining_observes"], 0)

            reassembled = captain_module.LivingCaptain.assemble(state_dir)
            self.assertEqual(reassembled.spend_status()["remaining_observes"], 0)

            with self.assertRaises(captain_module.SpendBudgetExceeded):
                reassembled.observe()

            actions = reassembled.actions()
            self.assertEqual(actions[-1]["kind"], "spend_exhausted")
            self.assertEqual(
                reassembled.spend_status(),
                {"observe_count": 1, "observe_limit": 1, "remaining_observes": 0},
            )


if __name__ == "__main__":
    unittest.main()
