import queue
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import codex_daemon


class CodexDaemonQueueTests(unittest.TestCase):
    def daemon_without_process(self):
        daemon = codex_daemon.CodexDaemon.__new__(codex_daemon.CodexDaemon)
        daemon._subscribers = []
        daemon._subscribers_lock = threading.Lock()
        return daemon

    def test_subscriber_queue_is_bounded(self):
        daemon = self.daemon_without_process()
        listener = daemon.subscribe()

        self.assertEqual(listener.maxsize, codex_daemon.SUBSCRIBER_QUEUE_SIZE)

    def test_slow_subscriber_keeps_newest_events(self):
        daemon = self.daemon_without_process()
        listener = queue.Queue(maxsize=2)
        daemon._subscribers.append(listener)

        daemon.broadcast({"sequence": 1})
        daemon.broadcast({"sequence": 2})
        daemon.broadcast({"sequence": 3})

        self.assertEqual(listener.get_nowait(), {"sequence": 2})
        self.assertEqual(listener.get_nowait(), {"sequence": 3})


if __name__ == "__main__":
    unittest.main()
