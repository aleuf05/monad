"""Static contract checks for the integrated Root Console Wardroom station."""

from pathlib import Path
import unittest


ROOT = Path(__file__).parents[2]
PAGE = (ROOT / "console/index.html").read_text()
SCRIPT = (ROOT / "console/assets/js/root-console.js").read_text()


class WardroomStationTests(unittest.TestCase):
    def test_station_is_part_of_existing_console(self):
        self.assertIn('data-station="wardroom"', PAGE)
        self.assertIn('id="wardroom-board"', PAGE)
        self.assertIn('data-helm-station="wardroom"', PAGE)
        self.assertIn('new URLSearchParams(window.location.search).get("station")', SCRIPT)

    def test_meeting_uses_existing_command_and_voice_seams(self):
        start = SCRIPT.index("(function wireWardroom()")
        end = SCRIPT.index("// Universal helm", start)
        wardroom = SCRIPT[start:end]
        self.assertIn("input.value = text;", wardroom)
        self.assertIn("submitDirective();", wardroom)
        self.assertIn("unlockCaptainVoice();", wardroom)
        self.assertIn("setCaptainVoice(true);", wardroom)
        self.assertIn('speakLocally("Wardroom audio path.', wardroom)
        self.assertIn("wardroomAudioArmed = true;", wardroom)
        self.assertIn("wardroomRoomReady = true;", wardroom)
        self.assertIn("if (!wardroomRoomReady) return;", wardroom)
        self.assertNotIn('method: "POST"', wardroom)

    def test_canon_markers_do_not_claim_automatic_promotion(self):
        for marker in ("Log that", "Canon candidate", "Make that canon", "Hold that", "Not for canon", "Correction"):
            self.assertIn(marker, PAGE)
        self.assertIn("they do not silently make doctrine", PAGE)
        self.assertIn("Do not promote an unstated ruling", SCRIPT)

    def test_captain_owns_meeting_course(self):
        self.assertIn("Captain-led meeting", PAGE)
        self.assertIn("Captain owns classification, conflict checks, readback, and filing", PAGE)
        self.assertIn("Captain, call the Wardroom meeting to order", SCRIPT)

    def test_fleetnet_receiver_sounds_only_new_priority_traffic(self):
        self.assertIn('/data/fleetnet-wire.json', SCRIPT)
        self.assertIn("if (!fleetnetPrimed)", SCRIPT)
        self.assertIn("entries.slice(cursorIndex + 1)", SCRIPT)
        self.assertIn("Number(entry.priority || 0) < 4", SCRIPT)
        self.assertIn("speakLocally(`FleetNet.", SCRIPT)
        self.assertIn('localStorage.getItem("monad.fleetnetCursor")', SCRIPT)
        self.assertIn("recentPriorityMuster", SCRIPT)
        self.assertIn("if (!wardroomAudioArmed ||", SCRIPT)
        self.assertIn("Date.now() - wardroomAudioArmedAt < 4000", SCRIPT)


if __name__ == "__main__":
    unittest.main()
