"use strict";
// Deterministic FleetCore snapshot fixtures for the Radio Traffic
// Evaluation packet (RADIO-TRAFFIC-EVALUATION-0.1.md). Every field name
// and threshold here is read directly from the real toys/radio-console/app.js
// (fuelSeverity's 0.15 critical threshold, vesselEventCursor's event_seq
// field, canonEventCursor's fleet_event_sequence field,
// captainControlSignature's exact field list, etc.) -- this file does not
// edit that source, only mirrors its documented contract so the fixtures
// actually exercise the real diff functions instead of guessing at their
// shape.
//
// Sequence: SEED (establishes cursors with no diffable content) ->
// SNAPSHOT_1 (the ten required scenarios except duplicate-posture and
// emergency-separation, which need a prior accepted posture to diff
// against) -> SNAPSHOT_2 (duplicate posture) -> SNAPSHOT_3 (emergency
// separation). Each snapshot must be applied in order to the *same* page
// load, since the diff functions are stateful across calls.

function vessel(overrides) {
  return Object.assign(
    {
      id: "monad",
      name: "Monad",
      callsign: "MONAD",
      kind: "flagship",
      status: "underway",
      position: { lat: 24.8, lng: 58.6 },
      course: 90,
      speed_mps: 10,
      fuel_fraction: 0.8,
    },
    overrides
  );
}

const SEED_VESSELS = [
  vessel({ id: "monad", kind: "flagship" }),
  vessel({ id: "scout-alpha", name: "Scout Alpha", callsign: "SCOUT ALPHA", kind: "scout", fuel_fraction: 0.8 }),
  vessel({ id: "scout-bravo", name: "Scout Bravo", callsign: "SCOUT BRAVO", kind: "scout", fuel_fraction: 0.8 }),
  vessel({ id: "scout-charlie", name: "Scout Charlie", callsign: "SCOUT CHARLIE", kind: "scout", fuel_fraction: 0.5 }),
  vessel({ id: "coaster-1", name: "Coaster One", callsign: "COASTER ONE", kind: "passive-traffic", fuel_fraction: 0.7 }),
];

const SEED_CAPTAIN_CONTROL = {
  captain_id: "captain.monad.001",
  vessel_id: "monad",
  role: "flagship-captain",
  enabled: true,
  runtime_status: "nominal",
  provider: "sim",
  status_message: "steady",
  last_report_tick: 100,
};

function seedSnapshot() {
  return {
    tick: 1000,
    sim_time: "2026-07-16T22:00:00Z",
    clock_state: "running",
    escort_mode: "off",
    vessels: SEED_VESSELS,
    watch_events: [{ id: "watch-seed-1", sequence: 1, message: "Watch established." }],
    vessel_events: [],
    canon_events: [],
    captain_controls: [SEED_CAPTAIN_CONTROL],
    escort_intents: [],
    agent_decisions: [],
  };
}

// 20 scout route_completed events (scout-bravo) + 1 routine holding event
// (scout-alpha) + 1 canon change + 1 captain-control change + 1 fuel
// transition to critical (scout-charlie) + 1 escort-mode change + 1 new
// human watch event + 1 accepted scout posture (scout-alpha).
function snapshot1() {
  const routeCompletedEvents = Array.from({ length: 20 }, (_, i) => ({
    event_seq: i + 1,
    type: "route_completed",
    vessel_id: "scout-bravo",
  }));
  const holdingEvent = { event_seq: 21, type: "holding", vessel_id: "scout-alpha" };

  return {
    tick: 1010,
    sim_time: "2026-07-16T22:01:00Z",
    clock_state: "running",
    escort_mode: "screen", // was "off" in seed -> diffEscortMode fires
    vessels: [
      vessel({ id: "monad", kind: "flagship" }),
      vessel({ id: "scout-alpha", name: "Scout Alpha", callsign: "SCOUT ALPHA", kind: "scout", fuel_fraction: 0.78 }),
      vessel({ id: "scout-bravo", name: "Scout Bravo", callsign: "SCOUT BRAVO", kind: "scout", fuel_fraction: 0.75 }),
      // was 0.5 (routine) in seed -> now <= 0.15 -> critical transition
      vessel({ id: "scout-charlie", name: "Scout Charlie", callsign: "SCOUT CHARLIE", kind: "scout", fuel_fraction: 0.1 }),
      vessel({ id: "coaster-1", name: "Coaster One", callsign: "COASTER ONE", kind: "passive-traffic", fuel_fraction: 0.68 }),
    ],
    watch_events: [
      { id: "watch-seed-1", sequence: 1, message: "Watch established." },
      { id: "watch-2", sequence: 2, message: "Lookout reports clear horizon, all quarters." },
    ],
    vessel_events: [...routeCompletedEvents, holdingEvent],
    canon_events: [{ fleet_event_sequence: 1, kind: "canon-change", detail: "test canon delta" }],
    captain_controls: [
      Object.assign({}, SEED_CAPTAIN_CONTROL, { runtime_status: "degraded", status_message: "reduced telemetry" }),
    ],
    escort_intents: [],
    agent_decisions: [{ vessel_id: "scout-alpha", posture: "advance-screen", outcome: "accepted", decision_id: "dec-1" }],
  };
}

// Same agent_decisions array plus one more entry for scout-alpha repeating
// the identical posture -- diffAgentDecisions() must see a longer array
// (records.length > lastAgentDecisionCount) to process it as "fresh" at
// all, but lastSpokenScoutPosture already matches "advance-screen" for
// scout-alpha, so this specific new record should not produce a new call.
function snapshot2(previous) {
  return Object.assign({}, previous, {
    tick: 1020,
    agent_decisions: previous.agent_decisions.concat([
      { vessel_id: "scout-alpha", posture: "advance-screen", outcome: "accepted", decision_id: "dec-2" },
    ]),
  });
}

// A genuinely new, distinct posture (emergency-separation) for a different
// vessel -- should always queue regardless of cooldown/dedupe state, since
// its topic (scout-posture:scout-bravo:emergency-separation) is new.
function snapshot3(previous) {
  return Object.assign({}, previous, {
    tick: 1030,
    agent_decisions: previous.agent_decisions.concat([
      { vessel_id: "scout-bravo", posture: "emergency-separation", outcome: "accepted", decision_id: "dec-3" },
    ]),
  });
}

function buildFixtureSequence() {
  const seed = seedSnapshot();
  const s1 = snapshot1();
  const s2 = snapshot2(s1);
  const s3 = snapshot3(s2);
  return [
    { label: "seed", snapshot: seed },
    { label: "snapshot_1_ten_scenarios", snapshot: s1 },
    { label: "snapshot_2_duplicate_posture", snapshot: s2 },
    { label: "snapshot_3_emergency_separation", snapshot: s3 },
  ];
}

module.exports = { buildFixtureSequence, seedSnapshot, snapshot1, snapshot2, snapshot3 };
