"""Tests for Mission Director's vessel_events cursor migration (GitHub
issue #6, Slice C). advance() is pure with respect to its explicit
state/snapshot arguments -- record_evidence/request_capture/transition are
all in-memory, and the one real network call (post_command, on mission
completion) needs a real 30s dwell to reach, which these tests never do --
so this exercises the real advance() directly, not a reimplementation of
its cursor logic.

Run: python3 -m unittest tools/mission-director/test_cursor.py
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))  # mission_director.py does `import report` relative to its own dir

import mission_director as md  # noqa: E402


def vessel_event(seq, event_type="waypoint_reached", vessel_id=md.TRACKED_VESSEL_ID, **overrides):
    event = {
        "type": event_type,
        "vessel_id": vessel_id,
        "route_id": 1,
        "remaining_leg_count": 1,
        "tick": seq,
        "sim_time": "2026-07-10T20:00:00Z",
        "event_seq": seq,
    }
    event.update(overrides)
    return event


def snapshot_with(vessel_events, tick=100):
    return {
        "tick": tick,
        "sim_time": "2026-07-10T20:00:00Z",
        "vessels": [
            {"id": md.TRACKED_VESSEL_ID, "position": {"lat": 26.0, "lng": 56.0}},
            {"id": md.DUCKY_ID, "position": md.DUCKY_POSITION},
        ],
        "vessel_events": vessel_events,
    }


class CursorMigrationTests(unittest.TestCase):
    def setUp(self):
        self.state = md.new_state("test-mission")
        self.state["phase"] = "TRANSIT_UNDERWAY"

    def test_fresh_state_starts_at_sentinel(self):
        self.assertEqual(self.state["last_vessel_event_seq"], -1)

    def test_advances_cursor_and_transitions_on_new_event(self):
        snapshot = snapshot_with([vessel_event(0, "waypoint_reached", remaining_leg_count=1)])
        changed = md.advance(self.state, snapshot)
        self.assertTrue(changed)
        self.assertEqual(self.state["phase"], "STRAIT_TRANSIT")
        self.assertEqual(self.state["last_vessel_event_seq"], 0)

    def test_only_new_events_are_considered_on_the_next_poll(self):
        # First poll: events 0-1 already seen.
        md.advance(self.state, snapshot_with([vessel_event(0), vessel_event(1)]))
        seq_after_first = self.state["last_vessel_event_seq"]
        self.assertEqual(seq_after_first, 1)
        # Second poll: same two plus two genuinely new ones. Only the new
        # ones should move the phase machinery/cursor.
        changed = md.advance(
            self.state,
            snapshot_with([vessel_event(0), vessel_event(1), vessel_event(2, "route_completed"), vessel_event(3)]),
        )
        self.assertTrue(changed)
        self.assertEqual(self.state["last_vessel_event_seq"], 3)

    def test_survives_a_rotated_shrunk_array_without_losing_the_transition(self):
        md.advance(self.state, snapshot_with([vessel_event(0), vessel_event(1)]))
        self.assertEqual(self.state["last_vessel_event_seq"], 1)
        self.assertEqual(self.state["phase"], "STRAIT_TRANSIT")
        # Server rotated: array is now shorter than before (2,000-entry
        # retention truncated it), but starts with events newer than what
        # this persisted cursor already recorded -- the exact case that
        # would have broken the old array-length cursor (it would have
        # sliced past the end of a now-shorter array and silently stopped
        # seeing anything, forever, with no restart-equivalent reset since
        # this state is itself persisted to disk).
        changed = md.advance(self.state, snapshot_with([vessel_event(5, "route_completed"), vessel_event(6)]))
        self.assertTrue(changed)
        self.assertEqual(self.state["phase"], "APPROACH_QUACKEN")
        self.assertEqual(self.state["last_vessel_event_seq"], 6)

    def test_no_op_when_nothing_new(self):
        md.advance(self.state, snapshot_with([vessel_event(0), vessel_event(1)]))
        before_phase = self.state["phase"]
        before_seq = self.state["last_vessel_event_seq"]
        changed = md.advance(self.state, snapshot_with([vessel_event(0), vessel_event(1)]))
        self.assertFalse(changed)
        self.assertEqual(self.state["phase"], before_phase)
        self.assertEqual(self.state["last_vessel_event_seq"], before_seq)

    def test_untracked_vessel_events_do_not_advance_the_state_machine(self):
        snapshot = snapshot_with([vessel_event(0, "waypoint_reached", vessel_id="vessel.scout-alpha")])
        changed = md.advance(self.state, snapshot)
        self.assertFalse(changed)
        self.assertEqual(self.state["phase"], "TRANSIT_UNDERWAY")
        # The cursor still advances even for events irrelevant to the
        # tracked vessel -- otherwise a stream of other vessels' events
        # would keep re-presenting themselves as "new" forever.
        self.assertEqual(self.state["last_vessel_event_seq"], 0)

    def test_same_tick_multi_event_batch_is_scanned_in_order_not_just_first_hit(self):
        # Both a waypoint_reached and, in the same poll, the route_completed
        # that follows it -- must not get stuck re-evaluating only
        # STRAIT_TRANSIT's own check and miss the completion in the same
        # batch (see the code comment in advance() this test protects).
        snapshot = snapshot_with(
            [vessel_event(0, "waypoint_reached", tick=50), vessel_event(1, "route_completed", tick=50)]
        )
        changed = md.advance(self.state, snapshot)
        self.assertTrue(changed)
        self.assertEqual(self.state["phase"], "APPROACH_QUACKEN")


if __name__ == "__main__":
    unittest.main()
