#!/usr/bin/env python3
"""Tests for the Little Buddy router.

Everything here runs with no hardware, no network, and no API key. That is
the point of the sink abstraction: the ordering and failover rules are the
part worth being sure about, and they are all provable against a fake
provider and a null sink.
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from buddy_router import (  # noqa: E402
    BUFFERING, DROPPED_QUEUE_FULL, DUCK_PRIORITY, READY,
    BuddyRouter, FailoverProvider, FileSink, NullSink, Payload, PayloadError,
)
from rich_voice import BudgetExceeded  # noqa: E402


class FakeProvider:
    def __init__(self, tag=b"cloud", delay=0.0, raises=None):
        self.tag, self.delay, self.raises = tag, delay, raises
        self.calls = []
        self.failovers = []

    def render_pcm(self, *, prompt, voice_name, model):
        self.calls.append(prompt)
        if self.delay:
            time.sleep(self.delay)
        if self.raises:
            raise self.raises
        return self.tag + b":" + prompt.encode()


def payload(priority, text="hello", ts=1000):
    return {"timestamp": ts, "priority_level": priority, "text_payload": text}


class ContractTests(unittest.TestCase):
    def test_accepts_the_specified_schema(self):
        p = Payload.from_json(json.dumps(payload(5, "status nominal")))
        self.assertEqual(p.priority_level, 5)
        self.assertEqual(p.text_payload, "status nominal")

    def test_rejects_missing_fields(self):
        for drop in ("timestamp", "priority_level", "text_payload"):
            body = payload(3)
            del body[drop]
            with self.assertRaises(PayloadError, msg=drop):
                Payload.from_json(json.dumps(body))

    def test_rejects_empty_text(self):
        with self.assertRaises(PayloadError):
            Payload.from_json(json.dumps(payload(3, "   ")))

    def test_rejects_out_of_range_priority(self):
        for bad in (-1, 11, 99):
            with self.assertRaises(PayloadError):
                Payload.from_json(json.dumps(payload(bad)))

    def test_critical_threshold(self):
        self.assertFalse(Payload.from_json(json.dumps(payload(DUCK_PRIORITY - 1))).critical)
        self.assertTrue(Payload.from_json(json.dumps(payload(DUCK_PRIORITY))).critical)


class HandshakeTests(unittest.TestCase):
    def setUp(self):
        self.router = BuddyRouter(FakeProvider(), NullSink())

    def test_first_payload_is_ready_then_buffering(self):
        self.assertEqual(self.router.submit(payload(1))["status"], READY)
        self.assertEqual(self.router.submit(payload(1))["status"], BUFFERING)

    def test_malformed_payload_is_rejected_not_queued(self):
        result = self.router.submit('{"timestamp": 1}')
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(self.router.queued, 0)

    def test_queue_full_is_reported(self):
        router = BuddyRouter(FakeProvider(), NullSink(), capacity=2)
        router.submit(payload(1))
        router.submit(payload(1))
        self.assertEqual(router.submit(payload(1))["status"], DROPPED_QUEUE_FULL)


class PriorityTests(unittest.TestCase):
    def test_most_urgent_speaks_first(self):
        router = BuddyRouter(FakeProvider(), NullSink())
        router.submit(payload(0, "ambient"))
        router.submit(payload(9, "fault"))
        router.submit(payload(4, "routine"))
        order = [s.payload.text_payload for s in router.pump()]
        self.assertEqual(order, ["fault", "routine", "ambient"])

    def test_equal_priority_keeps_arrival_order(self):
        """Reordering same-priority telemetry reads as glitching."""
        router = BuddyRouter(FakeProvider(), NullSink())
        for i in range(5):
            router.submit(payload(3, f"line {i}", ts=1000))
        order = [s.payload.text_payload for s in router.pump()]
        self.assertEqual(order, [f"line {i}" for i in range(5)])

    def test_critical_ducks_whatever_is_sounding(self):
        sink = NullSink()
        router = BuddyRouter(FakeProvider(), sink)
        router.submit(payload(1, "ambient"))
        router.pump()
        self.assertEqual(sink.stops, 0)
        router.submit(payload(9, "critical fault"))
        spoken = router.pump()
        self.assertTrue(spoken[0].ducked)
        self.assertEqual(sink.stops, 1)

    def test_critical_evicts_ambient_rather_than_being_dropped(self):
        """An alert must not be lost because the queue is full of chatter."""
        router = BuddyRouter(FakeProvider(), NullSink(), capacity=3)
        for i in range(3):
            router.submit(payload(1, f"chatter {i}"))
        result = router.submit(payload(10, "EMERGENCY"))
        self.assertNotEqual(result["status"], DROPPED_QUEUE_FULL)
        texts = [s.payload.text_payload for s in router.pump()]
        self.assertEqual(texts[0], "EMERGENCY")
        self.assertEqual(len(router.dropped), 1)

    def test_criticals_do_not_evict_each_other(self):
        router = BuddyRouter(FakeProvider(), NullSink(), capacity=2)
        router.submit(payload(9, "fault a"))
        router.submit(payload(9, "fault b"))
        self.assertEqual(router.submit(payload(9, "fault c"))["status"],
                         DROPPED_QUEUE_FULL)


class FailoverTests(unittest.TestCase):
    def test_uses_primary_when_it_answers(self):
        provider = FailoverProvider(FakeProvider(b"cloud"), FakeProvider(b"local"))
        pcm = provider.render_pcm(prompt="hi", voice_name="v", model="m")
        self.assertTrue(pcm.startswith(b"cloud"))
        self.assertEqual(provider.failovers, [])

    def test_fails_over_on_timeout(self):
        provider = FailoverProvider(
            FakeProvider(b"cloud", delay=0.4), FakeProvider(b"local"),
            timeout_ms=80)
        pcm = provider.render_pcm(prompt="hi", voice_name="v", model="m")
        self.assertTrue(pcm.startswith(b"local"))
        self.assertIn("exceeded", provider.failovers[0])

    def test_fails_over_when_primary_raises(self):
        provider = FailoverProvider(
            FakeProvider(raises=RuntimeError("endpoint down")),
            FakeProvider(b"local"))
        pcm = provider.render_pcm(prompt="hi", voice_name="v", model="m")
        self.assertTrue(pcm.startswith(b"local"))
        self.assertIn("endpoint down", provider.failovers[0])

    def test_budget_exhaustion_fails_over_rather_than_erroring(self):
        """The adaptation. The packet names only timeouts, but this repo caps
        daily spend, and an exhausted budget is operationally identical to an
        unreachable endpoint: the expensive voice is gone, the cheap one
        should speak. Running out of money must not sound like a crash."""
        provider = FailoverProvider(
            FakeProvider(raises=BudgetExceeded("daily cap reached")),
            FakeProvider(b"local"))
        pcm = provider.render_pcm(prompt="hi", voice_name="v", model="m")
        self.assertTrue(pcm.startswith(b"local"))
        self.assertIn("budget exhausted", provider.failovers[0])

    def test_no_primary_configured_still_speaks(self):
        provider = FailoverProvider(None, FakeProvider(b"local"))
        pcm = provider.render_pcm(prompt="hi", voice_name="v", model="m")
        self.assertTrue(pcm.startswith(b"local"))

    def test_router_records_that_a_failover_happened(self):
        provider = FailoverProvider(
            FakeProvider(raises=RuntimeError("down")), FakeProvider(b"local"))
        router = BuddyRouter(provider, NullSink())
        router.submit(payload(5, "telemetry"))
        self.assertTrue(router.pump()[0].failed_over)


class SinkTests(unittest.TestCase):
    def test_null_sink_needs_no_hardware(self):
        sink = NullSink()
        router = BuddyRouter(FakeProvider(), sink)
        router.submit(payload(2, "no speaker required"))
        router.pump()
        self.assertEqual(len(sink.written), 1)

    def test_file_sink_writes_pcm(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.pcm"
            router = BuddyRouter(FakeProvider(), FileSink(path))
            router.submit(payload(2, "recorded"))
            router.pump()
            self.assertGreater(path.stat().st_size, 0)


class StatusTests(unittest.TestCase):
    def test_status_reports_the_contract_constants(self):
        router = BuddyRouter(FakeProvider(), NullSink())
        router.submit(payload(1))
        status = router.status()
        self.assertEqual(status["queued"], 1)
        self.assertEqual(status["duck_priority"], DUCK_PRIORITY)
        self.assertEqual(status["primary_timeout_ms"], 800)


if __name__ == "__main__":
    unittest.main(verbosity=2)
