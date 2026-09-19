const clone = (value, seen = new WeakMap()) => {
  if (value === null || typeof value !== "object") return value;
  if (seen.has(value)) return seen.get(value);

  const copy = Array.isArray(value) ? [] : {};
  seen.set(value, copy);
  Object.keys(value).forEach((key) => {
    copy[key] = clone(value[key], seen);
  });
  return copy;
};

const freeze = (value, seen = new WeakSet()) => {
  if (value === null || typeof value !== "object" || seen.has(value)) return value;
  seen.add(value);
  Object.keys(value).forEach((key) => freeze(value[key], seen));
  return Object.freeze(value);
};

const copyForObserver = (value) => freeze(clone(value));

export function clampSampleHz(sampleHz) {
  const numericSampleHz = Number(sampleHz);
  if (!Number.isFinite(numericSampleHz)) return 1;
  return Math.min(10, Math.max(0.1, numericSampleHz));
}

export function createObservationBus() {
  const subscribers = new Set();
  let sequence = 0;

  function publish(message) {
    subscribers.forEach((subscriber) => {
      try {
        subscriber(copyForObserver(message));
      } catch {
        // Observers are read-only side channels. Their failures must not
        // affect simulation behavior or other observers.
      }
    });
  }

  return {
    // Delivery is synchronous: messages are state-isolated, but callbacks share
    // the browser event loop and must return promptly.
    subscribe(subscriber) {
      if (typeof subscriber !== "function") throw new TypeError("subscriber must be a function");
      subscribers.add(subscriber);
      return () => subscribers.delete(subscriber);
    },

    publishEvent(tick, type, data = {}) {
      publish({ sequence: ++sequence, tick, kind: "event", event: { type, data } });
    },

    publishSnapshot(tick, state) {
      publish({ sequence: ++sequence, tick, kind: "snapshot", state });
    },
  };
}
