import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

import database
from engine import CaptainEngine
from model_provider import ProviderError, ProviderResponse
from usage_budget import UsageBudget


class FakeProvider:
    name = "Fake"
    model = "fake-1"

    def __init__(self, script):
        self._script = list(script)
        self.calls = []

    def generate(self, system_prompt, messages, limits, sandbox="read-only"):
        self.calls.append((system_prompt, messages, sandbox))
        if not self._script:
            raise ProviderError("fake provider exhausted")
        next_text = self._script.pop(0)
        if isinstance(next_text, Exception):
            raise next_text
        return ProviderResponse(
            text=next_text, provider=self.name, model=self.model,
            input_tokens=10, output_tokens=10, total_tokens=20, finish_reason="completed",
        )


class FakeImageGenerator:
    def __init__(self):
        self.submitted: list[tuple[str, str]] = []

    def submit(self, session_id, prompt):
        self.submitted.append((session_id, prompt))
        return {"id": "img-fake0000000000", "session_id": session_id, "prompt": prompt, "status": "queued"}


class EngineTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name)
        self.conn = database.connect(self.data_dir / "captain.sqlite3")
        self.budget = UsageBudget(self.data_dir / "usage.json")

    def tearDown(self):
        self.conn.close()
        self._tmp.cleanup()

    def _engine(self, script):
        provider = FakeProvider(script)
        return provider, CaptainEngine(
            provider=provider, conn=self.conn, budget=self.budget,
            seed_instruction="SEED", data_dir=self.data_dir,
        )

    def test_reply_persists_both_sides_and_stores_valid_harvest(self):
        reply_text = (
            "Sure thing.\n```captain-json\n"
            '{"reply": "Sure thing.", "mode_suggestion": "design", "project_suggestion": null, '
            '"harvest_proposals": [{"type": "decision", "title": "Use SQLite", '
            '"summary": "Because structure.", "confidence": 0.8, "provenance_note": "chat"}], '
            '"state_notes": [], "safety_signal": null}\n```'
        )
        _, engine = self._engine([reply_text])
        result = engine.reply("What storage should we use?")

        self.assertEqual(result["reply"], "Sure thing.")
        self.assertEqual(result["mode_suggestion"], "design")
        self.assertEqual(len(result["harvest_proposals"]), 1)
        self.assertEqual(result["harvest_proposals"][0]["status"], "candidate")

        state = database.get_state(self.conn)
        messages = database.list_messages(self.conn, state["current_session_id"])
        self.assertEqual([m["role"] for m in messages], ["user", "assistant"])
        self.assertEqual(messages[0]["content"], "What storage should we use?")
        self.assertIsNotNone(state["last_successful_interaction_at"])
        engine.close()

    def test_malformed_provider_output_fails_safely(self):
        _, engine = self._engine(["I forgot to include structured output."])
        result = engine.reply("hello")
        self.assertEqual(result["reply"], "I forgot to include structured output.")
        self.assertIsNone(result["mode_suggestion"])
        self.assertEqual(result["harvest_proposals"], [])
        engine.close()

    def test_invalid_harvest_proposal_is_dropped_not_stored(self):
        reply_text = (
            "OK.\n```captain-json\n"
            '{"reply": "OK.", "mode_suggestion": null, "project_suggestion": null, '
            '"harvest_proposals": [{"type": "not-a-real-type", "title": "X", "summary": "Y"}], '
            '"state_notes": [], "safety_signal": null}\n```'
        )
        _, engine = self._engine([reply_text])
        result = engine.reply("hi")
        self.assertEqual(result["harvest_proposals"], [])
        self.assertEqual(database.list_harvest_items(self.conn), [])
        engine.close()

    def test_bogus_mode_suggestion_is_dropped(self):
        reply_text = (
            "OK.\n```captain-json\n"
            '{"reply": "OK.", "mode_suggestion": "warp_speed", "project_suggestion": null, '
            '"harvest_proposals": [], "state_notes": [], "safety_signal": null}\n```'
        )
        _, engine = self._engine([reply_text])
        result = engine.reply("hi")
        self.assertIsNone(result["mode_suggestion"])
        engine.close()

    def test_close_session_generates_and_persists_brief(self):
        _, engine = self._engine(["Sure.\n```captain-json\n{}\n```", "Brief: shipped the spine."])
        engine.reply("what did we do")
        session = engine.close_session()
        self.assertEqual(session["status"], "closed")
        self.assertEqual(session["brief"], "Brief: shipped the spine.")
        state = database.get_state(self.conn)
        self.assertEqual(state["last_session_brief"], "Brief: shipped the spine.")
        self.assertIsNone(state["current_session_id"])
        engine.close()

    def test_close_session_brief_generation_fails_safely(self):
        _, engine = self._engine(["Sure.\n```captain-json\n{}\n```", ProviderError("down")])
        engine.reply("hi")
        session = engine.close_session()
        self.assertIn("failed", session["brief"])
        engine.close()

    def test_exclusive_owner_lock_prevents_second_engine(self):
        provider, engine = self._engine(["x"])
        with self.assertRaises(Exception):
            CaptainEngine(
                provider=provider, conn=self.conn, budget=self.budget,
                seed_instruction="SEED", data_dir=self.data_dir,
            )
        engine.close()

    def test_new_session_after_close_starts_fresh(self):
        _, engine = self._engine(["a\n```captain-json\n{}\n```", "brief"])
        engine.reply("hi")
        first_session = database.get_state(self.conn)["current_session_id"]
        engine.close_session()
        second_session = engine.start_session()
        self.assertNotEqual(first_session, second_session["id"])
        engine.close()

    def test_master_mode_gets_workspace_write_sandbox(self):
        provider, engine = self._engine(["OK.\n```captain-json\n{}\n```"])
        self.assertEqual(database.get_state(self.conn)["current_mode"], "master")
        engine.reply("do something real")
        self.assertEqual(provider.calls[-1][2], "workspace-write")
        engine.close()

    def test_non_master_mode_stays_read_only(self):
        provider, engine = self._engine(["OK.\n```captain-json\n{}\n```"])
        database.update_state(self.conn, current_mode="design")
        engine.reply("just discuss this")
        self.assertEqual(provider.calls[-1][2], "read-only")
        engine.close()

    def test_image_request_submits_job_and_links_to_assistant_message(self):
        reply_text = (
            "Generating that now.\n```captain-json\n"
            '{"reply": "Generating that now.", "image_request": "a red ship on a calm sea"}\n```'
        )
        provider = FakeProvider([reply_text])
        image_generator = FakeImageGenerator()
        engine = CaptainEngine(
            provider=provider, conn=self.conn, budget=self.budget,
            seed_instruction="SEED", data_dir=self.data_dir, image_generator=image_generator,
        )
        result = engine.reply("draw me a ship")

        self.assertEqual(len(image_generator.submitted), 1)
        session_id, prompt = image_generator.submitted[0]
        self.assertEqual(prompt, "a red ship on a calm sea")
        self.assertIsNotNone(result["image_job"])
        self.assertEqual(result["image_job"]["id"], "img-fake0000000000")

        state = database.get_state(self.conn)
        messages = database.list_messages(self.conn, state["current_session_id"])
        assistant_message = [m for m in messages if m["role"] == "assistant"][0]
        self.assertEqual(assistant_message["image_job_id"], "img-fake0000000000")
        engine.close()

    def test_no_image_request_means_no_job_and_no_generator_call(self):
        _, engine = self._engine(["OK.\n```captain-json\n{}\n```"])
        engine.image_generator = FakeImageGenerator()
        result = engine.reply("hello")
        self.assertIsNone(result["image_job"])
        self.assertEqual(engine.image_generator.submitted, [])
        engine.close()

    def test_missing_image_generator_does_not_crash_on_image_request(self):
        reply_text = (
            "Sure.\n```captain-json\n"
            '{"reply": "Sure.", "image_request": "a lighthouse"}\n```'
        )
        _, engine = self._engine([reply_text])  # no image_generator configured
        result = engine.reply("draw a lighthouse")
        self.assertIsNone(result["image_job"])
        engine.close()


if __name__ == "__main__":
    unittest.main()
