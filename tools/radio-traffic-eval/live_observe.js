#!/usr/bin/env node
"use strict";
// 60-second live observation against the real deployed Radio Console,
// connected to the real shared FleetCore world (not fixtures) -- the
// second half of RADIO-TRAFFIC-EVALUATION-0.1.md §7's "Tests / rollback"
// requirement, alongside evaluate.js's fixture-driven scoring. Read-only:
// this powers on the console the same way a visitor would, then samples
// editorialSuppressions/liveQueue/editorialTopics every 5s. It never sends
// a FleetCore command and never edits Radio Console's source.

const { chromium } = require("playwright");

const URL = process.argv[2] || "https://cameronlampley.com/toys/radio-console/";
const DURATION_MS = 60000;
const SAMPLE_EVERY_MS = 5000;

async function main() {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const consoleErrors = [];
  page.on("pageerror", (err) => consoleErrors.push(err.message));

  await page.goto(URL, { waitUntil: "domcontentloaded" });

  // Power on the same way a real visitor would -- clicking the real DOM
  // control, not calling internal functions. Powering on is what starts
  // live mode (see app.js's setPowered()/liveMode = true).
  await page.locator("#powerButton").click();
  await page.waitForTimeout(2000);

  const samples = [];
  const start = Date.now();
  while (Date.now() - start < DURATION_MS) {
    const sample = await page.evaluate(() => {
      const safe = (fn) => { try { return fn(); } catch { return null; } };
      return {
        t: Date.now(),
        queueLength: safe(() => liveQueue.length),
        suppressionCounts: safe(() => Object.fromEntries(editorialSuppressions.entries())),
        topicCount: safe(() => editorialTopics.size),
        linkStatus: document.querySelector("#diagSummaryLine")?.textContent || null,
      };
    });
    samples.push(sample);
    await page.waitForTimeout(SAMPLE_EVERY_MS);
  }

  const finalQueueEntries = await page.evaluate(() => {
    return liveQueue.map((e) => ({ topic: e.topic, speaker: e.speaker, kind: e.kind }));
  }).catch(() => []);

  await browser.close();

  console.log("=== 60s Live Observation ===");
  console.log("URL:", URL);
  console.log("Console errors:", consoleErrors.length ? consoleErrors : "none");
  console.log("");
  samples.forEach((s) => {
    console.log(
      `t+${Math.round((s.t - start) / 1000)}s  queue=${s.queueLength}  topics_tracked=${s.topicCount}  suppressions=${JSON.stringify(s.suppressionCounts)}  status="${s.linkStatus}"`
    );
  });
  console.log("");
  console.log("Final queued/aired entries over the window:", JSON.stringify(finalQueueEntries, null, 2));
}

main().catch((error) => {
  console.error("live_observe.js crashed:", error);
  process.exitCode = 1;
});
