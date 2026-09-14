import test from "node:test";
import assert from "node:assert/strict";
import { SelfChatBridge, TEST_PREFIX, requestPairingCodeOnce, sanitizePairingError } from "../bridge.js";

const now = 2_000_000;
const msg = (overrides = {}) => ({
  id: "m1", remoteJid: "12345@s.whatsapp.net", fromMe: true,
  timestamp: now / 1000, text: `${TEST_PREFIX} solve a harmless test`, ...overrides,
});

function bridge(overrides = {}) {
  const calls = [];
  return { calls, bridge: new SelfChatBridge({
    ownJid: "12345@s.whatsapp.net", startedAt: now, dryRun: true,
    invokeCodex: async context => { calls.push(context); return "proposed Captain reply"; }, ...overrides,
  }) };
}

test("designated self-chat input produces one dry-run proposal", async () => {
  const { bridge: b, calls } = bridge();
  assert.deepEqual(await b.handleMessage(msg()), { action: "proposed", text: "proposed Captain reply" });
  assert.equal(calls.length, 1);
});

test("other chats invoke neither Codex nor reply", async () => {
  const { bridge: b, calls } = bridge();
  assert.equal((await b.handleMessage(msg({ id: "m2", remoteJid: "999@s.whatsapp.net" }))).action, "ignored");
  assert.equal(calls.length, 0);
});

test("duplicates, non-designated bridge replies, and replay are ignored", async () => {
  const { bridge: b, calls } = bridge();
  await b.handleMessage(msg());
  assert.equal((await b.handleMessage(msg())).reason, "stopped-or-duplicate");
  assert.equal((await b.handleMessage(msg({ id: "m3", text: "proposed Captain reply" }))).reason, "not-designated-test-input");
  assert.equal((await b.handleMessage(msg({ id: "m4", timestamp: (now - 1000) / 1000 }))).reason, "historical-replay");
  assert.equal(calls.length, 1);
});

test("backend errors do not retry or send", async () => {
  let sends = 0;
  const { bridge: b, calls } = bridge({ invokeCodex: async () => { throw new Error("Codex unavailable"); }, send: async () => { sends++; } });
  assert.deepEqual(await b.handleMessage(msg()), { action: "failed", reason: "Codex unavailable" });
  assert.equal(calls.length, 0);
  assert.equal(sends, 0);
});

test("stop control blocks later inputs and sending is disabled by default", async () => {
  const { bridge: b, calls } = bridge({ send: async () => assert.fail("send must not run") });
  b.stop();
  assert.equal((await b.handleMessage(msg({ id: "m5" }))).action, "ignored");
  assert.equal(calls.length, 0);
});

test("explicit send mode permits one fresh reply and never retries", async () => {
  let sends = 0;
  const { bridge: b } = bridge({ dryRun: false, maxSends: 1, send: async () => { sends++; } });
  assert.equal((await b.handleMessage(msg({ id: "send-1" }))).action, "sent");
  assert.equal(sends, 1);
  assert.equal((await b.handleMessage(msg({ id: "send-2" }))).reason, "send-limit-or-sender-disabled");
  assert.equal(sends, 1);
});

test("pairing request is bounded and errors are sanitized", async () => {
  const fake = { requestPairingCode: async () => { throw Object.assign(new Error("secret transport detail"), { output: { statusCode: 428 } }); } };
  await assert.rejects(() => requestPairingCodeOnce(fake, "+15551234567", 20));
  assert.equal(sanitizePairingError(Object.assign(new Error("hidden"), { output: { statusCode: 428 } })), "status 428; no retry performed");
});
