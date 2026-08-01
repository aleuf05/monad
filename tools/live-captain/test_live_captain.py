"""Focused tests for the Live Captain minimum-context bootstrap contract
(packet LIVE-CAPTAIN-MINIMUM-CONTEXT-BOOTSTRAP-0.1 section 14). Tests the
new minimal contract only -- not a recreation of the parked legacy
experiment's test surface.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from context_compiler import (
    ContextCompilerError,
    compile_live_captain_context,
    format_chronological_messages,
    load_required_text,
)
from persistence import LiveCaptainStore, PersistenceError


class ContextCompilerTests(unittest.TestCase):
    def test_kernel_and_bearing_always_included(self):
        text = compile_live_captain_context(
            "KERNEL-MARKER", "BEARING-MARKER", [], "hello captain"
        )
        self.assertIn("KERNEL-MARKER", text)
        self.assertIn("BEARING-MARKER", text)

    def test_missing_kernel_raises(self):
        with self.assertRaises(ContextCompilerError):
            compile_live_captain_context("", "BEARING-MARKER", [], "hello")

    def test_missing_bearing_raises(self):
        with self.assertRaises(ContextCompilerError):
            compile_live_captain_context("KERNEL", "", [], "hello")

    def test_missing_current_message_raises(self):
        with self.assertRaises(ContextCompilerError):
            compile_live_captain_context("KERNEL", "BEARING", [], "   ")

    def test_recent_messages_chronological_and_not_mode_filtered(self):
        # Messages from different "task types" (conceptual, design, code
        # review) all remain visible together, in order -- there is no
        # mode field anywhere in the schema to filter by.
        messages = [
            {"role": "admiral", "text": "let's talk concepts", "seq": 1, "ts": 1},
            {"role": "captain", "text": "sure, concept reply", "seq": 2, "ts": 2},
            {"role": "admiral", "text": "now review this diff", "seq": 3, "ts": 3},
            {"role": "captain", "text": "diff looks fine", "seq": 4, "ts": 4},
        ]
        formatted = format_chronological_messages(messages)
        positions = [formatted.index(m["text"]) for m in messages]
        self.assertEqual(positions, sorted(positions))

    def test_current_admiral_message_appears_once_and_last(self):
        text = compile_live_captain_context(
            "KERNEL", "BEARING", [{"role": "admiral", "text": "earlier", "seq": 1, "ts": 1}],
            "THE CURRENT MESSAGE",
        )
        self.assertEqual(text.count("THE CURRENT MESSAGE"), 1)
        self.assertGreater(text.rindex("THE CURRENT MESSAGE"), text.index("earlier"))

    def test_omission_is_reported_not_hidden(self):
        formatted = format_chronological_messages(
            [{"role": "admiral", "text": "recent one", "seq": 31, "ts": 1}], omitted=12
        )
        self.assertIn("12 earlier message", formatted)

    def test_load_required_text_missing_file_raises(self):
        with self.assertRaises(ContextCompilerError):
            load_required_text(Path("/nonexistent/does-not-exist.md"), "test file")

    def test_load_required_text_empty_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty.md"
            empty.write_text("   \n")
            with self.assertRaises(ContextCompilerError):
                load_required_text(empty, "test file")


class PersistenceTests(unittest.TestCase):
    def test_chronological_ordering_across_all_messages(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LiveCaptainStore(Path(tmp) / "test.db")
            store.record_message("admiral", "first", "kd", "bd")
            store.record_message("captain", "second", "kd", "bd")
            store.record_message("admiral", "third", "kd", "bd")
            messages, omitted = store.load_recent_messages(limit=30)
            self.assertEqual([m["text"] for m in messages], ["first", "second", "third"])
            self.assertEqual(omitted, 0)
            store.close()

    def test_window_reports_omitted_older_messages(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LiveCaptainStore(Path(tmp) / "test.db")
            for i in range(35):
                store.record_message("admiral", f"message-{i}", "kd", "bd")
            messages, omitted = store.load_recent_messages(limit=30)
            self.assertEqual(len(messages), 30)
            self.assertEqual(omitted, 5)
            self.assertEqual(messages[0]["text"], "message-5")
            self.assertEqual(messages[-1]["text"], "message-34")
            store.close()

    def test_invalid_role_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LiveCaptainStore(Path(tmp) / "test.db")
            with self.assertRaises(PersistenceError):
                store.record_message("mode-harvest", "text", "kd", "bd")
            store.close()

    def test_empty_message_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LiveCaptainStore(Path(tmp) / "test.db")
            with self.assertRaises(PersistenceError):
                store.record_message("admiral", "   ", "kd", "bd")
            store.close()

    def test_restart_marker_recorded_and_conversation_survives(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            store = LiveCaptainStore(db_path)
            store.record_message("admiral", "before restart", "kd", "bd")
            store.close()

            # Simulate a service restart: new process, same db file.
            restarted = LiveCaptainStore(db_path)
            messages, _ = restarted.load_recent_messages(limit=30)
            self.assertEqual(messages[0]["text"], "before restart")
            self.assertEqual(restarted.restart_count(), 2)
            restarted.close()

    def test_malformed_persistence_path_fails_truthfully(self):
        # A db path under a file (not a directory) cannot be created;
        # this must raise, not silently fall back to in-memory state.
        with tempfile.TemporaryDirectory() as tmp:
            blocking_file = Path(tmp) / "not-a-directory"
            blocking_file.write_text("x")
            with self.assertRaises((PersistenceError, OSError, NotADirectoryError)):
                LiveCaptainStore(blocking_file / "live-captain.db")


if __name__ == "__main__":
    unittest.main()
