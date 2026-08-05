#!/usr/bin/env python3
"""Tests for the M³ cycle engine.

Each test builds a throwaway git repo with a small docs/ corpus, so the
predicates are exercised against real git behaviour rather than mocks --
the engine's whole premise is that H_t *is* git, and a mocked git would
test the wrong thing.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import engine  # noqa: E402


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


class CycleTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "Test")
        (self.repo / "docs").mkdir()
        self.write("docs/one.md", "# One\n\nEpistemic label: direct\n\nSee [[Two]].\n")
        self.write("docs/two.md", "# Two\n\n## What would change the answer\n\nEvidence.\n")
        self.commit("initial")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, rel: str, text: str) -> None:
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(self, message: str) -> None:
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", message)

    # --- no-op ------------------------------------------------------------

    def test_clean_tree_is_a_no_op(self):
        result = engine.evaluate(self.repo)
        self.assertFalse(result["proposed"])
        self.assertEqual(result["verdict"], "no-op")

    # --- Cont -------------------------------------------------------------

    def test_retitling_a_document_breaks_identity(self):
        self.write("docs/one.md", "# Renamed\n\nEpistemic label: direct\n\nSee [[Two]].\n")
        result = engine.evaluate(self.repo)
        self.assertFalse(result["continuity"]["I"])
        self.assertEqual(result["verdict"], "rollback")

    def test_deleting_a_document_breaks_identity(self):
        (self.repo / "docs/one.md").unlink()
        result = engine.evaluate(self.repo)
        self.assertFalse(result["continuity"]["I"])

    def test_rewriting_a_refusal_breaks_governance(self):
        self.write("docs/packets/X-REFUSED.md", "# Packet X [REFUSED]\n\nOriginal reasoning.\n")
        self.commit("add refusal")
        self.write("docs/packets/X-REFUSED.md", "# Packet X [REFUSED]\n\nActually it was fine.\n")
        result = engine.evaluate(self.repo)
        self.assertFalse(result["continuity"]["G"])
        self.assertEqual(result["verdict"], "rollback")

    def test_appending_to_a_refusal_is_permitted(self):
        original = "# Packet X [REFUSED]\n\nOriginal reasoning.\n"
        self.write("docs/packets/X-REFUSED.md", original)
        self.commit("add refusal")
        self.write("docs/packets/X-REFUSED.md", original + "\n## Review\n\nStanding, 2026-08-05.\n")
        result = engine.evaluate(self.repo)
        self.assertTrue(result["continuity"]["G"], result["continuity"]["reasons"])

    # --- V ----------------------------------------------------------------

    def test_dangling_link_lowers_valuation(self):
        before = engine.valuation(engine.corpus_at_head(self.repo))
        self.write("docs/three.md", "# Three\n\nSee [[Nowhere At All]].\n")
        after = engine.valuation(engine.corpus_at_worktree(self.repo))
        self.assertLess(after["components"]["dangling_links"],
                        before["components"]["dangling_links"])

    def test_resolvable_link_raises_valuation(self):
        before = engine.valuation(engine.corpus_at_head(self.repo))
        self.write("docs/three.md", "# Three\n\nSee [[Two]] and [[One]].\n")
        after = engine.valuation(engine.corpus_at_worktree(self.repo))
        self.assertGreater(after["total"], before["total"])

    def test_removing_a_hazard_is_not_punished_for_shrinking(self):
        """MSR-EXP-001 §4.1: strict expansion would forbid ever removing
        something bad. Deleting a document full of dangling links must be
        able to raise the valuation."""
        self.write("docs/bad.md", "# Bad\n\n[[Ghost]] [[Phantom]] [[Missing]]\n")
        self.commit("add a document that only dangles")
        before = engine.valuation(engine.corpus_at_head(self.repo))
        (self.repo / "docs/bad.md").unlink()
        after = engine.valuation(engine.corpus_at_worktree(self.repo))
        self.assertGreater(after["total"], before["total"])

    # --- Q_rev ------------------------------------------------------------

    def test_protected_capacity_regression_blocks_even_with_gains(self):
        before = {"gen": 1, "model": 1, "test": 1, "verify": 2, "govern": 1, "recover": 1}
        after = {"gen": 9, "model": 1, "test": 1, "verify": 1, "govern": 1, "recover": 1}
        result = engine.constrained_improvement(before, after)
        self.assertIn("gen", result["improved"])
        self.assertIn("verify", result["protected_regressed"])
        self.assertFalse(result["holds"], "a scalar would have called this progress")

    def test_improvement_with_no_regression_holds(self):
        before = {"gen": 1, "model": 1, "test": 1, "verify": 1, "govern": 1, "recover": 1}
        after = {"gen": 2, "model": 1, "test": 1, "verify": 1, "govern": 1, "recover": 1}
        self.assertTrue(engine.constrained_improvement(before, after)["holds"])

    def test_no_movement_at_all_does_not_hold(self):
        same = {"gen": 1, "model": 1, "test": 1, "verify": 1, "govern": 1, "recover": 1}
        self.assertFalse(engine.constrained_improvement(same, dict(same))["holds"])

    # --- commit / rollback ------------------------------------------------

    def test_rollback_restores_tracked_documents(self):
        self.write("docs/one.md", "# One\n\nvandalised\n")
        engine.rollback(self.repo)
        self.assertIn("Epistemic label", (self.repo / "docs/one.md").read_text())

    def test_commit_advances_head(self):
        head_before = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo,
                                     capture_output=True, text=True).stdout.strip()
        self.write("docs/three.md", "# Three\n\nSee [[Two]].\n")
        engine.commit(self.repo, "add three")
        head_after = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo,
                                    capture_output=True, text=True).stdout.strip()
        self.assertNotEqual(head_before, head_after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
