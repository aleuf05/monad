import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import speech_acceptance


class SpeechAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.dict(os.environ, {
            "MONAD_SPEECH_ACCEPTANCE_PATH": str(Path(self.temp.name) / "result.json")
        })
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def test_pending_until_operator_records_result(self):
        self.assertEqual(speech_acceptance.read(), {"outcome": "pending"})
        result = speech_acceptance.record("passed", "heard clearly")
        self.assertEqual(speech_acceptance.read(), result)

    def test_fault_is_evidence_not_service_failure(self):
        result = speech_acceptance.record("fault", "recognition missed words")
        self.assertEqual(result["outcome"], "fault")

    def test_rejects_unknown_outcome_and_oversized_note(self):
        with self.assertRaises(ValueError):
            speech_acceptance.record("maybe")
        with self.assertRaises(ValueError):
            speech_acceptance.record("passed", "x" * 501)


if __name__ == "__main__":
    unittest.main()
