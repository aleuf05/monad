// Tests for the vessel_events cursor migration in app.js (GitHub issue #6,
// Slice C). app.js is a plain, non-modular browser script (this repo has no
// build step for static toys -- see README's "Development Notes" -- and
// this test deliberately doesn't add one). It's loaded here with Node's
// built-in vm module against stubbed DOM/Leaflet/WebSocket globals, so the
// real script runs unmodified and its actual processVesselEvents/state are
// exercised directly, not a reimplementation of the logic under test.
//
// Run: node --test toys/fleetcore-live/test_vessel_events_cursor.js

const test = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");
const fs = require("node:fs");
const path = require("node:path");

function fakeElement() {
  const el = {
    textContent: "",
    value: "",
    hidden: false,
    disabled: false,
    classList: { toggle() {}, add() {}, remove() {} },
    style: {},
    addEventListener() {},
    focus() {},
    querySelector: () => fakeElement(),
  };
  return el;
}

function fakeLeafletObject() {
  const self = {};
  for (const method of ["addTo", "setView", "panTo", "removeLayer", "setLatLng", "setIcon", "bindPopup", "openPopup", "on"]) {
    self[method] = () => self;
  }
  self.getLatLng = () => ({ lat: 0, lng: 0 });
  return self;
}

class FakeWebSocket {
  constructor() {
    this.onopen = null;
    this.onmessage = null;
    this.onclose = null;
    this.onerror = null;
  }
  send() {}
  close() {}
}

function loadApp() {
  const source = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");
  const sandbox = {
    document: { querySelector: () => fakeElement() },
    L: {
      map: () => fakeLeafletObject(),
      tileLayer: () => fakeLeafletObject(),
      divIcon: () => ({}),
      marker: () => fakeLeafletObject(),
    },
    WebSocket: FakeWebSocket,
    console,
    setTimeout,
    clearTimeout,
  };
  vm.createContext(sandbox);
  // app.js's top-level `const state = ...` and `function processVesselEvents`
  // live in the script's own lexical scope, not as sandbox properties --
  // same as a real <script> tag. Exposing them requires an epilogue in the
  // *same* parse/scope, appended before compiling, not a second vm.Script
  // run against the same sandbox (that would get its own fresh top-level
  // scope and couldn't see app.js's `const` bindings at all).
  const instrumented = `${source}\nglobalThis.__exports = { state, processVesselEvents };`;
  new vm.Script(instrumented, { filename: "app.js" }).runInContext(sandbox);
  return sandbox.__exports;
}

function event(seq, overrides = {}) {
  return {
    type: "waypoint_reached",
    vessel_id: "vessel.scout-alpha",
    route_id: 1,
    remaining_leg_count: 1,
    tick: seq,
    sim_time: "2026-07-10T20:00:00Z",
    event_seq: seq,
    ...overrides,
  };
}

test("processes every event on a fresh (never-connected) client", () => {
  const app = loadApp();
  app.processVesselEvents([event(0), event(1), event(2)]);
  assert.equal(app.state.lastVesselEventSeq, 2);
  assert.equal(app.state.lastVesselEvent.get("vessel.scout-alpha").event_seq, 2);
});

test("only processes events newer than the last seen event_seq", () => {
  const app = loadApp();
  app.processVesselEvents([event(0), event(1)]);
  const calledWith = [];
  const originalSet = app.state.lastVesselEvent.set.bind(app.state.lastVesselEvent);
  app.state.lastVesselEvent.set = (id, evt) => {
    calledWith.push(evt.event_seq);
    return originalSet(id, evt);
  };
  app.processVesselEvents([event(0), event(1), event(2), event(3)]);
  assert.deepEqual(calledWith, [2, 3], "only the two new events since last snapshot were processed");
  assert.equal(app.state.lastVesselEventSeq, 3);
});

test("no-op when nothing new (equal-length or identical batch, not just equal count)", () => {
  const app = loadApp();
  app.processVesselEvents([event(0), event(1), event(2)]);
  const before = app.state.lastVesselEventSeq;
  // Same length, same content re-delivered (e.g. an unrelated snapshot
  // field changed but vessel_events didn't) -- the old array-length cursor
  // would have already correctly no-op'd here too; this just confirms the
  // event_seq cursor doesn't regress that case.
  app.processVesselEvents([event(0), event(1), event(2)]);
  assert.equal(app.state.lastVesselEventSeq, before);
});

test("survives a rotated/shrunk array (retention truncation) without throwing or going backwards", () => {
  const app = loadApp();
  app.processVesselEvents([event(0), event(1), event(2)]);
  assert.equal(app.state.lastVesselEventSeq, 2);
  // Server restarted or rotated: the array is now shorter than before, but
  // starts with events newer than what this client already saw -- the
  // exact case that broke the old array.length-based cursor (it would have
  // done vesselEvents.slice(3) against a 2-length array and silently
  // stopped seeing anything, forever).
  app.processVesselEvents([event(3), event(4)]);
  assert.equal(app.state.lastVesselEventSeq, 4, "cursor advances correctly even though the array is now shorter");
});

test("logs a visible warning when a real gap is detected (client fell behind the retained window)", () => {
  const app = loadApp();
  app.processVesselEvents([event(0), event(1)]);
  const warnings = [];
  const originalWarn = console.warn;
  console.warn = (msg) => warnings.push(msg);
  try {
    // Retention rotated past what this client last saw (event_seq 1) --
    // the oldest retained event is now event_seq 5, so events 2-4 are
    // gone forever from this view. This must be visible, not silent.
    app.processVesselEvents([event(5), event(6)]);
  } finally {
    console.warn = originalWarn;
  }
  assert.equal(warnings.length, 1);
  assert.match(warnings[0], /gap detected/);
  assert.equal(app.state.lastVesselEventSeq, 6, "still catches up to the newest available event despite the gap");
});

test("a multi-event batch in one poll is processed in order, not just the last entry", () => {
  const app = loadApp();
  const seen = [];
  app.state.lastVesselEvent.set = (id, evt) => seen.push(evt.event_seq);
  app.processVesselEvents([event(0), event(1), event(2), event(3), event(4)]);
  assert.deepEqual(seen, [0, 1, 2, 3, 4]);
});

test("empty vessel_events array is a safe no-op, not a crash on vesselEvents[0]", () => {
  const app = loadApp();
  assert.doesNotThrow(() => app.processVesselEvents([]));
  assert.equal(app.state.lastVesselEventSeq, -1, "cursor stays at its initial sentinel");
});
