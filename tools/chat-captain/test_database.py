import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

import database


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.conn = database.connect(Path(self._tmp.name) / "captain.sqlite3")

    def tearDown(self):
        self.conn.close()
        self._tmp.cleanup()

    def test_initialization_seeds_state_row(self):
        state = database.get_state(self.conn)
        self.assertIsNotNone(state)
        self.assertEqual(state["current_mode"], database.DEFAULT_MODE)
        self.assertEqual(state["safety_state"], "green")

    def test_initialization_is_idempotent(self):
        state_before = database.get_state(self.conn)
        database._ensure_state_row(self.conn)
        state_after = database.get_state(self.conn)
        self.assertEqual(state_before["created_at"], state_after["created_at"])

    def test_project_lifecycle(self):
        project = database.create_project(self.conn, title="Beastscape", purpose="Chart it")
        self.assertEqual(project["title"], "Beastscape")
        self.assertEqual(project["active"], 1)
        updated = database.update_project(self.conn, project["id"], next_action="Ship it")
        self.assertEqual(updated["next_action"], "Ship it")
        self.assertIn(project["id"], [row["id"] for row in database.list_projects(self.conn)])

    def test_session_lifecycle(self):
        session = database.create_session(self.conn, mode="design", project_id=None)
        self.assertEqual(session["status"], "open")
        closed = database.close_session(self.conn, session["id"], mode_at_end="review", brief="Did the thing.")
        self.assertEqual(closed["status"], "closed")
        self.assertEqual(closed["brief"], "Did the thing.")
        self.assertIsNotNone(closed["ended_at"])

    def test_message_persistence_and_ordering(self):
        session = database.create_session(self.conn, mode="master", project_id=None)
        database.append_message(self.conn, session_id=session["id"], role="user", content="first")
        database.append_message(self.conn, session_id=session["id"], role="assistant", content="second")
        messages = database.list_messages(self.conn, session["id"])
        self.assertEqual([message["content"] for message in messages], ["first", "second"])

    def test_harvest_accept_persists(self):
        item = database.create_harvest_item(
            self.conn,
            type="principle",
            title="Test principle",
            summary="A summary.",
            project_id=None,
            session_id=None,
            provenance_note="unit test",
            confidence=0.9,
        )
        self.assertEqual(item["status"], "candidate")
        accepted = database.set_harvest_status(self.conn, item["id"], "accepted")
        self.assertEqual(accepted["status"], "accepted")
        self.assertIsNotNone(accepted["reviewed_at"])
        self.assertIn(item["id"], [row["id"] for row in database.list_harvest_items(self.conn, status="accepted")])

    def test_harvest_status_rejects_unknown_value(self):
        item = database.create_harvest_item(
            self.conn,
            type="decision",
            title="X",
            summary="Y",
            project_id=None,
            session_id=None,
            provenance_note=None,
            confidence=None,
        )
        with self.assertRaises(ValueError):
            database.set_harvest_status(self.conn, item["id"], "canonical")

    def test_mode_transition_logging(self):
        event = database.log_mode_event(
            self.conn, previous_mode="master", new_mode="design", reason="starting design work", source="operator"
        )
        self.assertEqual(event["new_mode"], "design")
        with self.assertRaises(ValueError):
            database.log_mode_event(self.conn, previous_mode="design", new_mode="bogus", reason=None, source="operator")

    def test_project_selection_persists(self):
        project = database.create_project(self.conn, title="P")
        database.update_state(self.conn, active_project_id=project["id"])
        state = database.get_state(self.conn)
        self.assertEqual(state["active_project_id"], project["id"])


if __name__ == "__main__":
    unittest.main()
