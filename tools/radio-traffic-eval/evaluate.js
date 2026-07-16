#!/usr/bin/env node
"use strict";
// Radio Traffic Evaluation -- drives the real toys/radio-console/app.js
// (never edits it) through the deterministic fixtures in fixtures.js and
// scores the result against RADIO-EDITORIAL-GATE-0.1.md's acceptance
// criteria, via scoring.js. See docs/engineering-orders/
// RADIO-TRAFFIC-EVALUATION-0.1.md for scope, and selftest.js for proof the
// scorer itself is trustworthy before this file's numbers are believed.
//
// Usage: node evaluate.js [url]
//   url defaults to the live deployed page. Pass a file:// URL or a
//   different host to evaluate against a specific build.

const { chromium } = require("playwright");
const { buildFixtureSequence } = require("./fixtures");
const { score } = require("./scoring");

const DEFAULT_URL = "https://cameronlampley.com/toys/radio-console/";

async function readCommitSha() {
  const { execSync } = require("child_process");
  try {
    return execSync("git rev-parse HEAD", { cwd: __dirname }).toString().trim();
  } catch {
    return null;
  }
}

async function main() {
  const url = process.argv[2] || DEFAULT_URL;
  const commitSha = await readCommitSha();

  const browser = await chromium.launch();
  const page = await browser.newPage();
  const consoleErrors = [];
  page.on("pageerror", (err) => consoleErrors.push(err.message));
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto(url, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(500);

  const hasHooks = await page.evaluate(() => {
    return typeof applyLiveSnapshot === "function" && typeof editorialSuppressions === "object" && typeof editorialTopics === "object" && typeof liveQueue === "object";
  }).catch(() => false);

  if (!hasHooks) {
    console.error("FATAL: applyLiveSnapshot/editorialSuppressions/editorialTopics/liveQueue are not accessible on this page.");
    console.error("This evaluator reads Radio Console's real top-level script bindings without editing the file;");
    console.error("if this fails, the source has likely changed shape and fixtures.js/evaluate.js need updating to match.");
    await browser.close();
    process.exitCode = 1;
    return;
  }

  const fixtures = buildFixtureSequence();
  for (const { label, snapshot } of fixtures) {
    // eslint-disable-next-line no-loop-func
    await page.evaluate((snap) => { applyLiveSnapshot(snap); }, snapshot);
    await page.waitForTimeout(50);
    console.log(`applied fixture: ${label}`);
  }

  const observed = await page.evaluate(() => {
    return {
      suppressionCounts: Object.fromEntries(editorialSuppressions.entries()),
      topics: Object.fromEntries(
        Array.from(editorialTopics.entries()).map(([k, v]) => [k, { utterances: v.utterances, lastSpeaker: v.lastSpeaker }])
      ),
      queueEntries: liveQueue.map((e) => ({
        topic: e.topic,
        intent: e.intent,
        audience: e.audience,
        editorialReason: e.editorialReason,
        speaker: e.speaker,
        text: e.text,
        kind: e.kind,
        interruptible: e.interruptible,
        urgency: e.urgency,
      })),
      editorialCooldownMs: typeof EDITORIAL_COOLDOWN_MS !== "undefined" ? EDITORIAL_COOLDOWN_MS : null,
      maxUtterancesPerTopic: typeof MAX_UTTERANCES_PER_TOPIC !== "undefined" ? MAX_UTTERANCES_PER_TOPIC : null,
    };
  });

  await browser.close();

  const result = score(observed);

  console.log("\n=== Radio Traffic Evaluation ===");
  console.log("URL:", url);
  console.log("Commit (this evaluator's own checkout):", commitSha);
  console.log("Console errors during run:", consoleErrors.length ? consoleErrors : "none");
  console.log("Raw observed queue entries:", observed.queueEntries.length);
  console.log("Raw observed suppression reasons:", Object.keys(observed.suppressionCounts));
  console.log("");

  result.checks.forEach((c) => {
    console.log(`[${c.pass ? "PASS" : "FAIL"}] ${c.id}: ${c.description}`);
    console.log(`       ${c.detail}`);
  });

  console.log("");
  console.log(`${result.passCount}/${result.checks.length} checks passed. Overall: ${result.allPass ? "PASS" : "FAIL"}`);

  process.exitCode = result.allPass ? 0 : 2;
}

main().catch((error) => {
  console.error("evaluate.js crashed:", error);
  process.exitCode = 1;
});
