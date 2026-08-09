from pathlib import Path
import unittest

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


if __name__ == "__main__":
    unittest.main()
