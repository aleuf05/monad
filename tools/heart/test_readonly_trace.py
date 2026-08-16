import tempfile
import unittest
from pathlib import Path

from readonly_trace import extract


class ReadOnlyTraceTests(unittest.TestCase):
    def test_absence_of_retest_is_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "watch.md"
            path.write_text(
                "**SIGNAL:** lesson\n\n**EVIDENCE:** proof\n\n"
                "**CHANGE:** do this\n\n**CONFIDENCE:** provisional\n\n"
                "**SOURCE:** record\n",
                encoding="utf-8",
            )
            result = extract(path)
        self.assertTrue(result["captured"])
        self.assertTrue(result["retrievable"])
        self.assertTrue(result["applied"])
        self.assertEqual(result["retest_opportunity"], "NOT_YET_RETESTED")
        self.assertEqual(result["correction_outcome"], "UNKNOWN")
        self.assertFalse(result["promotion_eligible"])


if __name__ == "__main__":
    unittest.main()
