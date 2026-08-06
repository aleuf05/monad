import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

import database
from image_generator import ImageGenerator, extract_image


class FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return self._body


def fake_success_transport(*args, **kwargs):
    body = json.dumps({
        "output": [{"type": "image", "mime_type": "image/jpeg",
                    "data": base64.b64encode(b"\xff\xd8\xff fake jpeg bytes").decode()}],
    }).encode()
    return FakeResponse(body)


def fake_no_image_transport(*args, **kwargs):
    return FakeResponse(json.dumps({"output": []}).encode())


class ImageGeneratorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name)
        self.conn = database.connect(self.data_dir / "captain.sqlite3")

    def tearDown(self):
        self.conn.close()
        self._tmp.cleanup()

    def test_extract_image_finds_nested_data(self):
        encoded = base64.b64encode(b"raw-bytes").decode()
        self.assertEqual(
            extract_image({"nested": [{"mimeType": "image/png", "data": encoded}]}),
            (b"raw-bytes", "image/png"),
        )
        self.assertIsNone(extract_image({"no": "image here"}))

    def test_successful_job_persists_artifact_and_status(self):
        generator = ImageGenerator(
            self.conn, "not-a-real-key", self.data_dir / "images", transport=fake_success_transport
        )
        job = generator.submit("sess-1", "a red ship on a calm sea")
        self.assertEqual(job["status"], "queued")

        generator._queue.join()
        finished = database.get_image_job(self.conn, job["id"])
        self.assertEqual(finished["status"], "succeeded")
        self.assertEqual(finished["artifact_mime"], "image/jpeg")
        path = generator.artifact_path(finished)
        self.assertIsNotNone(path)
        self.assertTrue(path.exists())
        self.assertEqual(path.read_bytes(), b"\xff\xd8\xff fake jpeg bytes")

    def test_failed_job_records_error_not_a_crash(self):
        generator = ImageGenerator(
            self.conn, "not-a-real-key", self.data_dir / "images", transport=fake_no_image_transport
        )
        job = generator.submit("sess-1", "an impossible request")
        generator._queue.join()
        finished = database.get_image_job(self.conn, job["id"])
        self.assertEqual(finished["status"], "failed")
        self.assertIsNone(generator.artifact_path(finished))


if __name__ == "__main__":
    unittest.main()
