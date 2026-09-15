from __future__ import annotations

import threading
import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from persistence import LiveCaptainStore


class ContinuityRepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "live-captain.db"
        self.store = LiveCaptainStore(self.db)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_existing_messages_remain_readable_after_additive_schema(self):
        first = self.store.record_message("admiral", "old message", "k", "b", "l")
        second = self.store.record_message("captain", "old reply", "k", "b", "l")
        messages, omitted = self.store.load_recent_messages(10)
        self.assertEqual([m["seq"] for m in messages], [first, second])
        self.assertEqual([m["text"] for m in messages], ["old message", "old reply"])
        self.assertEqual(omitted, 0)

    def test_same_request_id_is_one_execution_across_two_sessions(self):
        results = []
        barrier = threading.Barrier(2)

        def reserve():
            barrier.wait()
            results.append(self.store.begin_execution(
                "request-same", "harmless isolated marker", "admiral", "bridge",
                "kernel", "bearing", "ledger",
            ))

        threads = [threading.Thread(target=reserve) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(sum(created for _, created in results), 1)
        self.assertEqual(len({execution["id"] for execution, _ in results}), 1)
        messages, _, executions = self.store.load_history()
        self.assertEqual(len([m for m in messages if m["text"] == "harmless isolated marker"]), 1)
        self.assertEqual(len(executions), 1)

    def test_completed_execution_replays_events_and_result_without_rerun(self):
        execution, created = self.store.begin_execution(
            "request-complete", "inspect isolated state", "admiral", "bridge",
        )
        self.assertTrue(created)
        self.store.record_execution_event(
            execution["id"], "codex_event", {"method": "item/completed", "item": {"type": "command", "status": "completed"}},
        )
        captain_seq = self.store.record_message("captain", "isolated result", "k", "b", "l")
        completed = self.store.update_execution(
            execution["id"], status="completed", captain_seq=captain_seq,
            thread_id="thread-isolated", result_text="isolated result",
            metadata={"tool_event_count": 1}, completed=True,
        )
        replay, created_again = self.store.begin_execution(
            "request-complete", "inspect isolated state", "admiral", "bridge",
        )
        self.assertFalse(created_again)
        self.assertEqual(replay["status"], "completed")
        self.assertEqual(replay["result_text"], completed["result_text"])
        history, _, executions = self.store.load_history()
        self.assertIn("isolated result", [m["text"] for m in history])
        self.assertEqual(executions[0]["events"][0]["event_type"], "codex_event")

    def test_failed_execution_is_durable_and_retry_is_replay_only(self):
        execution, _ = self.store.begin_execution(
            "request-failed", "fail in isolation", "admiral", "bridge",
        )
        self.store.record_execution_event(execution["id"], "failed", {"message": "isolated failure"})
        failed = self.store.update_execution(
            execution["id"], status="failed", error={"message": "isolated failure"}, completed=True,
        )
        replay, created_again = self.store.begin_execution(
            "request-failed", "fail in isolation", "admiral", "bridge",
        )
        self.assertFalse(created_again)
        self.assertEqual(replay["status"], "failed")
        self.assertEqual(replay["error"], failed["error"])
        self.assertEqual(self.store.load_history()[2][0]["events"][0]["event_type"], "failed")

    def test_restart_marks_abandoned_running_execution_as_interrupted(self):
        execution, _ = self.store.begin_execution(
            "request-interrupted", "restart isolation", "admiral", "bridge",
        )
        self.store.close()
        self.store = LiveCaptainStore(self.db)
        recovered = self.store.get_execution(execution["id"])
        self.assertEqual(recovered["status"], "failed")
        self.assertIn("restarted", recovered["error"]["message"])
        self.assertEqual(recovered["events"][-1]["event_type"], "interrupted")


if __name__ == "__main__":
    unittest.main(verbosity=2)
