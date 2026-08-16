"""Unit tests for the Recovery Index & Query Engine."""

import unittest
from recovery_index import RecoveryIndex, BIG_BOOK_CHAPTERS, STEPS_MAP, TRADITIONS_MAP


class TestRecoveryIndex(unittest.TestCase):
    def setUp(self) -> None:
        self.index = RecoveryIndex()

    def test_all_twelve_steps_present(self) -> None:
        self.assertEqual(len(STEPS_MAP), 12)
        for i in range(1, 13):
            step = self.index.get_step(i)
            self.assertIsNotNone(step)
            self.assertEqual(step.step_num, i)
            self.assertTrue(len(step.practical_function) > 10)
            self.assertTrue(len(step.failure_mode_prevented) > 10)

    def test_all_twelve_traditions_present(self) -> None:
        self.assertEqual(len(TRADITIONS_MAP), 12)
        for i in range(1, 13):
            trad = self.index.get_tradition(i)
            self.assertIsNotNone(trad)
            self.assertEqual(trad.tradition_num, i)
            self.assertTrue(len(trad.short_form) > 10)
            self.assertTrue(len(trad.failure_mode_prevented) > 10)

    def test_big_book_chapters_coverage(self) -> None:
        self.assertEqual(len(BIG_BOOK_CHAPTERS), 12)  # Doctor's Opinion (0) + Chapters 1-11
        for i in range(12):
            chap = self.index.get_chapter(i)
            self.assertIsNotNone(chap)
            self.assertEqual(chap.chapter_num, i)
            self.assertTrue(len(chap.mechanism) > 10)

    def test_policies_coverage(self) -> None:
        self.assertIsNotNone(self.index.get_policy("p-11"))
        self.assertIsNotNone(self.index.get_policy("p-35"))
        self.assertIsNotNone(self.index.get_policy("hi-btg"))
        self.assertIsNotNone(self.index.get_policy("peer-vs-clinical"))
        self.assertIsNotNone(self.index.get_policy("home-first"))

    def test_search_functionality(self) -> None:
        results = self.index.search("meditation")
        self.assertTrue(any(s["step_num"] == 11 for s in results["steps"]))
        self.assertTrue(any(c["chapter_num"] == 6 for c in results["chapters"]))

        results_anonymity = self.index.search("anonymity")
        self.assertTrue(any(t["tradition_num"] == 11 for t in results_anonymity["traditions"]))
        self.assertTrue(any(t["tradition_num"] == 12 for t in results_anonymity["traditions"]))

        results_med = self.index.search("medication")
        self.assertTrue(any(p["key"] == "p-11" for p in results_med["policies"]))

        results_home = self.index.search("sanctuary")
        self.assertTrue(any(p["key"] == "home-first" for p in results_home["policies"]))


if __name__ == "__main__":
    unittest.main()
