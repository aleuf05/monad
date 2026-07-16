import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).with_name("rich_voice.py")
spec = importlib.util.spec_from_file_location("rich_voice", MODULE)
rich_voice = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = rich_voice
spec.loader.exec_module(rich_voice)


class FakeProvider:
    def __init__(self): self.calls = 0; self.prompts = []
    def render_pcm(self, *, prompt, voice_name, model):
        self.calls += 1; self.prompts.append((prompt, voice_name, model))
        return b"\x00\x00" * 24_000  # one second


class FailingProvider:
    def render_pcm(self, **kwargs): raise RuntimeError("synthetic provider failure")


class RichVoiceTests(unittest.TestCase):
    def request(self, transcript="Hold the formation."):
        return rich_voice.RenderRequest(
            transcript=transcript,
            character=rich_voice.CharacterSpec("captain.monad", "1", "Captain Monad", "command presence", "Kore", "Measured authority with restrained warmth."),
            performance=rich_voice.PerformancePlan("reassure", "the Lieutenant", "a private operational report", "warm authority under controlled concern", "measured", "tension remains audible but contained"),
        )

    def test_same_take_generates_once_then_hits_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            provider = FakeProvider(); engine = rich_voice.RichVoiceEngine(Path(directory), provider)
            first = engine.render(self.request()); second = engine.render(self.request())
            self.assertFalse(first["cache_hit"]); self.assertTrue(second["cache_hit"])
            self.assertEqual(provider.calls, 1)
            self.assertIn("Recite the transcript exactly", provider.prompts[0][0])
            self.assertEqual(engine.budget()["seconds_used"], 1)

    def test_budget_fails_before_provider_call(self):
        with tempfile.TemporaryDirectory() as directory:
            provider = FakeProvider(); engine = rich_voice.RichVoiceEngine(Path(directory), provider, daily_usd=0.0001)
            with self.assertRaises(rich_voice.BudgetExceeded): engine.render(self.request())
            self.assertEqual(provider.calls, 0)

    def test_character_revision_changes_cache_key(self):
        request = self.request()
        changed = rich_voice.RenderRequest(request.transcript, rich_voice.CharacterSpec("captain.monad", "2", "Captain Monad", "command presence", "Kore", "Measured authority."), request.performance)
        self.assertNotEqual(rich_voice.cache_key(request), rich_voice.cache_key(changed))

    def test_failed_generation_releases_reserved_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = rich_voice.RichVoiceEngine(Path(directory), FailingProvider())
            with self.assertRaises(RuntimeError): engine.render(self.request())
            self.assertEqual(engine.budget()["usd_used"], 0)


if __name__ == "__main__": unittest.main()
