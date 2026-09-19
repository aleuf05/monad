import test from "node:test";
import assert from "node:assert/strict";
import { clampSampleHz, createObservationBus } from "./observation.js";

test("snapshot sampling is clamped to the supported bounds", () => {
  assert.equal(clampSampleHz(0), 0.1);
  assert.equal(clampSampleHz(-4), 0.1);
  assert.equal(clampSampleHz(50), 10);
  assert.equal(clampSampleHz(1), 1);
});

test("observer messages are immutable copies and cannot mutate source state", () => {
  const bus = createObservationBus();
  const state = { ducks: [{ name: "Mabel", x: 10 }], food: [] };

  bus.subscribe((message) => {
    assert.equal(Object.isFrozen(message), true);
    assert.equal(Object.isFrozen(message.state), true);
    assert.equal(Object.isFrozen(message.state.ducks[0]), true);
    try { message.state.ducks[0].x = 999; } catch {}
    try { message.state.ducks.push({ name: "Intruder" }); } catch {}
  });

  bus.publishSnapshot(4, state);
  assert.deepEqual(state, { ducks: [{ name: "Mabel", x: 10 }], food: [] });
});

test("events and snapshots share monotonic sequence numbers and ticks", () => {
  const bus = createObservationBus();
  const messages = [];
  const unsubscribe = bus.subscribe((message) => messages.push(message));

  bus.publishEvent(0, "pond_started", { message: "ready" });
  bus.publishSnapshot(7, { rain: 0 });
  unsubscribe();
  bus.publishEvent(8, "not_seen");

  assert.deepEqual(messages.map(({ sequence, tick, kind }) => ({ sequence, tick, kind })), [
    { sequence: 1, tick: 0, kind: "event" },
    { sequence: 2, tick: 7, kind: "snapshot" },
  ]);
});
