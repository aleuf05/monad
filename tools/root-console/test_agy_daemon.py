"""Unit tests for AgyDaemon and backend dispatch."""

from __future__ import annotations

import json
import os
import queue
import sys
import threading
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import agy_daemon
from agy_daemon import AgyDaemon, AgyError
import server as root_console_server

LIVE_CAPTAIN_DIR = Path(__file__).resolve().parent.parent / "live-captain"
if str(LIVE_CAPTAIN_DIR) not in sys.path:
    sys.path.append(str(LIVE_CAPTAIN_DIR))
import server as live_captain_server


class _FakePipe:
    def __init__(self, lines: list[str]):
        self._lines = list(lines)

    def __iter__(self):
        return iter(self._lines)

    def read(self) -> str:
        return "\n".join(self._lines)


class _FakePopen:
    def __init__(self, stdout_lines: list[str], stderr_text: str = "", exit_code: int = 0):
        self.stdout = _FakePipe(stdout_lines)
        self.stderr = _FakePipe([stderr_text] if stderr_text else [])
        self.returncode = exit_code
        self.pid = 99999

    def wait(self, timeout: float | None = None) -> int:
        return self.returncode

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        pass

    def kill(self) -> None:
        pass


class AgyDaemonTests(unittest.TestCase):
    def test_subscriber_queue_bounded_and_drops_oldest(self):
        daemon = AgyDaemon(cwd=Path("."))
        listener = daemon.subscribe()
        self.assertEqual(listener.maxsize, agy_daemon.SUBSCRIBER_QUEUE_SIZE)

        slow_listener = queue.Queue(maxsize=2)
        daemon._subscribers.append(slow_listener)

        daemon.broadcast({"msg": 1})
        daemon.broadcast({"msg": 2})
        daemon.broadcast({"msg": 3})

        self.assertEqual(slow_listener.get_nowait(), {"msg": 2})
        self.assertEqual(slow_listener.get_nowait(), {"msg": 3})

    def test_status_reports_truthful_agy_metadata(self):
        daemon = AgyDaemon(cwd=Path("."))
        st = daemon.status()
        self.assertEqual(st["backend"], "agy")
        self.assertEqual(st["execution_sandbox"], "workspace-write")
        self.assertEqual(st["approval_policy"], "never")
        self.assertTrue(st["running"])
        self.assertEqual(st["model"], agy_daemon.AGY_MODEL)

    def test_send_and_wait_success(self):
        daemon = AgyDaemon(cwd=Path("."))
        sample_output = [
            json.dumps({"event": "init", "conversation_id": "test-conv-1", "init": {"cwd": "/tmp"}}),
            json.dumps({"event": "step_update", "step_update": {"step_index": 1, "state": "DONE", "step_type": "user_input"}}),
            json.dumps({"event": "step_update", "step_update": {"step_index": 2, "state": "ACTIVE", "step_type": "tool", "tool_name": "run_command", "tool_info": {"parameters": {"CommandLine": "ls"}}}}),
            json.dumps({"event": "step_update", "step_update": {"step_index": 2, "state": "DONE", "step_type": "tool", "tool_name": "run_command", "tool_info": {"parameters": {"CommandLine": "ls"}, "output": "file1.txt"}}}),
            json.dumps({"event": "step_update", "step_update": {"step_index": 3, "state": "ACTIVE", "step_type": "agent_response", "text_delta": "Captain "}}),
            json.dumps({"event": "step_update", "step_update": {"step_index": 3, "state": "DONE", "step_type": "agent_response", "text_delta": "Ready.\n"}}),
            json.dumps({"event": "result", "result": {"status": "SUCCESS", "response": "Captain Ready.\n", "usage": {"input_tokens": 100, "output_tokens": 20}}}),
        ]

        def fake_popen(*args, **kwargs):
            return _FakePopen(sample_output, exit_code=0)

        with mock.patch("subprocess.Popen", side_effect=fake_popen):
            result = daemon.send_and_wait("Hello Captain", timeout=10)

        self.assertEqual(result["text"], "Captain Ready.")
        self.assertEqual(len(result["tool_events"]), 1)
        self.assertEqual(result["tool_events"][0]["command"], "run_command: ls")
        self.assertEqual(result["tool_events"][0]["text"], "file1.txt")

    def test_send_and_wait_failure_raises_agy_error(self):
        daemon = AgyDaemon(cwd=Path("."))
        error_output = [
            json.dumps({"event": "init", "conversation_id": "test-conv-err", "init": {}}),
            json.dumps({"event": "result", "result": {"status": "FAILED", "error_message": "Quota exceeded"}}),
        ]

        def fake_popen(*args, **kwargs):
            return _FakePopen(error_output, exit_code=1)

        with mock.patch("subprocess.Popen", side_effect=fake_popen):
            with self.assertRaises(AgyError) as ctx:
                daemon.send_and_wait("Do task", timeout=10)
            self.assertIn("Quota exceeded", str(ctx.exception))

    def test_empty_compiled_text_raises_value_error(self):
        daemon = AgyDaemon(cwd=Path("."))
        with self.assertRaises(ValueError):
            daemon.send_and_wait("   ")
        with self.assertRaises(ValueError):
            daemon.send_turn("   ")


class BackendDispatchTests(unittest.TestCase):
    def test_root_console_create_daemon_explicit_dispatch(self):
        with mock.patch("agy_daemon.AgyDaemon.__init__", return_value=None):
            daemon_agy = root_console_server.create_daemon("agy")
            self.assertIsInstance(daemon_agy, AgyDaemon)

        with mock.patch("claude_daemon.ClaudeDaemon.__init__", return_value=None):
            daemon_claude = root_console_server.create_daemon("claude")
            self.assertIsInstance(daemon_claude, root_console_server.ClaudeDaemon)

        with mock.patch("codex_daemon.CodexDaemon.__init__", return_value=None):
            daemon_codex = root_console_server.create_daemon("codex")
            self.assertIsInstance(daemon_codex, root_console_server.CodexDaemon)

    def test_live_captain_create_daemon_explicit_dispatch(self):
        with mock.patch("agy_daemon.AgyDaemon.__init__", return_value=None):
            daemon_agy = live_captain_server.create_daemon("agy")
            self.assertIsInstance(daemon_agy, AgyDaemon)

        with mock.patch("claude_daemon.ClaudeDaemon.__init__", return_value=None):
            daemon_claude = live_captain_server.create_daemon("claude")
            self.assertIsInstance(daemon_claude, live_captain_server.ClaudeDaemon)

        with mock.patch("codex_daemon.CodexDaemon.__init__", return_value=None):
            daemon_codex = live_captain_server.create_daemon("codex")
            self.assertIsInstance(daemon_codex, live_captain_server.CodexDaemon)

    def test_unknown_backend_fails_loudly_no_silent_fallback(self):
        for bad in ["unknown", "gemini", "gpt4", "something_else", ""]:
            with self.assertRaises(ValueError) as ctx:
                root_console_server.create_daemon(bad)
            self.assertIn("Unknown CAPTAIN_BACKEND", str(ctx.exception))

            with self.assertRaises(ValueError) as ctx:
                live_captain_server.create_daemon(bad)
            self.assertIn("Unknown CAPTAIN_BACKEND", str(ctx.exception))

    def test_default_backend_is_agy(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            if "CAPTAIN_BACKEND" in os.environ:
                del os.environ["CAPTAIN_BACKEND"]
            with mock.patch("agy_daemon.AgyDaemon.__init__", return_value=None):
                daemon_rc = root_console_server.create_daemon()
                self.assertIsInstance(daemon_rc, AgyDaemon)
                daemon_lc = live_captain_server.create_daemon()
                self.assertIsInstance(daemon_lc, AgyDaemon)


if __name__ == "__main__":
    unittest.main()
