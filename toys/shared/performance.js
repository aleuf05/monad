(function (global) {
  "use strict";

  const states = new Map();
  const AXES = ["tension", "warmth", "energy", "restraint"];
  const DEFAULT_BASELINE = { tension: 0.22, warmth: 0.48, energy: 0.46, restraint: 0.68 };
  const INTENTS = {
    operational: { tension: 0.35, warmth: 0.34, energy: 0.55, restraint: 0.78, label: "measured operational report" },
    urgent: { tension: 0.78, warmth: 0.25, energy: 0.82, restraint: 0.72, label: "controlled urgency" },
    reassuring: { tension: 0.2, warmth: 0.72, energy: 0.44, restraint: 0.62, label: "steady reassurance" },
    reflective: { tension: 0.26, warmth: 0.58, energy: 0.3, restraint: 0.7, label: "quiet reflection" },
    ceremonial: { tension: 0.28, warmth: 0.42, energy: 0.52, restraint: 0.9, label: "ceremonial gravity" },
    humorous: { tension: 0.12, warmth: 0.76, energy: 0.62, restraint: 0.4, label: "restrained amusement" }
  };

  const clamp = (value, min = 0, max = 1) => Math.min(max, Math.max(min, value));
  const number = (value, fallback) => Number.isFinite(Number(value)) ? Number(value) : fallback;
  const mix = (from, to, amount) => from + (to - from) * amount;

  function characterBaseline(character = {}) {
    const traits = character.initial_tendencies || character.traits || character;
    const caution = clamp(number(traits.caution, 0.5));
    const initiative = clamp(number(traits.initiative, 0.5));
    const humor = clamp(number(traits.humor, 0.3));
    const trust = clamp(number(traits.trust, 0.5));
    return {
      tension: clamp(DEFAULT_BASELINE.tension + (caution - 0.5) * 0.22),
      warmth: clamp(DEFAULT_BASELINE.warmth + (trust - 0.5) * 0.22 + (humor - 0.3) * 0.12),
      energy: clamp(DEFAULT_BASELINE.energy + (initiative - 0.5) * 0.2),
      restraint: clamp(DEFAULT_BASELINE.restraint + (caution - 0.5) * 0.18 - (humor - 0.3) * 0.12)
    };
  }

  function plan(speaker, direction = {}, nowMs = Date.now()) {
    if (!speaker) throw new Error("Performance plan requires a speaker");
    const baseline = characterBaseline(direction.character);
    const intentName = INTENTS[direction.intent] ? direction.intent : "operational";
    const preset = INTENTS[intentName];
    const pressure = clamp(number(direction.state?.pressure, 0));
    const target = {};
    AXES.forEach((axis) => { target[axis] = mix(baseline[axis], preset[axis], 0.62); });
    target.tension = clamp(target.tension + pressure * 0.22);
    target.energy = clamp(target.energy + pressure * 0.12);
    target.restraint = clamp(target.restraint + pressure * 0.06);
    AXES.forEach((axis) => {
      if (direction.controls?.[axis] != null) target[axis] = clamp(number(direction.controls[axis], target[axis]));
    });

    const previous = states.get(speaker);
    const elapsed = previous ? Math.max(0, nowMs - previous.at) : 0;
    // A first direction establishes posture without jumping fully to it. Later
    // turns approach their target over roughly 12 seconds, preserving inertia.
    const response = previous ? clamp(1 - Math.exp(-elapsed / 12000), 0.08, 0.72) : 0.42;
    const axes = {};
    AXES.forEach((axis) => { axes[axis] = clamp(mix(previous?.axes?.[axis] ?? baseline[axis], target[axis], response)); });
    states.set(speaker, { axes, at: nowMs });

    const rate = clamp(0.9 + axes.energy * 0.19 - axes.restraint * 0.04, 0.88, 1.08);
    const pitch = clamp(0.96 + axes.warmth * 0.06 - axes.tension * 0.035, 0.94, 1.04);
    const volume = clamp(0.84 + axes.energy * 0.16, 0.86, 1);
    const reasons = [`intent:${intentName}`];
    if (pressure >= 0.65) reasons.push("sustained-pressure");
    if (direction.controls && AXES.some((axis) => direction.controls[axis] != null)) reasons.push("operator-directed");
    if (previous) reasons.push("carried-prior-state");

    return {
      schema_version: "monad.performance.v0.1",
      speaker,
      label: preset.label,
      intent: intentName,
      axes,
      target,
      voice: { rate, pitch, volume },
      reasons,
      context: direction.context || {}
    };
  }

  function inspect(speaker) { return states.get(speaker) || null; }
  function reset(speaker) { speaker ? states.delete(speaker) : states.clear(); }

  global.MonadPerformance = { plan, inspect, reset, characterBaseline, intents: () => ({ ...INTENTS }) };
})(typeof window === "undefined" ? globalThis : window);
