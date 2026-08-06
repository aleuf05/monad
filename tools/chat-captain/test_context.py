import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

import context_compiler
import database


class ContextCompilerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.conn = database.connect(Path(self._tmp.name) / "captain.sqlite3")

    def tearDown(self):
        self.conn.close()
        self._tmp.cleanup()

    def test_system_prompt_includes_required_state(self):
        project = database.create_project(self.conn, title="Beastscape", purpose="Chart it")
        project = database.update_project(self.conn, project["id"], current_summary="Foundry compares candidates.", next_action="Ship it")
        accepted = database.create_harvest_item(
            self.conn, type="decision", title="Use SQLite", summary="Because structure.",
            project_id=project["id"], session_id=None, provenance_note="design chat", confidence=0.9,
        )
        database.set_harvest_status(self.conn, accepted["id"], "accepted")

        state = database.get_state(self.conn)
        prompt = context_compiler.compile_system_prompt(
            self.conn,
            seed_instruction="SEED INSTRUCTION TEXT",
            state=state,
            project=project,
            last_brief="Previous session shipped the spine.",
        )

        self.assertIn("SEED INSTRUCTION TEXT", prompt)
        self.assertIn("Beastscape", prompt)
        self.assertIn("Chart it", prompt)
        self.assertIn("Ship it", prompt)
        self.assertIn("Previous session shipped the spine.", prompt)
        self.assertIn("Use SQLite", prompt)
        self.assertIn("captain-json", prompt)

    def test_system_prompt_handles_no_project_or_brief(self):
        state = database.get_state(self.conn)
        prompt = context_compiler.compile_system_prompt(
            self.conn, seed_instruction="SEED", state=state, project=None, last_brief=None,
        )
        self.assertIn("none selected", prompt)
        self.assertIn("fresh ship", prompt)

    def test_bounded_messages_respects_limit(self):
        session = database.create_session(self.conn, mode="master", project_id=None)
        for index in range(30):
            database.append_message(self.conn, session_id=session["id"], role="user", content=f"msg {index}")
        messages = context_compiler.bounded_messages(self.conn, session["id"], limit=5)
        self.assertEqual(len(messages), 5)
        self.assertEqual(messages[-1].content, "msg 29")

    def test_bounded_messages_scoped_by_mode_when_mode_given(self):
        session = database.create_session(self.conn, mode="master", project_id=None)
        database.append_message(self.conn, session_id=session["id"], role="user", content="master turn", mode="master")
        database.append_message(self.conn, session_id=session["id"], role="user", content="design turn", mode="design")
        database.append_message(self.conn, session_id=session["id"], role="user", content="another master turn", mode="master")

        master_only = context_compiler.bounded_messages(self.conn, session["id"], mode="master")
        self.assertEqual([m.content for m in master_only], ["master turn", "another master turn"])

        design_only = context_compiler.bounded_messages(self.conn, session["id"], mode="design")
        self.assertEqual([m.content for m in design_only], ["design turn"])

        unscoped = context_compiler.bounded_messages(self.conn, session["id"])
        self.assertEqual(len(unscoped), 3)

    def test_compile_system_prompt_includes_role_instruction_for_active_mode(self):
        state = database.get_state(self.conn)
        state["current_mode"] = "associative_lab"
        prompt = context_compiler.compile_system_prompt(
            self.conn, seed_instruction="SEED", state=state, project=None, last_brief=None,
        )
        self.assertIn("decode generously", prompt)
        self.assertNotIn("Project Formation mode", prompt)

    def test_extract_structured_reply_parses_valid_block(self):
        raw = (
            "Here is my reply.\n\n"
            "```captain-json\n"
            '{"reply": "Here is my reply.", "mode_suggestion": "design", '
            '"project_suggestion": null, "harvest_proposals": [], '
            '"state_notes": [], "safety_signal": null}\n'
            "```"
        )
        parsed = context_compiler.extract_structured_reply(raw)
        self.assertEqual(parsed["mode_suggestion"], "design")
        self.assertEqual(parsed["reply"], "Here is my reply.")

    def test_extract_structured_reply_fails_safe_on_malformed_output(self):
        raw = "I forgot to include the JSON block entirely."
        parsed = context_compiler.extract_structured_reply(raw)
        self.assertEqual(parsed["reply"], raw)
        self.assertIsNone(parsed["mode_suggestion"])
        self.assertEqual(parsed["harvest_proposals"], [])

    def test_extract_structured_reply_fails_safe_on_broken_json(self):
        raw = "Reply text\n```captain-json\n{not valid json\n```"
        parsed = context_compiler.extract_structured_reply(raw)
        self.assertEqual(parsed["reply"], raw.strip())
        self.assertEqual(parsed["harvest_proposals"], [])


if __name__ == "__main__":
    unittest.main()
