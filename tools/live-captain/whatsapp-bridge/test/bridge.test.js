import test from "node:test";
import assert from "node:assert/strict";
import os from "node:os";
import path from "node:path";
import fs from "node:fs/promises";
import { SelfChatBridge, TEST_PREFIX, NOTEBOOK_PREFIX, OPERATOR_PREFIX, explicitNotebookGitAction, requestPairingCodeOnce, sanitizePairingError, pairingLifecycleDecision, classifyAuthState } from "../bridge.js";
import { remember } from "../memory.js";

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
  assert.deepEqual(await b.handleMessage(msg()), { action: "proposed", text: "⚓ Captain: proposed Captain reply" });
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

test("a failed worker releases the serialized queue for the next fresh input", async () => {
  let attempts = 0;
  const { bridge: b } = bridge({ invokeCodex: async () => {
    attempts += 1;
    if (attempts === 1) throw new Error("Codex timeout");
    return "second request completed";
  } });
  assert.deepEqual(await b.handleMessage(msg({ id: "failed-then-recover-1" })), { action: "failed", reason: "Codex timeout" });
  assert.deepEqual(await b.handleMessage(msg({ id: "failed-then-recover-2", text: `${TEST_PREFIX} second request` })),
    { action: "proposed", text: "⚓ Captain: second request completed" });
  assert.equal(attempts, 2);
});

test("stop control blocks later inputs and sending is disabled by default", async () => {
  const { bridge: b, calls } = bridge({ send: async () => assert.fail("send must not run") });
  b.stop();
  assert.equal((await b.handleMessage(msg({ id: "m5" }))).action, "ignored");
  assert.equal(calls.length, 0);
});

test("explicit notebook request uses repo worker and excludes Cameron-private memory", async () => {
  const calls = [];
  const { bridge: b } = bridge({
    liveMode: true,
    invokeCodex: async () => { throw new Error("ordinary worker must not run"); },
    invokeNotebook: async (request, memory) => { calls.push({ request, memory }); return "repo work proposed"; },
  });
  const result = await b.handleMessage(msg({ id: "notebook-1", text: `${NOTEBOOK_PREFIX} inspect the notebook tests` }));
  assert.deepEqual(result, { action: "proposed", text: "⚓ Captain: repo work proposed" });
  assert.deepEqual(calls, [{ request: "inspect the notebook tests", memory: "(memory unavailable)" }]);
});

test("dry-run notebook requests require the designated test prefix", async () => {
  const calls = [];
  const { bridge: b } = bridge({ invokeNotebook: async request => { calls.push(request); return "ok"; } });
  assert.equal((await b.handleMessage(msg({ id: "notebook-2", text: `${NOTEBOOK_PREFIX} inspect` }))).reason, "not-designated-test-input");
  assert.equal((await b.handleMessage(msg({ id: "notebook-3", text: `${TEST_PREFIX} ${NOTEBOOK_PREFIX} inspect` }))).action, "proposed");
  assert.deepEqual(calls, ["inspect"]);
});

test("Git publication requires an explicit positive commit-and-push request", () => {
  assert.equal(explicitNotebookGitAction("Please commit and push the README to origin main"), "commit-readme-push");
  assert.equal(explicitNotebookGitAction("Do not commit or push"), null);
  assert.equal(explicitNotebookGitAction("Inspect the README only"), null);
  assert.equal(explicitNotebookGitAction("Publish the minimal upstream baseline to the fork and open a pull request"), "publish-minimal-fork-pr");
});

test("operator prefix uses the authenticated self-chat worker boundary", async () => {
  const calls = [];
  const { bridge: b } = bridge({
    liveMode: true,
    invokeCodex: async () => { throw new Error("ordinary worker must not run"); },
    invokeNotebook: async request => { calls.push(request); return "operator probe complete"; },
  });
  assert.deepEqual(await b.handleMessage(msg({ id: "operator-1", text: `${OPERATOR_PREFIX} run a harmless probe` })),
    { action: "proposed", text: "⚓ Captain: operator probe complete" });
  assert.deepEqual(calls, ["run a harmless probe"]);
});

test("Mike route uses shared plus Mike-private context and excludes Cameron-private context", async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "captain-mike-"));
  const memoryPath = path.join(dir, "memory.json");
  await remember(memoryPath, { scope: "shared", content: "shared teaching", source: "test" });
  await remember(memoryPath, { scope: "mike-private", content: "Mike context", source: "test" });
  await remember(memoryPath, { scope: "cameron-private", content: "Cameron secret", source: "test" });
  const contexts = [];
  const mike = "15550000001@s.whatsapp.net";
  const b = new SelfChatBridge({ ownJid: msg().remoteJid, mikeJids: [mike], startedAt: now, liveMode: true,
    memoryPath, invokeCodex: async context => { contexts.push(context); return "Mike reply"; } });
  const result = await b.handleMessage({ id: "mike-1", remoteJid: mike, fromMe: false, timestamp: now / 1000, text: "hello Captain" });
  assert.equal(result.action, "proposed");
  assert.match(contexts[0], /shared teaching/);
  assert.match(contexts[0], /Mike context/);
  assert.doesNotMatch(contexts[0], /Cameron secret/);
  assert.equal((await b.handleMessage({ id: "other-1", remoteJid: "15550000002@s.whatsapp.net", fromMe: false, timestamp: now / 1000, text: "hello" })).reason, "not-allowed-chat");
});

test("Mike route accepts an exact configured alternate phone/LID identity", async () => {
  const mike = "15550000005@s.whatsapp.net";
  const { bridge: b } = bridge({ mikeJids: [mike], liveMode: true,
    invokeCodex: async () => "alternate identity reply" });
  const result = await b.handleMessage({ id: "mike-alt", remoteJid: "19990000005@lid", remoteJidAlt: mike,
    fromMe: false, timestamp: now / 1000, text: "hello Captain" });
  assert.equal(result.action, "proposed");
});

test("named non-Mike contacts receive shared memory without Mike-private memory", async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "captain-mom-"));
  const memoryPath = path.join(dir, "memory.json");
  await remember(memoryPath, { scope: "shared", content: "shared teaching", source: "test" });
  await remember(memoryPath, { scope: "mike-private", content: "Mike-only context", source: "test" });
  const contexts = [];
  const mom = "15550000006@s.whatsapp.net";
  const b = new SelfChatBridge({ ownJid: msg().remoteJid, contacts: [{ name: "mom", jids: [mom] }], startedAt: now, liveMode: true,
    memoryPath, invokeCodex: async context => { contexts.push(context); return "Mom reply"; } });
  assert.equal((await b.handleMessage({ id: "mom-1", remoteJid: mom, fromMe: false, timestamp: now / 1000, text: "hello" })).action, "proposed");
  assert.match(contexts[0], /shared teaching/);
  assert.doesNotMatch(contexts[0], /Mike-only context/);
});

test("Mike operator request has parity without Cameron-private context", async () => {
  const calls = [];
  const mike = "15550000003@s.whatsapp.net";
  const b = new SelfChatBridge({ ownJid: msg().remoteJid, mikeJids: [mike], startedAt: now, liveMode: true,
    invokeCodex: async () => { throw new Error("ordinary worker must not run"); },
    invokeNotebook: async request => { calls.push(request); return "operator result"; } });
  assert.equal((await b.handleMessage({ id: "mike-op", remoteJid: mike, fromMe: false, timestamp: now / 1000, text: `${OPERATOR_PREFIX} inspect status` })).action, "proposed");
  assert.deepEqual(calls, ["inspect status"]);
});

test("Mike manual takeover pauses, resume does not replay backlog, and Captain echoes are ignored", async () => {
  const mike = "15550000004@s.whatsapp.net";
  const calls = [];
  const b = new SelfChatBridge({ ownJid: msg().remoteJid, mikeJids: [mike], startedAt: now, liveMode: true,
    invokeCodex: async () => { calls.push(true); return "reply"; } });
  assert.equal((await b.handleMessage({ id: "takeover", remoteJid: mike, fromMe: true, timestamp: now / 1000, text: "Cameron manual message" })).reason, "mike-manual-takeover");
  assert.equal((await b.handleMessage({ id: "paused", remoteJid: mike, fromMe: false, timestamp: now / 1000, text: "backlog" })).reason, "mike-paused");
  assert.equal((await b.handleMessage({ id: "resume", remoteJid: msg().remoteJid, fromMe: true, timestamp: now / 1000, text: "Resume Mike" })).action, "proposed");
  assert.equal((await b.handleMessage({ id: "fresh", remoteJid: mike, fromMe: false, timestamp: now / 1000, text: "fresh" })).action, "proposed");
  assert.equal((await b.handleMessage({ id: "echo", remoteJid: mike, fromMe: true, timestamp: now / 1000, text: "⚓ Captain: reply" })).reason, "captain-echo");
  assert.equal(calls.length, 1);
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

test("pairing lifecycle waits for readiness and never acts after close", () => {
  assert.equal(pairingLifecycleDecision({ connection: "connecting", socketReady: false, closed: false, registered: false, attempted: false }), "wait");
  assert.equal(pairingLifecycleDecision({ connection: "connecting", socketReady: true, closed: false, registered: false, attempted: false }), "request");
  assert.equal(pairingLifecycleDecision({ connection: "connecting", socketReady: true, closed: true, registered: false, attempted: false }), "ignore");
  assert.equal(pairingLifecycleDecision({ connection: "connecting", socketReady: true, closed: false, registered: true, attempted: false }), "ignore");
  assert.equal(pairingLifecycleDecision({ connection: "connecting", socketReady: true, closed: false, registered: false, attempted: true }), "ignore");
});

test("paired-but-restart-required credentials are distinct from incomplete state", () => {
  // pair-success supplies account + signalIdentities while Baileys leaves
  // registered=false until the required manual restart.
  const legitimate = { registered: false, me: { id: "redacted@s.whatsapp.net", lid: "redacted@lid" }, account: {}, signalIdentities: [] };
  const incomplete = { registered: false, me: { id: "redacted@s.whatsapp.net" }, pairingCode: "present" };
  assert.equal(classifyAuthState(legitimate), "paired-restart-required");
  assert.equal(classifyAuthState(incomplete), "incomplete");
  assert.equal(classifyAuthState({ registered: true, me: {} }), "registered");
});
