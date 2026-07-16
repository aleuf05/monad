"use strict";
// Pure scoring logic for the Radio Traffic Evaluation packet
// (RADIO-TRAFFIC-EVALUATION-0.1.md §6). No browser, no I/O -- this module
// takes the observed state captured after running fixtures.js's sequence
// through the real page, and returns a structured pass/fail report. Kept
// separate from evaluate.js (which drives Playwright) specifically so it
// can be self-tested against synthetic known-good/known-bad inputs without
// needing a browser at all -- see selftest.js.

function topicHasPrefix(entry, prefix) {
  return typeof entry.topic === "string" && entry.topic.startsWith(prefix);
}

function countSuppressions(suppressionCounts, reason) {
  return suppressionCounts[reason] || 0;
}

// observed shape:
// {
//   suppressionCounts: { [reason]: count },
//   topics: { [topic]: { utterances, lastSpeaker, lastAt } },
//   queueEntries: [ { topic, intent, audience, editorialReason, speaker, text, ... } ],
//   editorialCooldownMs: number,
//   maxUtterancesPerTopic: number,
// }
function score(observed) {
  const checks = [];

  function check(id, description, pass, detail) {
    checks.push({ id, description, pass: Boolean(pass), detail: detail || "" });
  }

  const queue = observed.queueEntries || [];
  const suppressions = observed.suppressionCounts || {};
  const topics = observed.topics || {};

  // 1. Every aired entry carries full editorial metadata.
  const missingMetadata = queue.filter(
    (e) => !e.topic || !e.intent || !e.audience || !e.editorialReason
  );
  check(
    "metadata-completeness",
    "Every aired entry has topic, intent, audience, editorialReason",
    queue.length > 0 && missingMetadata.length === 0,
    missingMetadata.length ? `${missingMetadata.length}/${queue.length} entries missing a field` : `${queue.length}/${queue.length} complete`
  );

  // 2. 20 scout route_completed events yield zero calls (and, per the
  // source comment, zero suppression-tracking too -- scouts `break` out
  // silently rather than calling suppressRadioEvent at all).
  const scoutRouteCalls = queue.filter((e) => topicHasPrefix(e, "route-complete:scout-") || topicHasPrefix(e, "route:scout-"));
  check(
    "scout-route-silence",
    "20 scout route_completed events yield zero radio calls",
    scoutRouteCalls.length === 0,
    `${scoutRouteCalls.length} scout-route-topic entries aired`
  );

  // 3. Canon / captain-runtime / routine-holding telemetry yield zero calls,
  // and register as suppressions instead.
  const routineTelemetryTopics = ["canon:", "captain-control:", "holding:"];
  const routineTelemetryCalls = queue.filter((e) => routineTelemetryTopics.some((p) => topicHasPrefix(e, p)));
  check(
    "routine-telemetry-silence",
    "Canon / captain-runtime / routine-holding telemetry yield zero calls",
    routineTelemetryCalls.length === 0,
    `${routineTelemetryCalls.length} routine-telemetry entries aired`
  );
  const canonSuppressed = countSuppressions(suppressions, "canon-ledger-telemetry") > 0;
  const captainRuntimeSuppressed = countSuppressions(suppressions, "captain-runtime-telemetry") > 0;
  const holdingSuppressed = countSuppressions(suppressions, "routine-holding-telemetry") > 0;
  check(
    "routine-telemetry-suppressed-not-silent",
    "Canon/captain-runtime/holding are recorded as suppressions, not just absent",
    canonSuppressed && captainRuntimeSuppressed && holdingSuppressed,
    `canon=${canonSuppressed} captain=${captainRuntimeSuppressed} holding=${holdingSuppressed}`
  );

  // 4. Accepted posture (scout-alpha, advance-screen) yields exactly one
  // addressed Scout Net call.
  const advanceScreenCalls = queue.filter((e) => e.topic === "scout-posture:scout-alpha:advance-screen");
  check(
    "accepted-posture-one-call",
    "Accepted posture change yields exactly one addressed call",
    advanceScreenCalls.length === 1,
    `${advanceScreenCalls.length} calls for scout-posture:scout-alpha:advance-screen`
  );

  // 5. Duplicate posture (same vessel, same posture, second decision
  // record) is suppressed -- i.e. still exactly one call for that topic,
  // not two, after the duplicate fixture snapshot is applied.
  check(
    "duplicate-posture-suppressed",
    "A repeated identical posture decision does not produce a second call",
    advanceScreenCalls.length === 1,
    `topic call count after duplicate fixture: ${advanceScreenCalls.length}`
  );

  // 6. Critical fuel (scout-charlie, seed 0.5 -> 0.1) yields one
  // recommendation call.
  const fuelCalls = queue.filter((e) => e.topic === "fuel:scout-charlie:critical");
  check(
    "critical-fuel-one-call",
    "Critical fuel transition yields exactly one recommendation call",
    fuelCalls.length === 1,
    `${fuelCalls.length} calls for fuel:scout-charlie:critical`
  );

  // 7. Emergency separation can interrupt -- present, interruptible, high
  // urgency.
  const emergencyCalls = queue.filter((e) => e.topic === "scout-posture:scout-bravo:emergency-separation");
  const emergencyOk = emergencyCalls.length === 1 && emergencyCalls[0].interruptible === true && emergencyCalls[0].urgency === 1;
  check(
    "emergency-separation-interruptible",
    "Emergency separation airs once, marked interruptible with urgency 1",
    emergencyOk,
    emergencyCalls.length === 1
      ? `interruptible=${emergencyCalls[0].interruptible} urgency=${emergencyCalls[0].urgency}`
      : `${emergencyCalls.length} calls for that topic`
  );

  // 8. No topic exceeds MAX_UTTERANCES_PER_TOPIC (read from source, not
  // assumed).
  const overLimitTopics = Object.entries(topics).filter(
    ([, t]) => t.utterances > (observed.maxUtterancesPerTopic || 2)
  );
  check(
    "max-utterances-per-topic",
    `No topic exceeds ${observed.maxUtterancesPerTopic || 2} utterances (source constant)`,
    overLimitTopics.length === 0,
    overLimitTopics.length ? overLimitTopics.map(([k, v]) => `${k}=${v.utterances}`).join(", ") : "none over limit"
  );

  // 9. Editorial cooldown is at least 45 seconds (read from source).
  check(
    "cooldown-at-least-45s",
    "Editorial cooldown constant is at least 45000ms",
    (observed.editorialCooldownMs || 0) >= 45000,
    `EDITORIAL_COOLDOWN_MS = ${observed.editorialCooldownMs}`
  );

  // 10. Suppressed counts/reasons are inspectable (true by construction if
  // we have any suppression entries at all after a run that should have
  // produced several).
  check(
    "suppressions-inspectable",
    "Suppression counts by reason are readable after a run",
    Object.keys(suppressions).length > 0,
    `${Object.keys(suppressions).length} distinct suppression reasons observed`
  );

  const passCount = checks.filter((c) => c.pass).length;
  return {
    checks,
    passCount,
    failCount: checks.length - passCount,
    allPass: checks.every((c) => c.pass),
  };
}

module.exports = { score };
