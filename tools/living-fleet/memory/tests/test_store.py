import tempfile
import unittest
from pathlib import Path

from memory import store
from memory.models import now


class StoreRestartContinuityTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "memory.db"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_rows_survive_a_fresh_connection(self):
        conn = store.connect(self.db_path)
        store.insert(
            conn,
            "semantic_beliefs",
            {
                "belief_id": "bel-test-1",
                "captain_id": "captain.alpha",
                "subject": "self.role",
                "statement": "Test belief",
                "belief_type": "fact",
                "confidence": 1.0,
                "evidence_json": [],
                "provenance": "observed",
                "status": "active",
                "supersedes_belief_id": None,
                "superseded_by_belief_id": None,
                "revision_reason": None,
                "created_at": now(),
                "updated_at": now(),
            },
        )
        conn.close()

        # A brand new connection against the same path (simulating a
        # process restart) must see exactly what was written before.
        conn2 = store.connect(self.db_path)
        row = store.fetch_one(conn2, "semantic_beliefs", "bel-test-1")
        conn2.close()
        self.assertIsNotNone(row)
        self.assertEqual(row["statement"], "Test belief")
        self.assertEqual(row["evidence_json"], [])  # JSON round-trips correctly

    def test_json_columns_round_trip(self):
        conn = store.connect(self.db_path)
        store.insert(
            conn,
            "episodic_memories",
            {
                "episodic_id": "epi-test-1",
                "captain_id": "captain.alpha",
                "source_event_id": None,
                "occurred_at": "2026-07-13T00:00:00Z",
                "who_json": ["captain.alpha", "lieutenant.cgl"],
                "what": "Test episode",
                "outcome": "success",
                "evidence_json": [{"event_id": "evt-1"}],
                "certainty": 1.0,
                "interpretation": None,
                "interpretation_history_json": [],
                "salience_score": 0.5,
                "strength": 1.0,
                "tags_json": ["test"],
                "influenced_decisions_json": [],
                "is_imported_history": 0,
                "embedding_json": None,
                "created_at": now(),
                "updated_at": now(),
            },
        )
        row = store.fetch_one(conn, "episodic_memories", "epi-test-1")
        conn.close()
        self.assertEqual(row["who_json"], ["captain.alpha", "lieutenant.cgl"])
        self.assertEqual(row["tags_json"], ["test"])
        self.assertEqual(row["evidence_json"], [{"event_id": "evt-1"}])


if __name__ == "__main__":
    unittest.main()
