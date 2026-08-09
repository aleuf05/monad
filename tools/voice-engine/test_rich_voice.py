import importlib.util
import io
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

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


class BlockingProvider:
    def __init__(self): self.started = threading.Event(); self.release = threading.Event()
    def render_pcm(self, **kwargs):
        self.started.set(); self.release.wait(2)
        return b"\x00\x00" * 24_000


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

    def test_legacy_budget_arguments_do_not_gate_voice(self):
        with tempfile.TemporaryDirectory() as directory:
            provider = FakeProvider(); engine = rich_voice.RichVoiceEngine(Path(directory), provider, daily_usd=0.0001)
            engine.render(self.request())
            self.assertEqual(provider.calls, 1)
            self.assertFalse(engine.budget()["enforced"])

    def test_character_revision_changes_cache_key(self):
        request = self.request()
        changed = rich_voice.RenderRequest(request.transcript, rich_voice.CharacterSpec("captain.monad", "2", "Captain Monad", "command presence", "Kore", "Measured authority."), request.performance)
        self.assertNotEqual(rich_voice.cache_key(request), rich_voice.cache_key(changed))

    def test_failed_generation_releases_usage_reservation(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = rich_voice.RichVoiceEngine(Path(directory), FailingProvider())
            with self.assertRaises(RuntimeError): engine.render(self.request())
            self.assertEqual(engine.budget()["usd_used"], 0)

    def test_budget_remains_readable_during_provider_render(self):
        with tempfile.TemporaryDirectory() as directory:
            provider = BlockingProvider()
            engine = rich_voice.RichVoiceEngine(Path(directory), provider)
            worker = threading.Thread(target=lambda: engine.render(self.request()))
            worker.start(); self.assertTrue(provider.started.wait(1))
            started = time.monotonic(); budget = engine.budget()
            self.assertLess(time.monotonic() - started, .25)
            self.assertGreater(budget["seconds_used"], 0)
            provider.release.set(); worker.join(2)
            self.assertFalse(worker.is_alive())

    def test_restart_releases_orphaned_reservation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = rich_voice.RichVoiceEngine(root, FakeProvider())
            with first.db:
                first.db.execute(
                    "INSERT INTO spend(day,cache_key,seconds,usd,state,created_at) VALUES(?,?,?,?,?,?)",
                    ("2099-01-01", "orphan", 20, .01, "reserved", "2099-01-01T00:00:00Z"),
                )
            second = rich_voice.RichVoiceEngine(root, FakeProvider())
            state = second.db.execute("SELECT state FROM spend WHERE cache_key='orphan'").fetchone()[0]
            self.assertEqual(state, "failed")

    def test_gemini_http_error_preserves_provider_detail(self):
        provider = rich_voice.GeminiTTSProvider("test-key")
        failure = urllib.error.HTTPError(
            "https://example.invalid", 400, "Bad Request", {},
            io.BytesIO(b'{"error":{"message":"invalid voice"}}'),
        )
        with mock.patch.object(rich_voice.urllib.request, "urlopen", side_effect=failure):
            with self.assertRaisesRegex(RuntimeError, r'HTTP 400.*invalid voice'):
                provider.render_pcm(prompt="Report.", voice_name="Kore", model="test-model")


if __name__ == "__main__": unittest.main()
