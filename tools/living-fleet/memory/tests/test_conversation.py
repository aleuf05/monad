import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from memory.service import MemoryService

CAPTAINS_PATH = Path(__file__).resolve().parents[2] / "captains.json"
LOG_CONVERSATION_SCRIPT = Path(__file__).resolve().parents[1] / "log_conversation.py"


class ConversationIngestionTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "memory.db"
        self.captains = json.loads(CAPTAINS_PATH.read_text())

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_record_conversation_is_salience_scored_like_any_other_event(self):
        service = MemoryService(self.db_path, self.captains)
        try:
            result = service.record_conversation(
                "captain.alpha",
                with_id="lieutenant.cgl",
                occurred_at="2026-07-13T00:00:00Z",
                transcript="Lieutenant: hold your current station until further notice.",
            )
        finally:
            service.close()
        self.assertIn("salience_score", result)
        self.assertNotEqual(result["disposition"], "")

    def test_cli_round_trips_a_piped_transcript_into_a_real_row(self):
        completed = subprocess.run(
            [
                sys.executable,
                str(LOG_CONVERSATION_SCRIPT),
                "--captain",
                "captain.bravo",
                "--with",
                "lieutenant.cgl",
                "--db",
                str(self.db_path),
                "--captains",
                str(CAPTAINS_PATH),
                "--occurred-at",
                "2026-07-13T00:00:00Z",
            ],
            input="Lieutenant: widen the flank by another 200 meters.\n",
            text=True,
            capture_output=True,
            timeout=20,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Recorded:", completed.stdout)

        service = MemoryService(self.db_path, self.captains)
        try:
            rows = service.inspect_memory("captain.bravo", table="events")
        finally:
            service.close()
        conversations = [row for row in rows if row["kind"] == "conversation"]
        self.assertEqual(len(conversations), 1)
        self.assertIn("widen the flank", conversations[0]["payload_json"]["transcript"])


if __name__ == "__main__":
    unittest.main()
