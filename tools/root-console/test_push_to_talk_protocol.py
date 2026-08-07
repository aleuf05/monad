"""Regression checks for the Root Bridge push-to-talk boot contract.

The Web Speech API itself requires a real browser and microphone for human
acceptance. These checks protect the state-machine seams that previously made
boot/reconnect/release behavior unstable.
"""

from pathlib import Path
import unittest


SCRIPT = (Path(__file__).parents[2] / "console/assets/js/root-console.js").read_text()


class PushToTalkProtocolTests(unittest.TestCase):
    def test_trigger_does_not_reference_removed_live_mode_state(self):
        self.assertNotIn("live_mode: liveMode", SCRIPT)

    def test_bridge_starts_disarmed_and_auth_loss_disarms(self):
        self.assertIn("window.captainBridgeReady = false;", SCRIPT)
        self.assertIn('window.dispatchEvent(new Event("captain-bridge-unavailable"))', SCRIPT)
        self.assertIn('btn.disabled = true;', SCRIPT)

    def test_stream_readiness_arms_protocol(self):
        self.assertIn("window.captainBridgeReady = true;", SCRIPT)
        self.assertIn('window.dispatchEvent(new Event("captain-bridge-ready"))', SCRIPT)
        self.assertIn('btn.disabled = false;', SCRIPT)

    def test_physical_hold_uses_pointer_capture(self):
        self.assertIn("btn.setPointerCapture(e.pointerId)", SCRIPT)
        self.assertIn('btn.addEventListener("pointerup", release)', SCRIPT)
        self.assertNotIn('btn.addEventListener("pointerleave"', SCRIPT)

    def test_release_commits_once_after_recognizer_flush(self):
        self.assertIn("if (!releasePending || releaseCommitted) return;", SCRIPT)
        self.assertIn("if (releasePending) setTimeout(commitReleasedUtterance, 80);", SCRIPT)
        self.assertIn("releaseTimer = setTimeout(commitReleasedUtterance, 700);", SCRIPT)

    def test_pointer_cancel_never_submits(self):
        start = SCRIPT.index('btn.addEventListener("pointercancel"')
        end = SCRIPT.index('window.addEventListener("captain-bridge-ready"', start)
        handler = SCRIPT[start:end]
        self.assertIn("releasePending = false;", handler)
        self.assertIn("stop();", handler)
        self.assertNotIn("submitDirective", handler)
        self.assertNotIn("sendLiveUtterance", handler)

    def test_direct_turn_response_can_deliver_speech_once(self):
        self.assertIn("const consumedCaptainSpeech = new Set();", SCRIPT)
        self.assertIn("if (deliveryKey && consumedCaptainSpeech.has(deliveryKey)) return;", SCRIPT)
        self.assertIn("if (body.speech_artifact) {", SCRIPT)
        self.assertIn("artifact: body.speech_artifact", SCRIPT)


if __name__ == "__main__":
    unittest.main()
