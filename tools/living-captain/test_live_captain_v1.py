import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import gemini_provider
import live_captain_cli
from conversation import ConversationStore
from live_captain_engine import CaptainEngine
from model_provider import GenerationLimits, Message, ProviderError, ProviderResponse
from usage_budget import (
    BudgetExceeded,
    MAX_INPUT_TOKENS,
    MAX_REQUESTS,
    UsageBudget,
)


class FakeProvider:
    name = "Fake"
    model = "fake-v1"

    def __init__(self):
        self.calls = []

    def generate(self, system_prompt, messages, limits):
        self.calls.append((system_prompt, messages, limits))
        return ProviderResponse(
            text="Copy, Admiral. Prior context received.",
            provider=self.name,
            model=self.model,
            input_tokens=12,
            output_tokens=7,
            total_tokens=19,
            finish_reason="STOP",
        )


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


class LiveCaptainVersion1Tests(unittest.TestCase):
    def test_transcript_and_identity_survive_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            first = ConversationStore(path)
            session_id = first.session_id
            first.append("user", "Remember the lantern.")
            first.append("assistant", "Aye, Admiral.")

            restarted = ConversationStore(path)
            self.assertEqual(restarted.session_id, session_id)
            self.assertEqual(
                restarted.messages(),
                [
                    Message("user", "Remember the lantern."),
                    Message("assistant", "Aye, Admiral."),
                ],
            )
            self.assertEqual((path / "conversation.jsonl").stat().st_mode & 0o777, 0o600)

    def test_budget_reservation_survives_restart_and_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usage.json"
            budget = UsageBudget(path)
            for _ in range(MAX_REQUESTS):
                budget.reserve("small request")
            restarted = UsageBudget(path)
            self.assertEqual(restarted.status()["request_count"], MAX_REQUESTS)
            with self.assertRaisesRegex(BudgetExceeded, "request ceiling"):
                restarted.reserve("one request too many")

    def test_context_keeps_recent_complete_messages(self):
        with tempfile.TemporaryDirectory() as directory:
            budget = UsageBudget(Path(directory) / "usage.json")
            messages = [
                Message("user", "old " * MAX_INPUT_TOKENS),
                Message("assistant", "recent answer"),
                Message("user", "current question"),
            ]
            selected = live_captain_cli.bounded_context("system", messages, budget)
            self.assertEqual(
                selected,
                [
                    Message("assistant", "recent answer"),
                    Message("user", "current question"),
                ],
            )

    def test_oversized_current_message_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            budget = UsageBudget(Path(directory) / "usage.json")
            with self.assertRaisesRegex(BudgetExceeded, "current message"):
                live_captain_cli.bounded_context(
                    "system",
                    [Message("user", "x" * (MAX_INPUT_TOKENS * 4))],
                    budget,
                )

    def test_configured_key_and_key_pattern_are_rejected(self):
        key = "AIza" + "A" * 35
        self.assertTrue(live_captain_cli.contains_secret(key, key))
        self.assertTrue(live_captain_cli.contains_secret(f"do not save {key}", "different"))
        self.assertFalse(live_captain_cli.contains_secret("ordinary conversation", key))

    def test_gemini_uses_header_and_parses_usage(self):
        payload = {
            "modelVersion": "gemini-test",
            "candidates": [
                {
                    "content": {"parts": [{"text": "API_OK"}]},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 4,
                "candidatesTokenCount": 2,
                "totalTokenCount": 6,
            },
        }
        provider = gemini_provider.GeminiProvider("secret-key", model="gemini-test")
        with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(payload)) as call:
            response = provider.generate(
                "system",
                [Message("user", "hello")],
                GenerationLimits(max_output_tokens=8),
            )
        request = call.call_args.args[0]
        request_body = json.loads(request.data)
        self.assertEqual(request.headers["X-goog-api-key"], "secret-key")
        self.assertNotIn("secret-key", request.full_url)
        self.assertEqual(
            request_body["generationConfig"]["thinkingConfig"]["thinkingLevel"],
            "minimal",
        )
        self.assertNotIn("temperature", request_body["generationConfig"])
        self.assertEqual(response.text, "API_OK")
        self.assertEqual(response.total_tokens, 6)

    def test_provider_error_redacts_key(self):
        key = "secret-key"
        error = urllib.error.HTTPError(
            "https://example.invalid",
            400,
            "bad request",
            {},
            io.BytesIO(json.dumps({"error": {"message": f"bad {key}"}}).encode()),
        )
        provider = gemini_provider.GeminiProvider(key)
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(ProviderError) as raised:
                provider.generate(
                    "system",
                    [Message("user", "hello")],
                    GenerationLimits(max_output_tokens=8),
                )
        self.assertNotIn(key, str(raised.exception))
        self.assertIn("[REDACTED]", str(raised.exception))

    def test_terminal_chat_records_reply_and_shuts_down(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            store = ConversationStore(path)
            budget = UsageBudget(path / "usage.json")
            provider = FakeProvider()
            engine = CaptainEngine(
                provider=provider,
                store=store,
                budget=budget,
                system_prompt="Captain system prompt",
                acquire_owner_lock=False,
            )
            output = io.StringIO()
            with (
                patch("builtins.input", side_effect=["What is our prior context?", "/quit"]),
                patch.object(live_captain_cli, "safe_log"),
                patch("sys.stdout", output),
            ):
                result = live_captain_cli.run_chat(
                    engine,
                )
            self.assertEqual(result, 0)
            self.assertIn("Provider: Fake / fake-v1", output.getvalue())
            self.assertIn("Captain> Copy, Admiral.", output.getvalue())
            self.assertEqual([message.role for message in store.messages()], ["user", "assistant"])
            self.assertEqual(budget.status()["request_count"], 1)

    def test_runtime_modules_have_no_shell_imports(self):
        for filename in (
            "live_captain_cli.py",
            "conversation.py",
            "model_provider.py",
            "gemini_provider.py",
            "usage_budget.py",
        ):
            source = (ROOT / filename).read_text(encoding="utf-8")
            self.assertNotIn("import subprocess", source)
            self.assertNotIn("import shlex", source)
            self.assertNotIn("os.system", source)

    def test_cli_has_fixed_local_paths_and_no_listener(self):
        self.assertEqual(live_captain_cli.DATA_DIR, ROOT.parents[1] / "data" / "living-captain")
        source = (ROOT / "live_captain_cli.py").read_text(encoding="utf-8")
        self.assertNotIn("HTTPServer", source)
        self.assertNotIn("socket", source)


if __name__ == "__main__":
    unittest.main()
