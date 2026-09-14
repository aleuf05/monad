import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { contextFor, inspect, remember, rollback, supersede } from "../memory.js";

async function temp() { return path.join(await fs.mkdtemp(path.join(os.tmpdir(), "captain-memory-")), "memory.json"); }

test("teaching persists and shared context excludes Cameron-private material", async () => {
  const file = await temp();
  const shared = await remember(file, { scope: "shared", content: "Captain replies concisely.", source: "Cameron command" });
  await remember(file, { scope: "cameron-private", content: "Private health detail.", source: "Cameron command" });
  const context = await contextFor(file, "mike-private");
  assert.match(context, /Captain replies concisely/);
  assert.doesNotMatch(context, /Private health detail/);
  assert.equal((await inspect(file)).length, 2);
  assert.equal(shared.status, "active");
});

test("correction supersedes and rollback removes active memory", async () => {
  const file = await temp();
  const first = await remember(file, { scope: "shared", content: "Old teaching", source: "test" });
  const corrected = await supersede(file, first.id, { content: "Corrected teaching", source: "test correction" });
  assert.equal((await inspect(file)).find(r => r.id === first.id).status, "superseded");
  assert.equal((await contextFor(file)).includes("Corrected teaching"), true);
  await rollback(file, corrected.id);
  assert.equal((await contextFor(file)).includes("Corrected teaching"), false);
});

test("corrupt state fails closed", async () => {
  const file = await temp();
  await fs.writeFile(file, "not-json");
  await assert.rejects(() => inspect(file), /memory unavailable/);
});
