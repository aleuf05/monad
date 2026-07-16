#!/usr/bin/env node
"use strict";
// Self-test for scoring.js, per RADIO-TRAFFIC-EVALUATION-0.1.md §7:
// "Evaluator self-tests with known pass/fail fixtures." Pure Node, no
// browser -- proves the scorer itself correctly distinguishes a
// known-good run from a known-bad one *before* it's trusted against
// Bot 1's real implementation. Run: node selftest.js

const assert = require("assert");
const { score } = require("./scoring");

function metadataFull(topic, extra) {
  return Object.assign(
    { topic, intent: "test-intent", audience: "test-audience", editorialReason: "test-reason", speaker: "Test", text: "test" },
    extra
  );
}

// --- Known-good synthetic observation: everything the packet requires. ---
const knownGood = {
  editorialCooldownMs: 45000,
  maxUtterancesPerTopic: 2,
  suppressionCounts: {
    "canon-ledger-telemetry": 1,
    "captain-runtime-telemetry": 1,
    "routine-holding-telemetry": 1,
  },
  topics: {
    "scout-posture:scout-alpha:advance-screen": { utterances: 1 },
    "fuel:scout-charlie:critical": { utterances: 1 },
    "scout-posture:scout-bravo:emergency-separation": { utterances: 1 },
  },
  queueEntries: [
    metadataFull("scout-posture:scout-alpha:advance-screen"),
    metadataFull("fuel:scout-charlie:critical"),
    metadataFull("scout-posture:scout-bravo:emergency-separation", { interruptible: true, urgency: 1 }),
  ],
};

const goodResult = score(knownGood);
assert.strictEqual(goodResult.allPass, true, "known-good fixture must score allPass=true");
console.log("PASS: known-good synthetic observation scores allPass=true (" + goodResult.passCount + "/" + goodResult.checks.length + ")");

// --- Known-bad synthetic observation: violates several criteria at once. ---
const knownBad = {
  editorialCooldownMs: 5000, // too short
  maxUtterancesPerTopic: 2,
  suppressionCounts: {}, // nothing suppressed at all -- should fail suppression checks
  topics: {
    "scout-posture:scout-alpha:advance-screen": { utterances: 3 }, // over the limit
  },
  queueEntries: [
    // scout route completions aired directly -- should never happen
    { topic: "route-complete:scout-bravo", intent: "x", audience: "y", editorialReason: "z" },
    // missing required metadata field (no editorialReason)
    { topic: "fuel:scout-charlie:critical", intent: "x", audience: "y" },
    // duplicate posture call aired twice
    metadataFull("scout-posture:scout-alpha:advance-screen"),
    metadataFull("scout-posture:scout-alpha:advance-screen"),
    // emergency call present but not actually interruptible
    metadataFull("scout-posture:scout-bravo:emergency-separation", { interruptible: false, urgency: undefined }),
  ],
};

const badResult = score(knownBad);
assert.strictEqual(badResult.allPass, false, "known-bad fixture must score allPass=false");
const failedIds = badResult.checks.filter((c) => !c.pass).map((c) => c.id);
const expectedFailures = [
  "metadata-completeness",
  "scout-route-silence",
  "routine-telemetry-suppressed-not-silent",
  "max-utterances-per-topic",
  "cooldown-at-least-45s",
  "suppressions-inspectable",
  "emergency-separation-interruptible",
];
expectedFailures.forEach((id) => {
  assert.ok(failedIds.includes(id), `expected "${id}" to fail on the known-bad fixture, but it passed`);
});
console.log(
  "PASS: known-bad synthetic observation scores allPass=false, correctly failing " +
    expectedFailures.length +
    " targeted checks (" +
    badResult.failCount +
    "/" +
    badResult.checks.length +
    " total failed)"
);

console.log("\nAll self-tests passed. scoring.js is trustworthy for a real run.");
