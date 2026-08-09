import importlib.util
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).parent

def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

turn_arbiter = load("turn_arbiter")
speech = load("speech")


class TurnArbiterTests(unittest.TestCase):
    def test_concurrent_callers_enter_in_ticket_order(self):
        arbiter = turn_arbiter.TurnArbiter(); entered = []
        first = arbiter.acquire()
        threads = []
        for _ in range(3):
            def work():
                ticket = arbiter.acquire(); entered.append(ticket); arbiter.release(ticket)
            thread = threading.Thread(target=work); thread.start(); threads.append(thread)
            time.sleep(.01)
        self.assertEqual(arbiter.status()["queued"], 3)
        arbiter.release(first)
        for thread in threads: thread.join(1)
        self.assertEqual(entered, [2, 3, 4])
        self.assertEqual(arbiter.status()["queued"], 0)

    def test_spoken_lead_removes_rendering_debris_and_bounds_length(self):
        text = "# Aye, [Admiral](https://example.test). `code` " + ("steady words " * 50) + "⟦fx: phrases=x | land⟧"
        result = speech.spoken_lead(text)
        self.assertLessEqual(len(result), 321)
        self.assertNotIn("https", result)
        self.assertNotIn("⟦fx", result)
        self.assertIn("Admiral", result)


if __name__ == "__main__": unittest.main()
