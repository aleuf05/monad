import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE = Path(__file__).with_name("fleetnet-snapshot.py")
SPEC = importlib.util.spec_from_file_location("fleetnet_snapshot", MODULE)
fleetnet = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fleetnet)


class FleetnetOperatorWatchTests(unittest.TestCase):
    def state(self, *, down=None, failed=0, voice=True):
        return {
            "units": {"down": down or []},
            "suites": {"failed": failed, "passed": 6 - failed, "total": 6},
            "voice": {"enforced": False} if voice else None,
        }

    def healthy_probe(self, name, url, accepted, action):
        return ({"name": name, "url": url, "code": next(iter(accepted)), "ok": True}, None)

    @patch.object(fleetnet, "host_resources")
    @patch.object(fleetnet, "http_probe")
    def test_clear_watch_requests_no_action(self, probe, resources):
        probe.side_effect = self.healthy_probe
        resources.return_value = {
            "disk_used_percent": 18, "disk_available": "170G",
            "memory_available_percent": 79.0, "load_1m": 0.2,
        }
        result = fleetnet.operations(self.state())
        self.assertEqual(result["status"], "clear")
        self.assertEqual(result["alerts"], [])
        self.assertIn("no operator action", result["next_action"].lower())

    @patch.object(fleetnet, "host_resources")
    @patch.object(fleetnet, "http_probe")
    def test_failed_monad_unit_has_evidence_and_recovery_action(self, probe, resources):
        probe.side_effect = self.healthy_probe
        resources.return_value = {
            "disk_used_percent": 18, "disk_available": "170G",
            "memory_available_percent": 79.0, "load_1m": 0.2,
        }
        result = fleetnet.operations(self.state(down=[{"unit": "root-console", "state": "failed"}]))
        self.assertEqual(result["status"], "action-required")
        self.assertEqual(result["alerts"][0]["id"], "unit:root-console")
        self.assertIn("installed but not active", result["alerts"][0]["evidence"])
        self.assertIn("journalctl", result["alerts"][0]["action"])

    @patch.object(fleetnet, "host_resources")
    @patch.object(fleetnet, "http_probe")
    def test_endpoint_failure_and_resource_pressure_are_distinct_alerts(self, probe, resources):
        def probe_result(name, url, accepted, action):
            if name == "rich-voice":
                return ({"name": name, "code": 0, "ok": False}, {
                    "id": "endpoint:rich-voice", "severity": "critical",
                    "title": "rich-voice endpoint failed", "evidence": "unreachable", "action": action,
                })
            return self.healthy_probe(name, url, accepted, action)
        probe.side_effect = probe_result
        resources.return_value = {
            "disk_used_percent": 85, "disk_available": "30G",
            "memory_available_percent": 8.0, "load_1m": 3.0,
        }
        result = fleetnet.operations(self.state())
        ids = {alert["id"] for alert in result["alerts"]}
        self.assertEqual(result["status"], "action-required")
        self.assertTrue({"endpoint:rich-voice", "host:disk", "host:memory"}.issubset(ids))

    def test_master_page_uses_commissioned_live_audio_contracts(self):
        source = (fleetnet.REPO / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn('new EventSource("/live-captain-bootstrap-api/api/stream")', source)
        self.assertIn('character_id: "captain.alpha"', source)
        self.assertNotIn('character: { name: "Little Buddy"', source)
        self.assertIn('id="masterCaptainVoice"', source)
        self.assertIn('id="masterFleetVoice"', source)
        self.assertIn("function captainSpokenLead", source)
        self.assertIn('character_id: "captain.monad"', source)
        self.assertIn('event.type === "captain_speech"', source)
        self.assertNotIn('text: "Captain live. " + item.text', source)
        root_source = (fleetnet.REPO / "console" / "assets" / "js" / "root-console.js").read_text(encoding="utf-8")
        self.assertIn("playCentralCaptainSpeech", root_source)
        self.assertNotIn('fetch("/voice-api/render"', root_source)


if __name__ == "__main__":
    unittest.main()
