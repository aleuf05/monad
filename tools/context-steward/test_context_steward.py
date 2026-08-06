import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
SPEC = importlib.util.spec_from_file_location("context_steward", HERE / "context_steward.py")
CS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CS)


class ContextStewardTests(unittest.TestCase):
    def fixture(self, root: Path) -> dict:
        (root / "truth.md").write_text("# Truth\n")
        return {
            "schema": CS.SCHEMA,
            "mission": "Chart the space.",
            "active_goal": "Prove continuity.",
            "vocabulary": [{"term": "Passage", "meaning": "Navigable submanifold."}],
            "established_truth": ["The atlas exists."],
            "next_action": "Test the helm.",
            "sources": ["truth.md"],
            "historical_wake": ["Completed old work."],
            "disposable_repetition": ["do it", "do it again"],
        }

    def test_deterministic_outputs_and_exclusions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, out = Path(tmp), Path(tmp) / "out"
            source = root / "input.json"
            source.write_text(json.dumps(self.fixture(root)))
            CS.checkpoint(source, out, None, root)
            first = {path.name: path.read_bytes() for path in out.iterdir()}
            CS.checkpoint(source, out, None, root)
            second = {path.name: path.read_bytes() for path in out.iterdir()}
            self.assertEqual(first, second)
            prose = (out / "continuation.md").read_text()
            self.assertNotIn("Completed old work", prose)
            self.assertNotIn("do it again", prose)
            state = json.loads((out / "current-state.json").read_text())
            self.assertEqual(state["disposable_repetition_excluded"], 2)
            self.assertEqual(state["sources"], ["truth.md"])

    def test_secret_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = self.fixture(root)
            data["active_goal"] = "api_key=definitely-not-allowed-here"
            with self.assertRaisesRegex(ValueError, "secret"):
                CS.validate(data, root)

    def test_missing_section_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = self.fixture(root)
            del data["next_action"]
            with self.assertRaisesRegex(ValueError, "next_action"):
                CS.validate(data, root)

    def test_budget_reports_optional_omission(self):
        data = {
            "mission": "m",
            "active_goal": "g",
            "vocabulary": [{"term": "t", "meaning": "v"}],
            "established_truth": ["truth"],
            "next_action": "next",
            "sources": ["truth.md"],
            "deferred_ideas": ["x" * 20_000],
        }
        brief, continuation, state = CS.fit_budget(data, "2026-01-01T00:00:00+00:00", "digest")
        self.assertIn("deferred_ideas", state["omissions"])
        self.assertLessEqual(len(brief.encode()), CS.MAX_BYTES["current-brief.md"])
        self.assertLessEqual(len(continuation.encode()), CS.MAX_BYTES["continuation.md"])

    def test_archive_is_idempotent_and_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, out = Path(tmp), Path(tmp) / "out"
            source = root / "input.json"
            source.write_text(json.dumps(self.fixture(root)))
            CS.checkpoint(source, out, "milestone", root)
            archive = next((out / "archive").iterdir())
            original = archive.read_text()
            CS.checkpoint(source, out, "milestone", root)
            self.assertEqual(original, archive.read_text())


if __name__ == "__main__":
    unittest.main()
