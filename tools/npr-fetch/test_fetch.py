import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("npr_fetch", Path(__file__).with_name("fetch.py"))
npr_fetch = importlib.util.module_from_spec(spec); sys.modules[spec.name] = npr_fetch; spec.loader.exec_module(npr_fetch)


class HeadlineWriteTests(unittest.TestCase):
    def test_unchanged_items_do_not_rewrite_snapshot(self):
        items = [{"title": "Same", "link": "https://example.test/same", "pubDate": "today"}]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "headlines.json"
            output.write_text(json.dumps({"fetched_at": "original", "items": items}))
            before = output.stat().st_mtime_ns
            with patch.object(npr_fetch, "HEADLINES_OUTPUT_PATH", output), patch.object(npr_fetch, "fetch_feed", return_value=b"ignored"), patch.object(npr_fetch, "parse_headline_items", return_value=items):
                self.assertEqual(npr_fetch.fetch_headlines(), 0)
            self.assertEqual(output.stat().st_mtime_ns, before)
            self.assertEqual(json.loads(output.read_text())["fetched_at"], "original")

    def test_changed_items_replace_snapshot(self):
        old = [{"title": "Old", "link": "https://example.test/old", "pubDate": "yesterday"}]
        new = [{"title": "New", "link": "https://example.test/new", "pubDate": "today"}]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "headlines.json"
            output.write_text(json.dumps({"fetched_at": "original", "items": old}))
            with patch.object(npr_fetch, "HEADLINES_OUTPUT_PATH", output), patch.object(npr_fetch, "fetch_feed", return_value=b"ignored"), patch.object(npr_fetch, "parse_headline_items", return_value=new):
                self.assertEqual(npr_fetch.fetch_headlines(), 0)
            payload = json.loads(output.read_text())
            self.assertEqual(payload["items"], new)
            self.assertNotEqual(payload["fetched_at"], "original")


if __name__ == "__main__": unittest.main()
