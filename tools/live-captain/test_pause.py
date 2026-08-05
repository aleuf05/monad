#!/usr/bin/env python3
"""Tests for Live Captain pause.

Pause has to be trustworthy in the specific ways an operator assumes:
it holds across restart, it fails open rather than stranding the Captain,
and it never silently swallows a turn.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pause_state  # noqa: E402


class PauseStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._previous = os.environ.get("MONAD_LIVE_CAPTAIN_STATE_DIR")
        os.environ["MONAD_LIVE_CAPTAIN_STATE_DIR"] = self.tmp.name

    def tearDown(self):
        if self._previous is None:
            os.environ.pop("MONAD_LIVE_CAPTAIN_STATE_DIR", None)
        else:
            os.environ["MONAD_LIVE_CAPTAIN_STATE_DIR"] = self._previous
        self.tmp.cleanup()

    def test_default_is_running(self):
        self.assertFalse(pause_state.is_paused())

    def test_pause_then_resume(self):
        pause_state.pause("testing")
        self.assertTrue(pause_state.is_paused())
        self.assertEqual(pause_state.read()["reason"], "testing")
        pause_state.resume()
        self.assertFalse(pause_state.is_paused())

    def test_pause_survives_process_restart(self):
        """The flag is a file precisely so a bounced service cannot silently
        lift a pause. This is the property that makes pause trustworthy."""
        pause_state.pause("held across restart")
        reloaded = json.loads(pause_state.pause_path().read_text())
        self.assertTrue(reloaded["paused"])
        self.assertEqual(reloaded["reason"], "held across restart")

    def test_corrupt_flag_fails_open(self):
        """A damaged flag must not strand the Captain in a pause nobody
        asked for — unreadable means running."""
        pause_state.pause_path().write_text("{ this is not json")
        self.assertFalse(pause_state.is_paused())

    def test_missing_reason_is_explicit_not_blank(self):
        pause_state.pause("")
        self.assertEqual(pause_state.read()["reason"], "(no reason given)")

    def test_refusal_says_paused_not_broken(self):
        pause_state.pause("conference")
        body = pause_state.refusal()
        self.assertTrue(body["paused"])
        self.assertEqual(body["reason"], "conference")
        self.assertIn("resume_with", body)
        self.assertIn("Continuity is intact", body["note"])

    def test_write_is_atomic_leaving_no_temp_files(self):
        pause_state.pause("atomic")
        leftovers = list(pause_state.state_dir().glob("*.tmp"))
        self.assertEqual(leftovers, [])

    def test_checkpoint_is_safe_without_a_database(self):
        result = pause_state.checkpoint_database()
        self.assertFalse(result["checkpointed"])

    def test_checkpoint_truncates_the_wal(self):
        """The connection is held open throughout, because that is the real
        situation: SQLite tidies the WAL on clean close, so a WAL only grows
        while a long-lived process keeps its connection open — which is
        exactly what the Live Captain service does."""
        import sqlite3
        connection = sqlite3.connect(str(pause_state.db_path()))
        try:
            connection.execute("pragma journal_mode=wal")
            connection.execute("create table t (a text)")
            for i in range(500):
                connection.execute("insert into t values (?)", (f"row {i}" * 50,))
            connection.commit()

            wal = pause_state.db_path().with_suffix(".db-wal")
            self.assertGreater(wal.stat().st_size, 0)

            result = pause_state.checkpoint_database()
            self.assertTrue(result["checkpointed"])
            self.assertLess(result["wal_bytes_after"], result["wal_bytes_before"])
        finally:
            connection.close()


class GateWiringTests(unittest.TestCase):
    """The gate must sit after auth and before any recording, in both
    services. Asserted structurally because the HTTP path needs a password
    this test does not hold."""

    def _source(self, name):
        return (Path(__file__).resolve().parents[1] / name).read_text()

    def test_bootstrap_gates_turns(self):
        src = self._source("live-captain/server.py")
        self.assertIn("pause_state.is_paused()", src)
        gate = src.index("pause_state.is_paused()")
        self.assertLess(src.index("def do_POST"), gate)
        self.assertLess(gate, src.index("turn_started"))

    def test_web_service_gates_before_the_model_call(self):
        src = self._source("living-captain/web_service.py")
        gate = src.index("pause_state.is_paused()")
        self.assertLess(gate, src.index("self.server.engine.reply(text)"))

    def test_both_services_report_pause_in_status(self):
        self.assertIn("pause_state.read()", self._source("live-captain/server.py"))
        self.assertIn("pause_state.read()", self._source("living-captain/web_service.py"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
