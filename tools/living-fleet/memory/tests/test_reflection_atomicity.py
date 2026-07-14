"""Deterministic fault-injection tests for GitHub issue #14: prove that
apply_reflection() is atomic at the "one captain's one triggered reflection"
boundary -- either the whole batch of writes (belief revisions, procedural
lessons, relationship updates, trait shifts, the reflections summary row)
commits, or none of it does. No timing-based process kills: the earlier
manual crash testing (docs/verification/post-sprint-system-verification.md)
could not reliably land a kill inside the multi-row write sequence, since
the write phase is fast relative to interpreter startup. This monkeypatches
store.insert directly, so the injected failure is guaranteed to land exactly
where intended -- after the new belief's insert, before the old belief's
superseding update.

Only scratch/tempdir databases are used here; production
data/living-fleet/memory.db is never touched.
"""

import json
import tempfile
import unittest
from pathlib import Path

from memory import reflection, store
from memory.models import now
from memory.service import MemoryService

CAPTAINS_PATH = Path(__file__).resolve().parents[2] / "captains.json"


class ReflectionAtomicityTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "memory.db"
        self.captains = json.loads(CAPTAINS_PATH.read_text())
        self.service = MemoryService(self.db_path, self.captains)
        self.conn = self.service.conn
        self.old_belief_id = "bel_atomicity_seed"
        store.insert(
            self.conn,
            "semantic_beliefs",
            {
                "belief_id": self.old_belief_id,
                "captain_id": "captain.alpha",
                "subject": "test.subject",
                "statement": "original statement",
                "belief_type": "belief",
                "confidence": 0.6,
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

    def tearDown(self):
        self.service.close()
        self.tmp_dir.cleanup()

    def _content(self):
        return {
            "summary": "test reflection exercising multiple related writes",
            "belief_revisions": [
                {
                    "old_belief_id": self.old_belief_id,
                    "subject": "test.subject",
                    "new_statement": "revised statement",
                    "confidence": 0.8,
                    "evidence": [],
                    "revision_reason": "test",
                }
            ],
            "procedural_lessons": [
                {
                    "situation": "test situation",
                    "guidance": "test guidance",
                    "confidence": 0.7,
                    "evidence": [],
                }
            ],
        }

    def _run_with_fault_after_first_write(self):
        """Monkeypatch store.insert (as seen by the reflection module) to
        raise right after the first write succeeds -- landing between the
        new belief's insert and the old belief's superseding update, the
        exact half-linked-revision window the code comment in
        reflection.py's apply_reflection warns about.
        """
        calls = {"n": 0}
        real_insert = store.insert

        def faulty_insert(conn, table, fields, *, commit=True):
            calls["n"] += 1
            result = real_insert(conn, table, fields, commit=commit)
            if calls["n"] == 1:
                raise RuntimeError("injected crash mid-reflection")
            return result

        reflection.store.insert = faulty_insert
        try:
            with self.assertRaises(RuntimeError):
                reflection.apply_reflection(
                    self.conn,
                    "captain.alpha",
                    reason="fault-injection-test",
                    content=self._content(),
                    provider_name="test",
                    evidence={},
                )
        finally:
            reflection.store.insert = real_insert

    def test_injected_failure_leaves_no_partial_state(self):
        self._run_with_fault_after_first_write()

        self.assertEqual(self.conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")

        # The logical state is fully rolled back, not half-applied: no new
        # belief exists, and the old belief was never marked superseded --
        # proving the insert+update pair didn't split across the crash.
        new_beliefs = store.fetch_by(self.conn, "semantic_beliefs", supersedes_belief_id=self.old_belief_id)
        self.assertEqual(new_beliefs, [])
        old = store.fetch_one(self.conn, "semantic_beliefs", self.old_belief_id)
        self.assertEqual(old["status"], "active")
        self.assertIsNone(old["superseded_by_belief_id"])

        # Nothing else from the same batch landed either -- the whole
        # reflection is the atomicity boundary, not just the belief pair.
        self.assertEqual(store.fetch_by(self.conn, "procedural_lessons", captain_id="captain.alpha"), [])
        self.assertEqual(store.fetch_by(self.conn, "reflections", captain_id="captain.alpha"), [])

    def test_restart_then_clean_reflection_recovers_with_no_duplication(self):
        self._run_with_fault_after_first_write()

        # Simulate a restart: close and reopen against the same file.
        self.service.close()
        self.service = MemoryService(self.db_path, self.captains)
        self.conn = self.service.conn
        self.assertEqual(self.conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")

        # A clean, unfaulted reflection now succeeds completely.
        result = reflection.apply_reflection(
            self.conn,
            "captain.alpha",
            reason="post-restart-retry",
            content=self._content(),
            provider_name="test",
            evidence={},
        )
        self.assertIsNotNone(result)

        new_beliefs = store.fetch_by(self.conn, "semantic_beliefs", supersedes_belief_id=self.old_belief_id)
        self.assertEqual(len(new_beliefs), 1, "exactly one revision, no duplicate from the earlier rolled-back attempt")
        old = store.fetch_one(self.conn, "semantic_beliefs", self.old_belief_id)
        self.assertEqual(old["status"], "superseded")
        self.assertEqual(old["superseded_by_belief_id"], new_beliefs[0]["belief_id"])
        self.assertEqual(len(store.fetch_by(self.conn, "reflections", captain_id="captain.alpha")), 1)


if __name__ == "__main__":
    unittest.main()
