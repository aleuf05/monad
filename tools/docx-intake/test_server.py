import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).parent
SPEC = importlib.util.spec_from_file_location("docx_intake_server", ROOT / "server.py")
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


class StagedFileTests(unittest.TestCase):
    def test_readme_is_not_a_staged_packet(self):
        with tempfile.TemporaryDirectory() as directory:
            incoming = Path(directory)
            (incoming / "README.md").write_text("tray instructions")
            (incoming / "packet.md").write_text("packet")
            (incoming / "ignore.txt").write_text("not markdown")
            with mock.patch.object(server, "INCOMING_DIR", incoming):
                self.assertEqual([path.name for path in server._staged_files()], ["packet.md"])


if __name__ == "__main__":
    unittest.main()
