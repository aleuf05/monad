import tempfile
import unittest
from pathlib import Path

from memory import identity, store


class IdentityDriftTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "memory.db"
        self.conn = store.connect(self.db_path)
        identity.ensure_identity(self.conn, "captain.alpha", "Forward screen and reconnaissance")

    def tearDown(self):
        self.conn.close()
        self.tmp_dir.cleanup()

    def test_repeated_same_direction_proposals_never_exceed_bounds(self):
        for _ in range(200):
            identity.apply_trait_shift(self.conn, "captain.alpha", {"caution": 0.5}, reason="test", reflection_id="refl-x")
        row = store.fetch_one(self.conn, "identity_traits", "captain.alpha")
        self.assertLessEqual(row["traits_json"]["caution"], row["trait_bounds_json"]["caution"]["max"])

    def test_no_single_reflection_exceeds_max_delta(self):
        before = store.fetch_one(self.conn, "identity_traits", "captain.alpha")["traits_json"]["caution"]
        identity.apply_trait_shift(self.conn, "captain.alpha", {"caution": 10.0}, reason="test", reflection_id="refl-y")
        after = store.fetch_one(self.conn, "identity_traits", "captain.alpha")
        max_delta = after["trait_bounds_json"]["caution"]["max_delta_per_reflection"]
        self.assertLessEqual(after["traits_json"]["caution"] - before, max_delta + 1e-9)

    def test_drift_log_carries_reason_and_reflection_id(self):
        identity.apply_trait_shift(self.conn, "captain.alpha", {"humor": 0.1}, reason="reflection:major-success", reflection_id="refl-z")
        row = store.fetch_one(self.conn, "identity_traits", "captain.alpha")
        entry = row["drift_log_json"][-1]
        self.assertEqual(entry["reason"], "reflection:major-success")
        self.assertEqual(entry["reflection_id"], "refl-z")
        self.assertEqual(entry["trait"], "humor")

    def test_correction_applies_a_bounded_compensating_delta_not_an_overwrite(self):
        identity.apply_trait_shift(self.conn, "captain.alpha", {"trust": -0.06}, reason="reflection:x", reflection_id="refl-a")
        lowered = store.fetch_one(self.conn, "identity_traits", "captain.alpha")["traits_json"]["trust"]
        identity.apply_correction(self.conn, "captain.alpha", {"trust": 0.06}, reason="mistaken conclusion")
        row = store.fetch_one(self.conn, "identity_traits", "captain.alpha")
        self.assertGreater(row["traits_json"]["trust"], lowered)
        self.assertEqual(len(row["drift_log_json"]), 2)  # both the original shift and the correction are preserved


if __name__ == "__main__":
    unittest.main()
