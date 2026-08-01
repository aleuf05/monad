"""Trust-boundary tests for generated images shown in the Root Console."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location("root_console_server", ROOT / "server.py")
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


class GeneratedImageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Path(self.temp.name)
        self.patch = mock.patch.object(server, "GENERATED_IMAGE_DIR", self.store)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def image(self, relative="thread/call.png", body=b"\x89PNG\r\n\x1a\nimage"):
        path = self.store / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        return path

    def test_valid_png_maps_to_same_origin_authenticated_route(self):
        path = self.image()
        url = server.browser_generated_image_url(str(path))
        self.assertTrue(url.startswith(server.GENERATED_IMAGE_API_PREFIX))
        resolved, mime, size = server.resolve_generated_image(url.rsplit("/", 1)[-1])
        self.assertEqual(resolved, path)
        self.assertEqual(mime, "image/png")
        self.assertEqual(size, path.stat().st_size)

    def test_structured_event_path_is_mapped_without_rewriting_prose(self):
        path = self.image()
        event = {"params": {"item": {"type": "tool", "path": str(path), "text": f"saved {path}"}}}
        mapped = server.map_generated_images(event)
        self.assertTrue(mapped["params"]["item"]["path"].startswith(server.GENERATED_IMAGE_API_PREFIX))
        self.assertEqual(mapped["params"]["item"]["text"], f"saved {path}")

    def test_traversal_missing_and_unsupported_files_are_rejected(self):
        outside = self.store.parent / "outside.png"
        outside.write_bytes(b"png")
        self.assertIsNone(server.browser_generated_image_url(str(outside)))
        missing_token = server.generated_image_token(self.store / "missing.png")
        with self.assertRaises(FileNotFoundError):
            server.resolve_generated_image(missing_token)
        unsupported = self.image("thread/payload.svg", b"<svg/>")
        token = server.generated_image_token(unsupported)
        with self.assertRaises(server.GeneratedImageError):
            server.resolve_generated_image(token)

    def test_oversized_image_is_rejected(self):
        path = self.image()
        with mock.patch.object(server, "MAX_GENERATED_IMAGE_BYTES", path.stat().st_size - 1):
            token = server.generated_image_token(path)
            with self.assertRaises(server.GeneratedImageError):
                server.resolve_generated_image(token)


if __name__ == "__main__":
    unittest.main()
