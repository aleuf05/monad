"""Unit and Integration tests for the Job Engine & Worker Delegation."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import time
import unittest

ROOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROOT_DIR.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from job_engine import JobRunner, JobStore


import uuid

class TestJobEngine(unittest.TestCase):
    def setUp(self):
        self.tmp_db = REPO_ROOT / "data" / f"test_jobs_{uuid.uuid4().hex[:8]}.db"
        self.store = JobStore(self.tmp_db)
        self.runner = JobRunner(self.store)

    def tearDown(self):
        self.runner.wait_all(timeout=1.0)
        for suffix in ("", "-wal", "-shm"):
            p = self.tmp_db.parent / (self.tmp_db.name + suffix)
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass

    def test_job_lifecycle(self):
        job = self.store.create_job(worker="local", request="echo 'job test'")
        self.assertTrue(job["id"].startswith("job-"))
        self.assertEqual(job["state"], "pending")

        self.store.update_job(job["id"], state="running")
        running_job = self.store.get_job(job["id"])
        self.assertEqual(running_job["state"], "running")

        self.store.update_job(job["id"], state="completed", result="job test")
        completed_job = self.store.get_job(job["id"])
        self.assertEqual(completed_job["state"], "completed")
        self.assertEqual(completed_job["result"], "job test")

    def test_runner_execution(self):
        completed_events = []

        def on_done(j):
            completed_events.append(j)

        job = self.runner.submit(
            worker="local",
            request="echo 'runner test'",
            requester="admiral",
            on_complete=on_done,
        )

        # Wait for thread to finish
        for _ in range(50):
            j = self.store.get_job(job["id"])
            if j and j["state"] == "completed":
                break
            time.sleep(0.05)

        final_job = self.store.get_job(job["id"])
        self.assertIsNotNone(final_job)
        self.assertEqual(final_job["state"], "completed")
        self.assertIn("runner test", final_job["result"])
        self.assertEqual(len(completed_events), 1)

    def test_runner_cancellation(self):
        job = self.runner.submit(worker="local", request="sleep 5")
        time.sleep(0.05)
        cancelled = self.runner.cancel(job["id"])
        self.assertTrue(cancelled)
        j = self.store.get_job(job["id"])
        self.assertEqual(j["state"], "cancelled")


if __name__ == "__main__":
    unittest.main()
