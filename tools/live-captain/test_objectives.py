import importlib.util
import tempfile
import threading
import time
import unittest
from pathlib import Path

PATH = Path(__file__).with_name("objectives.py")
SPEC = importlib.util.spec_from_file_location("live_captain_objectives", PATH)
objectives = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(objectives)


class ObjectiveStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "captain.db"
        self.store = objectives.ObjectiveStore(self.path)

    def tearDown(self):
        self.store.close(); self.tmp.cleanup()

    def propose(self, budget=3):
        return self.store.propose("Investigate a real question", "Repository only", ["Evidence returned"], budget)

    def test_no_move_before_admiral_approval(self):
        item = self.propose()
        self.assertEqual(item["state"], "AWAITING_ADMIRAL")
        self.assertIsNone(self.store.claim_move())
        approved = self.store.transition(item["id"], "approve")
        self.assertIsNotNone(approved["approved_at"])
        self.assertEqual(self.store.claim_move()[1], 1)

    def test_restart_preserves_objective_exactly(self):
        item = self.propose(2)
        self.store.close()
        self.store = objectives.ObjectiveStore(self.path)
        loaded = self.store.latest()
        self.assertEqual(loaded["id"], item["id"])
        self.assertEqual(loaded["success_criteria"], ["Evidence returned"])
        self.assertEqual(loaded["move_budget"], 2)

    def test_atomic_claim_allows_only_one_worker(self):
        item = self.propose(); self.store.transition(item["id"], "approve")
        results = []
        threads = [threading.Thread(target=lambda: results.append(self.store.claim_move())) for _ in range(4)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(sum(result is not None for result in results), 1)

    def test_budget_stops_at_checkpoint_and_reapproval_adds_three(self):
        item = self.propose(2); self.store.transition(item["id"], "approve")
        for move in (1, 2):
            claimed = self.store.claim_move(); self.assertEqual(claimed[1], move)
            current = self.store.finish_move(item["id"], move, f"result {move}")
        self.assertEqual(current["state"], "CHECKPOINT")
        self.assertIsNone(self.store.claim_move())
        current = self.store.transition(item["id"], "approve")
        self.assertEqual(current["move_budget"], 5)

    def test_watch_controller_runs_to_budget(self):
        item = self.propose(3); calls = []
        watch = objectives.WatchController(self.store, lambda obj, move: calls.append(move) or f"move {move}")
        watch.start()
        self.store.transition(item["id"], "approve"); watch.wake()
        deadline = time.time() + 2
        while self.store.latest()["state"] != "CHECKPOINT" and time.time() < deadline:
            time.sleep(.01)
        watch.close()
        self.assertEqual(calls, [1, 2, 3])
        self.assertEqual(self.store.latest()["state"], "CHECKPOINT")

    def test_pause_during_move_finishes_current_move_but_prevents_next(self):
        item = self.propose(); self.store.transition(item["id"], "approve")
        objective, move = self.store.claim_move()
        self.store.transition(item["id"], "pause")
        current = self.store.finish_move(item["id"], move, "safe stopping point")
        self.assertEqual(current["state"], "PAUSED")
        self.assertIsNone(self.store.claim_move())


if __name__ == "__main__":
    unittest.main()
