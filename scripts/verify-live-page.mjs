#!/usr/bin/env node
/**
 * Drive a live page in a real browser and report what actually happened.
 *
 * Editing `web/` is deploying — there is no build step — so "verified" has
 * to mean the real URL rendered in a real engine, not that the diff read
 * correctly. This caught two genuine bugs on 2026-08-05 that reading the
 * diff did not: the only buttons on a panel rendered below the fold, and a
 * `#id { display: flex }` rule beating the UA's `[hidden] { display: none }`
 * so a placeholder stayed painted on top of every loaded 3D model.
 *
 * Usage:
 *   node scripts/verify-live-page.mjs [url] [--shot out.png] [--wait ms]
 *   node scripts/verify-live-page.mjs https://cameronlampley.com/
 *
 * Playwright is not a dependency of this repo; it is resolved from the npx
 * cache if present. If it is missing the script says so and exits 2 rather
 * than pretending it verified anything.
 */

import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";

const NPX_CACHE = `${process.env.HOME}/.npm/_npx`;

function findPlaywright() {
  if (!existsSync(NPX_CACHE)) return null;
  for (const dir of readdirSync(NPX_CACHE)) {
    const candidate = join(NPX_CACHE, dir, "node_modules/playwright/index.mjs");
    if (existsSync(candidate)) return candidate;
  }
  return null;
}

const args = process.argv.slice(2);
const url = args.find((a) => !a.startsWith("--")) || "https://cameronlampley.com/";
const shot = args.includes("--shot") ? args[args.indexOf("--shot") + 1] : null;
const wait = args.includes("--wait") ? Number(args[args.indexOf("--wait") + 1]) : 6000;

const playwrightPath = findPlaywright();
if (!playwrightPath) {
  console.error("playwright not found in the npx cache — cannot verify.");
  console.error("install it, or run: npx playwright@latest --version");
  process.exit(2);
}

const { chromium } = await import(playwrightPath);

const errors = [];
const failedRequests = [];
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1400, height: 1200 } });

page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
page.on("pageerror", (e) => errors.push(String(e)));
page.on("requestfailed", (r) => failedRequests.push(`${r.url()} — ${r.failure()?.errorText}`));

const response = await page.goto(url, { waitUntil: "networkidle" }).catch((e) => {
  console.error("navigation failed:", e.message);
  return null;
});
if (!response) { await browser.close(); process.exit(1); }

await page.waitForTimeout(wait);

// Horizontal overflow is the single most common responsive regression and
// the page body must never scroll sideways.
const overflow = await page.evaluate(() =>
  document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);

const title = await page.title();
const outPath = shot || "/tmp/verify-live-page.png";
await page.screenshot({ path: outPath, fullPage: false });

console.log(`URL          ${url}`);
console.log(`STATUS       ${response.status()}`);
console.log(`TITLE        ${title}`);
console.log(`H-OVERFLOW   ${overflow ? "YES — page scrolls sideways, fix this" : "no"}`);
console.log(`CONSOLE ERR  ${errors.length ? errors.length : "none"}`);
errors.slice(0, 8).forEach((e) => console.log(`  · ${e}`));
console.log(`FAILED REQ   ${failedRequests.length ? failedRequests.length : "none"}`);
failedRequests.slice(0, 8).forEach((r) => console.log(`  · ${r}`));
console.log(`SCREENSHOT   ${outPath}`);
console.log("\nNow look at the screenshot. Both bugs this script was written");
console.log("after were invisible to assertions and obvious in the image.");

await browser.close();
process.exit(errors.length || overflow ? 1 : 0);
