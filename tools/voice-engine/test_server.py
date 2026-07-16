import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("voice_server", ROOT / "server.py")
server = importlib.util.module_from_spec(spec); sys.modules[spec.name] = server; spec.loader.exec_module(server)


class ServerRequestTests(unittest.TestCase):
    def test_known_character_builds_bounded_request(self):
        request = server.build_request({"character_id": "captain.alpha", "transcript": " Contact ahead. ", "performance": {"affect": "alert"}})
        self.assertEqual(request.character.voice_name, "Puck")
        self.assertEqual(request.transcript, "Contact ahead.")

    def test_unknown_character_and_long_transcript_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown"): server.build_request({"character_id": "somebody.real", "transcript": "hello"})
        with self.assertRaisesRegex(ValueError, "1200"): server.build_request({"character_id": "captain.monad", "transcript": "x" * 1201})


if __name__ == "__main__": unittest.main()
