import importlib.util
import sys
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("voice_evaluation", Path(__file__).with_name("evaluation.py"))
evaluation = importlib.util.module_from_spec(spec); sys.modules[spec.name] = evaluation; spec.loader.exec_module(evaluation)


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.characters = ["captain.monad", "captain.alpha"]
        self.artifacts = {f"{character}:{line}": f"/{character}-{line}.wav" for character in self.characters for line, _ in evaluation.LINES}
        self.manifest = evaluation.build_manifest(self.characters, self.artifacts)

    def test_manifest_is_blinded_and_deterministic(self):
        public = evaluation.public_manifest(self.manifest)
        self.assertEqual(self.manifest, evaluation.build_manifest(self.characters, self.artifacts))
        self.assertNotIn("answer", public["trials"][0])
        self.assertEqual(len(public["trials"]), 12)

    def test_perfect_responses_pass(self):
        responses = [{"trial_id": trial["trial_id"], **trial["answer"], "caricature": False, "transcript_error": False} for trial in self.manifest["trials"]]
        result = evaluation.score(self.manifest, responses)
        self.assertTrue(result["pass"]); self.assertEqual(result["character_accuracy"], 1)

    def test_caricature_and_transcript_error_fail(self):
        responses = [{"trial_id": trial["trial_id"], **trial["answer"], "caricature": True, "transcript_error": True} for trial in self.manifest["trials"]]
        self.assertFalse(evaluation.score(self.manifest, responses)["pass"])


if __name__ == "__main__": unittest.main()
