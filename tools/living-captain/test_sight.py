import importlib.util
import io
import json
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).parent
spec = importlib.util.spec_from_file_location("sight", ROOT / "sight.py")
sight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sight)


def response(body):
    mocked = MagicMock()
    mocked.__enter__.return_value = io.BytesIO(json.dumps(body).encode())
    return mocked


class SightTest(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_fetch_fleetcore_snapshot(self, urlopen):
        snapshot = {
            "tick": 412,
            "vessels": [{"id": "vessel.monad", "status": "underway"}],
        }
        urlopen.return_value = response(snapshot)

        self.assertEqual(sight.fetch_fleetcore_snapshot(timeout=2.0), snapshot)
        urlopen.assert_called_once_with(
            "http://127.0.0.1:4771/snapshot", timeout=2.0
        )

    @patch("urllib.request.urlopen")
    def test_fetch_world_intake_returns_proposals_list(self, urlopen):
        proposals = [
            {"id": "proposal-1", "status": "pending", "subject": "Ada"},
            {"id": "proposal-2", "status": "pending", "subject": "Cyra"},
        ]
        urlopen.return_value = response({"proposals": proposals, "count": 2})

        result = sight.fetch_world_intake_pending()

        self.assertEqual(result, proposals)
        self.assertIsInstance(result, list)
        urlopen.assert_called_once_with(
            "http://127.0.0.1:4773/proposals?status=pending", timeout=5.0
        )

    @patch("urllib.request.urlopen")
    def test_http_error_propagates(self, urlopen):
        urlopen.side_effect = urllib.error.HTTPError(
            "http://127.0.0.1:4771/snapshot", 503, "Unavailable", {}, None
        )

        with self.assertRaises(urllib.error.HTTPError):
            sight.fetch_fleetcore_snapshot()

    @patch("urllib.request.urlopen")
    def test_malformed_json_propagates(self, urlopen):
        mocked = MagicMock()
        mocked.__enter__.return_value = io.BytesIO(b"{not valid json")
        urlopen.return_value = mocked

        with self.assertRaises(json.JSONDecodeError):
            sight.fetch_world_intake_pending()


if __name__ == "__main__":
    unittest.main()
