from pathlib import Path
import io
import json
import tempfile
import unittest
from unittest.mock import patch

import server


class ContextImageGatewayTests(unittest.TestCase):
    def test_types_and_limit_are_bounded(self):
        self.assertEqual(server.CONTEXT_IMAGE_TYPES["image/png"], ".png")
        self.assertNotIn("image/svg+xml", server.CONTEXT_IMAGE_TYPES)
        self.assertEqual(server.CONTEXT_IMAGE_MAX_BYTES, 12 * 1024 * 1024)

    def test_ui_uses_authenticated_context_image_route_without_publish_controls(self):
        page = (Path(__file__).parents[2] / "console/index.html").read_text()
        script = (Path(__file__).parents[2] / "console/assets/js/root-console.js").read_text()
        self.assertIn('id="context-image-drop"', page)
        self.assertIn("${API_BASE}/context-image", script)
        self.assertIn("private incoming pool", page)
        self.assertNotIn("context-image-commit", page)

    def test_captains_eye_uses_its_private_stable_inbox(self):
        source = (Path(__file__).with_name("server.py")).read_text()
        page = (Path(__file__).parents[2] / "console" / "captains-eye.html").read_text()
        self.assertIn('self.path == "/api/captains-eye"', source)
        self.assertIn('data" / "root-console" / "captains-eye"', source)
        self.assertIn('root / "latest.json"', source)
        self.assertIn('/root-console-api/api/captains-eye', page)

    def test_captains_eye_writes_latest_pointer_and_history(self):
        boundary = "captains-eye-test"
        image = b"not-a-real-png-but-the-transport-is-the-unit-under-test"
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="file"; filename="winstation.png"\r\n'
            "Content-Type: image/png\r\n\r\n"
        ).encode() + image + f"\r\n--{boundary}--\r\n".encode()
        handler = type("Upload", (), {
            "headers": {
                "Content-Length": str(len(body)),
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            "rfile": io.BytesIO(body),
        })()
        with tempfile.TemporaryDirectory() as directory, patch.object(server, "REPO_ROOT", Path(directory)):
            result = server.save_captains_eye_image(handler)
            latest = Path(directory, result["latest"])
            history = Path(directory, result["history"])
            self.assertEqual(image, latest.read_bytes())
            self.assertEqual(image, history.read_bytes())
            metadata = json.loads(Path(directory, "data/root-console/captains-eye/latest.json").read_text())
            self.assertEqual(result["latest"], metadata["latest"])


if __name__ == "__main__":
    unittest.main()
