import base64
import json
import tempfile
import unittest
from pathlib import Path

import service


RECIPE = {
    "schema": "monad.beastDefinition.v0.1", "family": "radial-hydra",
    "symmetry": 7, "branch_depth": 2, "reach": .66, "curl": .28,
    "irregularity": .16, "terminal": "eye", "seed": 1407,
    "id": "hydra-1407-7r2d",
}

BEASTSCAPE = {
    "schema": "monad.beastscapeSpecimen.v0.1", "v": [.1, .2, .3],
    "f": {}, "r": {}, "type": 0, "region": "radial",
    "nodes": [{"id": 0, "x": 0, "y": 0, "role": "core", "radius": 10}],
    "edges": [], "id": "beast-100-200-300",
}


class FakeResponse:
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self):
        return json.dumps({"output": [{"type": "image", "mime_type": "image/png",
                                      "data": base64.b64encode(b"\x89PNG\r\n\x1a\nresult").decode()}],
                           "usage": {"total_tokens": 12}}).encode()


class WorkbenchTests(unittest.TestCase):
    def test_recipe_contract(self):
        self.assertEqual(service.validate_recipe(RECIPE), RECIPE)
        bad = {**RECIPE, "symmetry": 13}
        with self.assertRaisesRegex(ValueError, "out of bounds"):
            service.validate_recipe(bad)
        self.assertEqual(service.validate_recipe(BEASTSCAPE), BEASTSCAPE)
        self.assertIn("graph is authoritative", service.captain_prompt(BEASTSCAPE))

    def test_image_extraction(self):
        encoded = base64.b64encode(b"image").decode()
        self.assertEqual(service.extract_image({"nested": [{"mimeType": "image/png", "data": encoded}]}),
                         (b"image", "image/png"))

    def test_job_executes_and_preserves_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = service.LIVE_ENABLED
            service.LIVE_ENABLED = True
            workbench = service.Workbench(Path(directory), "not-a-real-key",
                                          transport=lambda *args, **kwargs: FakeResponse())
            try:
                job = workbench.submit(RECIPE, b"\x89PNG\r\n\x1a\nsource")
                workbench.queue.join()
                finished = workbench.get(job["id"])
                self.assertEqual(finished["status"], "succeeded")
                self.assertEqual(finished["request_count"], 1)
                self.assertTrue(workbench.artifact(job["id"])[0].exists())
                self.assertEqual(
                    [event["stage"] for event in finished["observations"]],
                    ["admitted", "worker_claimed", "provider_request", "provider_response", "artifact_ready"],
                )
                self.assertTrue(all(event["source"] for event in finished["observations"]))
            finally:
                service.LIVE_ENABLED = previous

    def test_paid_generation_is_disarmed_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = service.LIVE_ENABLED
            service.LIVE_ENABLED = False
            try:
                workbench = service.Workbench(Path(directory), "not-a-real-key")
                with self.assertRaisesRegex(PermissionError, "disarmed"):
                    workbench.submit(RECIPE, b"\x89PNG\r\n\x1a\nsource")
            finally:
                service.LIVE_ENABLED = previous

    def test_engine_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            workbench = service.Workbench(Path(directory), "not-a-real-key")
            with self.assertRaisesRegex(ValueError, "unsupported Captain engine"):
                workbench.submit(RECIPE, b"\x89PNG\r\n\x1a\nsource", "unknown")

    def test_cancel_is_terminal_and_observed(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = service.LIVE_ENABLED
            service.LIVE_ENABLED = True
            try:
                workbench = service.Workbench(Path(directory), "not-a-real-key")
                job = workbench.submit(RECIPE, b"\x89PNG\r\n\x1a\nsource")
                cancelled = workbench.cancel(job["id"])
                self.assertEqual(cancelled["status"], "cancelled")
                self.assertEqual(cancelled["observations"][-1]["source"], "operator")
                self.assertFalse(cancelled["artifact_available"])
            finally:
                service.LIVE_ENABLED = previous


if __name__ == "__main__":
    unittest.main()
