import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import watch


class WatchTests(unittest.TestCase):
    def test_chunks_keep_heading_and_bound_size(self):
        text = "# First\nalpha\n\n# Second\nbeta"
        self.assertEqual(list(watch.heading_chunks(text)), [("First", 0, "alpha"), ("Second", 1, "beta")])

    def test_corpus_is_deliberately_bounded(self):
        corpus = __import__("json").loads(watch.CORPUS.read_text())
        self.assertGreaterEqual(len(corpus), 20)
        self.assertLessEqual(len(corpus), 50)
        self.assertNotIn("CURRENT_WATCH.md", " ".join(item["path"] for item in corpus))


if __name__ == "__main__": unittest.main()
