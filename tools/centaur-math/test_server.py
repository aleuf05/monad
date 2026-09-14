import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server


class CentaurMathServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name)
        self.db = self.data / "centaur.sqlite3"
        self.patches = [
            patch.object(server, "DATA_DIR", self.data),
            patch.object(server, "DB_PATH", self.db),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def test_candidate_validation_and_persistence(self):
        payload = server.validate({
            "attribution": "Cameron", "kind": "candidate", "note": "Introductory run",
            "start_value": 1, "step": 6, "length": 4, "endpoint": 19,
        })
        with server.connect() as connection:
            connection.execute(
                "INSERT INTO contributions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("one", payload["attribution"], payload["kind"], payload["note"], payload["start_value"], payload["step"], payload["length"], payload["endpoint"], "now"),
            )
            connection.commit()
            self.assertEqual(server.list_contributions(connection)[0]["endpoint"], 19)

    def test_invalid_candidate_rejected(self):
        with self.assertRaisesRegex(ValueError, "endpoint"):
            server.validate({
                "attribution": "Mike", "kind": "candidate", "note": "bad",
                "start_value": 1, "step": 6, "length": 4, "endpoint": 20,
            })

    def test_observation_does_not_require_candidate_fields(self):
        record = server.validate({"attribution": "Captain", "kind": "observation", "note": "Try factoring the endpoint."})
        self.assertIsNone(record["endpoint"])


if __name__ == "__main__":
    unittest.main()
