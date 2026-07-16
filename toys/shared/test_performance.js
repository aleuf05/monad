const assert = require("assert");
require("./performance.js");

const character = { caution: 0.65, initiative: 0.45, humor: 0.2, trust: 0.55 };
const first = MonadPerformance.plan("captain.test", { character, intent: "operational" }, 1000);
const urgent = MonadPerformance.plan("captain.test", { character, intent: "urgent", state: { pressure: 0.9 } }, 2000);
assert(urgent.axes.tension > first.axes.tension, "urgent direction raises tension");
assert(urgent.axes.tension < urgent.target.tension, "state approaches rather than jumps to target");
assert(urgent.reasons.includes("carried-prior-state"), "continuity is inspectable");

const sustained = MonadPerformance.plan("captain.test", { character, intent: "urgent", state: { pressure: 0.9 } }, 14000);
assert(sustained.axes.tension > urgent.axes.tension, "sustained state develops over time");
const recovery = MonadPerformance.plan("captain.test", { character, intent: "reassuring" }, 26000);
assert(recovery.axes.tension < sustained.axes.tension, "reassurance begins gradual recovery");
assert(recovery.axes.tension > recovery.target.tension, "recovery does not instantly erase tension");
assert(recovery.voice.rate >= 0.88 && recovery.voice.rate <= 1.08, "delivery remains within anti-caricature bounds");
assert.equal(MonadPerformance.inspect("captain.test").axes, recovery.axes);
const directed = MonadPerformance.plan("captain.directed", {
  character,
  intent: "reflective",
  controls: { warmth: 0.9, restraint: 0.8 }
}, 1000);
assert.equal(directed.target.warmth, 0.9, "operator direction overrides the intent target");
assert(directed.reasons.includes("operator-directed"));
console.log("voice performance tests passed");
