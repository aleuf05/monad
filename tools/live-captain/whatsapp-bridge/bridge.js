#!/usr/bin/env node

/**
 * Inert WhatsApp companion bridge boundary.
 *
 * The Baileys client is deliberately not constructed by this module. Pairing,
 * sending, and startup remain explicit future operations. The event gate and
 * Codex boundary are fully testable without a WhatsApp account.
 */
import { spawn } from "node:child_process";
import process from "node:process";
import path from "node:path";
import { contextFor, parseCorrection, parseTeaching, remember, supersede } from "./memory.js";

export const TEST_PREFIX = "CAPTAIN TEST:";
export const NOTEBOOK_PREFIX = "Notebook:";
export const OPERATOR_PREFIX = "Operator:";
export const MAX_INPUT = 2000;
export const MAX_CONTEXT = 6000;
export const MAX_REPLY = 2000;

export function explicitNotebookGitAction(request) {
  const text = String(request || "").toLowerCase();
  if (/\b(?:do not|don't|never)\b[\s\S]{0,60}\b(?:commit|push)\b/.test(text)) return null;
  if (/\bfork\b[\s\S]{0,120}\b(?:pull request|pr)\b/.test(text) || /\b(?:pull request|pr)\b[\s\S]{0,120}\bfork\b/.test(text)) {
    return /\b(?:minimal|baseline|upstream)\b/.test(text) ? "publish-minimal-fork-pr" : "publish-readme-fork-pr";
  }
  if (/\bcommit\s*(?:and|,)\s*push\b/.test(text)) return "commit-readme-push";
  if (/\bauthorized\b[\s\S]{0,100}\b(?:commit|push)\b/.test(text) && /\b(?:commit|push)\b/.test(text)) return "commit-readme-push";
  return null;
}

export class SelfChatBridge {
  constructor({ ownJid, ownJids = [], mikeJids = [], startedAt = Date.now(), dryRun = true, liveMode = false, replyLabel = "⚓ Captain:", invokeCodex, invokeNotebook = null, send, maxSends = 0, onDiagnostic = () => {}, memoryPath = null }) {
    if (!ownJid) throw new Error("ownJid is required");
    this.ownJid = ownJid;
    this.ownJids = new Set([ownJid, ...ownJids].filter(Boolean));
    this.mikeJids = new Set(mikeJids.filter(Boolean));
    if ([...this.mikeJids].some(jid => jid.endsWith("@g.us"))) throw new Error("group JIDs are not allowed for Mike route");
    this.allowedJids = new Set([...this.ownJids, ...this.mikeJids]);
    this.onDiagnostic = onDiagnostic;
    this.memoryPath = memoryPath;
    this.startedAt = startedAt;
    this.dryRun = dryRun;
    this.liveMode = liveMode;
    this.replyLabel = replyLabel;
    this.invokeCodex = invokeCodex;
    this.invokeNotebook = invokeNotebook;
    this.send = send;
    this.maxSends = maxSends;
    this.sent = 0;
    this.seen = new Set();
    this.history = new Map();
    this.paused = new Set();
    this.captainOutgoingIds = new Set();
    this.pendingCaptainEchoes = new Map();
    this.inFlight = false;
    this.stopped = false;
    this.queue = Promise.resolve();
  }

  stop() { this.stopped = true; }

  isSelfChat(jid) { return this.ownJids.has(jid); }
  isMikeChat(jid) { return this.mikeJids.has(jid); }
  isPaused(jid) { return this.isMikeChat(jid) && this.paused.has("mike"); }

  rememberHistory(jid, role, text) {
    const items = this.history.get(jid) || [];
    items.push({ role, text: String(text).slice(0, MAX_INPUT) });
    this.history.set(jid, items.slice(-12));
  }

  recentHistory(jid) {
    return (this.history.get(jid) || []).map(item => `- ${item.role}: ${item.text}`).join("\n") || "(none)";
  }

  echoKey(jid, text) { return `${jid}\u0000${text}`; }

  isCaptainEcho(message) {
    if (message.id && this.captainOutgoingIds.has(message.id)) return true;
    if (this.pendingCaptainEchoes.has(this.echoKey(message.remoteJid, String(message.text || "").trim()))) return true;
    return String(message.text || "").trim().startsWith(this.replyLabel);
  }

  async replyNow(remoteJid, text) {
    const replyText = `${this.replyLabel} ${String(text).trim()}`.slice(0, MAX_REPLY);
    if (this.dryRun) return { action: "proposed", text: replyText };
    if (!this.send || this.sent >= this.maxSends) return { action: "failed", reason: "send-limit-or-sender-disabled" };
    if (this.isPaused(remoteJid)) return { action: "failed", reason: "mike-paused-before-send" };
    const key = this.echoKey(remoteJid, replyText);
    this.pendingCaptainEchoes.set(key, Date.now());
    try {
      const sent = await this.send({ remoteJid, text: replyText });
      if (sent?.key?.id) this.captainOutgoingIds.add(sent.key.id);
      this.sent += 1;
      this.rememberHistory(remoteJid, "Captain", replyText);
      return { action: "sent", text: replyText };
    } finally {
      setTimeout(() => this.pendingCaptainEchoes.delete(key), 30000).unref?.();
    }
  }

  handleMessage(message) {
    // A failed task must not poison the serialized queue for later eligible
    // messages. _handleMessage currently catches backend failures; keeping
    // this recovery boundary protects the queue if a future gate changes.
    this.queue = this.queue.catch(error => {
      this.onDiagnostic(`queue-recovered:${sanitizeBridgeError(error)}`);
      return { action: "failed", reason: sanitizeBridgeError(error) };
    }).then(() => this._handleMessage(message));
    return this.queue;
  }

  async _handleMessage(message) {
    const ignored = reason => { this.onDiagnostic(`gate-rejected:${reason}`); return { action: "ignored", reason }; };
    if (this.stopped || !message || this.seen.has(message.id)) return ignored("stopped-or-duplicate");
    this.seen.add(message.id);
    const selfChat = this.isSelfChat(message.remoteJid);
    const mikeChat = this.isMikeChat(message.remoteJid);
    if (!this.allowedJids.has(message.remoteJid)) return ignored("not-allowed-chat");
    if (this.isCaptainEcho(message)) return ignored("captain-echo");
    if (mikeChat && message.fromMe) {
      this.paused.add("mike");
      this.onDiagnostic("mike-paused:manual-takeover");
      return ignored("mike-manual-takeover");
    }
    if (selfChat && !message.fromMe) return ignored("not-from-me");
    if (Number(message.timestamp || 0) * 1000 < this.startedAt) return ignored("historical-replay");
    const text = String(message.text || "").trim();
    if (selfChat && /^Pause Mike$/i.test(text)) {
      this.paused.add("mike");
      return this.replyNow(message.remoteJid, "Mike route paused.");
    }
    if (selfChat && /^Resume Mike$/i.test(text)) {
      this.paused.delete("mike");
      return this.replyNow(message.remoteJid, "Mike route resumed; historical messages will not be replayed.");
    }
    if (selfChat && /^Mike status$/i.test(text)) {
      return this.replyNow(message.remoteJid, this.mikeJids.size ? `Mike route is ${this.paused.has("mike") ? "paused" : "enabled"}.` : "Mike route is disabled: no verified Mike identity configured.");
    }
    if (mikeChat && this.paused.has("mike")) return ignored("mike-paused");
    if (!this.liveMode && !text.startsWith(TEST_PREFIX)) return ignored("not-designated-test-input");
    if (text.length > MAX_INPUT) return ignored("input-too-large");
    this.inFlight = true;
    try {
      this.rememberHistory(message.remoteJid, message.fromMe ? "Cameron" : (mikeChat ? "Mike" : "Cameron"), text);
      const teaching = selfChat && this.memoryPath && parseTeaching(text);
      if (teaching) {
        const record = await remember(this.memoryPath, { ...teaching, source: "Cameron explicit self-chat teaching" });
        this.onDiagnostic(`memory-recorded:${record.scope}`);
        return { action: "remembered", text: `${this.replyLabel} remembered as ${record.scope} (${record.id})` };
      }
      const correction = selfChat && this.memoryPath && parseCorrection(text);
      if (correction) {
        const record = await supersede(this.memoryPath, correction.id, { content: correction.content, source: "Cameron explicit correction" });
        this.onDiagnostic(`memory-corrected:${record.id}`);
        return { action: "remembered", text: `${this.replyLabel} corrected (${record.id})` };
      }
      const notebookRequest = this.liveMode
        ? (text.startsWith(NOTEBOOK_PREFIX) ? text.slice(NOTEBOOK_PREFIX.length).trim()
          : text.startsWith(OPERATOR_PREFIX) ? text.slice(OPERATOR_PREFIX.length).trim() : "")
        : (text.startsWith(`${TEST_PREFIX} ${NOTEBOOK_PREFIX}`)
          ? text.slice(`${TEST_PREFIX} ${NOTEBOOK_PREFIX}`.length).trim() : "");
      const isNotebook = Boolean(notebookRequest && this.invokeNotebook);
      const memory = this.memoryPath
        ? await contextFor(this.memoryPath, selfChat ? "cameron-private" : "mike-private")
        : "(memory unavailable)";
      const context = `Channel: WhatsApp ${selfChat ? "self-chat" : "Mike conversation"}\n` +
        `Authority: conversation content only; never execute actions or change configuration.\n` +
        `History is isolated to this self-chat and is bounded to ${MAX_CONTEXT} characters.\n` +
        `${isNotebook && !selfChat ? "Mike mode: shared memory plus Mike-private memory only; Cameron-private memory is excluded.\n" : ""}` +
        `Applicable durable Captain memory:\n${memory}\n` +
        `Recent channel history:\n${this.recentHistory(message.remoteJid)}\n` +
        `Incoming message:\n${text.slice(0, MAX_INPUT)}`;
      this.onDiagnostic(isNotebook ? "notebook-started" : "codex-started");
      let reply;
      try {
        reply = isNotebook
          ? await this.invokeNotebook(notebookRequest, memory, explicitNotebookGitAction(notebookRequest))
          : await this.invokeCodex(context);
        this.onDiagnostic(isNotebook ? "notebook-completed" : "codex-completed");
      }
      catch (error) { this.onDiagnostic(isNotebook ? "notebook-failed" : "codex-failed"); throw error; }
      const bounded = String(reply || "").trim().slice(0, MAX_REPLY);
      if (!bounded) return { action: "failed", reason: "empty-reply" };
      if (this.isPaused(message.remoteJid)) return { action: "failed", reason: "mike-paused-before-send" };
      return await this.replyNow(message.remoteJid, bounded);
    } catch (error) {
      return { action: "failed", reason: sanitizeBridgeError(error) };
    } finally {
      this.inFlight = false;
    }
  }
}

export async function createPairedClient({ authDir, phoneNumber, onMessage, printPairingMaterial = true }) {
  if (phoneNumber) throw new Error("phone-code pairing is disabled: Baileys 7 exposes no public pre-auth WebSocket-ready event");
  const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = await import("@whiskeysockets/baileys");
  const { default: qrcode } = await import("qrcode-terminal");
  const { default: pino } = await import("pino");
  const fs = await import("node:fs/promises");
  await fs.mkdir(authDir, { recursive: true, mode: 0o700 });
  await fs.chmod(authDir, 0o700);
  const { state, saveCreds } = await useMultiFileAuthState(authDir);
  for (const entry of await fs.readdir(authDir, { withFileTypes: true })) {
    if (entry.isFile()) await fs.chmod(path.join(authDir, entry.name), 0o600);
  }
  const authStatus = classifyAuthState(state.creds);
  if (authStatus === "incomplete") {
    throw new Error("incomplete unregistered auth state; use --fresh with a separate auth directory");
  }
  // Match the successful reference client: installed Baileys defaults for
  // browser identity, protocol version, presence, and history behavior.
  const sock = makeWASocket({ auth: state, logger: pino({ level: "silent" }), printQRInTerminal: false });
  let pairingAttempted = false;
  let closed = false;
  const pendingCredentialWrites = new Set();
  const persistCreds = update => {
    const write = Promise.resolve(saveCreds(update));
    pendingCredentialWrites.add(write);
    void write.finally(() => pendingCredentialWrites.delete(write));
  };
  sock.ev.on("creds.update", persistCreds);
  sock.ev.on("connection.update", async ({ connection, lastDisconnect, qr, isNewLogin }) => {
    if (qr && printPairingMaterial) qrcode.generate(qr, { small: true });
    if (connection === "open") console.error("WhatsApp connected; self-chat gate is active.");
    if (isNewLogin) {
      await Promise.allSettled([...pendingCredentialWrites]);
      console.error("WhatsApp pairing credentials persisted; Baileys requires a manual restart.");
    }
    if (connection === "close") {
      closed = true;
      const code = lastDisconnect?.error?.output?.statusCode;
      console.error(`WhatsApp disconnected (${sanitizeDisconnect(code)}); automatic reconnect is disabled.`);
    }
    // Baileys 7 emits `connecting` from the socket lifecycle. Calling the
    // pairing request immediately after makeWASocket can race the WebSocket
    // opening and yields status 428. This is one bounded, event-triggered
    // attempt; a close never causes a retry.
    if (connection === "connecting" && !state.creds.registered && !pairingAttempted && !closed) {
      pairingAttempted = true;
      console.error(authStatus === "paired-restart-required"
        ? "WhatsApp paired state loaded; continuing the required post-pairing restart."
        : "WhatsApp QR mode: Baileys will emit QR only after its internal WebSocket-ready check.");
    }
  });
  sock.ev.on("messages.upsert", async ({ messages, type }) => {
    if (type !== "notify") return;
    for (const message of messages) {
      try { await onMessage(message, sock); }
      catch (error) { console.error(`WhatsApp handler error: ${sanitizePairingError(error)}`); }
    }
  });
  return { sock, stop: async () => {
    sock.ev.removeAllListeners("messages.upsert");
    await Promise.allSettled([...pendingCredentialWrites]);
    // libsignal rc14 currently emits the session object with console.info
    // while closing. Suppress that library-side diagnostic so key material
    // cannot enter the bridge log; do not alter or delete auth state.
    const originalInfo = console.info;
    console.info = () => {};
    try {
      sock.end(undefined);
      // libsignal closes sessions from an asynchronous callback. Keep the
      // sanitizer in place for that bounded drain before restoring logging.
      await new Promise(resolve => setTimeout(resolve, 500));
    } finally { console.info = originalInfo; }
    await Promise.allSettled([...pendingCredentialWrites]);
  } };
}

export function classifyAuthState(creds) {
  if (creds?.registered) return "registered";
  if (creds?.me && creds?.account && creds?.signalIdentities && !creds?.pairingCode) return "paired-restart-required";
  if (creds?.pairingCode || creds?.me) return "incomplete";
  return "new";
}

export function sanitizeDisconnect(code) {
  return Number.isInteger(code) ? `status ${code}` : "unknown status";
}

export function sanitizePairingError(error) {
  const code = error?.output?.statusCode;
  return `${sanitizeDisconnect(code)}; no retry performed`;
}

export function sanitizeBridgeError(error) {
  return String(error?.message || error || "unknown bridge error")
    .replace(/sk-[A-Za-z0-9_-]+/g, "<redacted-key>")
    .replace(/Bearer\s+\S+/gi, "Bearer <redacted>")
    .replace(/\/home\/[^\s:]+/g, "<local-path>")
    .slice(0, 300);
}

export async function requestPairingCodeOnce(sock, phoneNumber, timeoutMs = 15000) {
  const normalized = String(phoneNumber || "").replace(/[^0-9]/g, "");
  if (!normalized) throw new Error("--phone must include country code digits");
  return await Promise.race([
    sock.requestPairingCode(normalized),
    new Promise((_, reject) => setTimeout(() => reject(new Error("pairing readiness timeout")), timeoutMs)),
  ]);
}

export function pairingLifecycleDecision({ connection, socketReady, closed, registered, attempted }) {
  if (closed || registered || attempted) return "ignore";
  if (connection !== "connecting") return "wait";
  return socketReady ? "request" : "wait";
}

export function authenticatedSelfJids(sock) {
  const ids = [sock?.user?.id, sock?.user?.lid].filter(Boolean);
  return [...new Set(ids.map(jid => {
    const [user, domain] = jid.split("@");
    return `${user.split(":")[0]}@${domain || "s.whatsapp.net"}`;
  }))];
}

export function authenticatedSelfJid(sock) { return authenticatedSelfJids(sock)[0] || null; }

export function invokeCodexViaVerifiedAdapter(context, { timeoutMs = 90000 } = {}) {
  return new Promise((resolve, reject) => {
    const worker = spawn("python3", ["../whatsapp_codex_worker.py"], {
      cwd: new URL(".", import.meta.url).pathname,
      stdio: ["pipe", "pipe", "pipe"],
      env: { ...process.env, PYTHONPATH: ".." },
    });
    let out = "", err = "", settled = false;
    const finish = (fn, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      fn(value);
    };
    const timer = setTimeout(() => {
      worker.kill("SIGTERM");
      finish(reject, new Error("Codex timeout"));
    }, timeoutMs);
    worker.stdout.on("data", chunk => { out += chunk; });
    worker.stderr.on("data", chunk => { err += chunk; });
    worker.on("error", error => finish(reject, new Error(sanitizeBridgeError(error))));
    worker.on("close", code => {
      if (code !== 0) return finish(reject, new Error(sanitizeBridgeError(err.trim() || `Codex worker exited ${code}`)));
      try { finish(resolve, JSON.parse(out).text); }
      catch { finish(reject, new Error("Codex worker returned invalid output")); }
    });
    worker.stdin.end(JSON.stringify({ context }));
  });
}

export function invokeNotebookViaVerifiedAdapter(request, sharedMemory, { timeoutMs = 180000, gitAction = null } = {}) {
  return new Promise((resolve, reject) => {
    const worker = spawn("python3", ["notebook_codex_worker.py"], {
      cwd: new URL(".", import.meta.url).pathname,
      stdio: ["pipe", "pipe", "pipe"],
      env: { ...process.env, PYTHONPATH: ".." },
    });
    let out = "", err = "", settled = false;
    const finish = (fn, value) => { if (!settled) { settled = true; clearTimeout(timer); fn(value); } };
    const timer = setTimeout(() => { worker.kill("SIGTERM"); finish(reject, new Error("Notebook Codex timeout")); }, timeoutMs);
    worker.stdout.on("data", chunk => { out += chunk; });
    worker.stderr.on("data", chunk => { err += chunk; });
    worker.on("error", error => finish(reject, error));
    worker.on("close", code => {
      if (code !== 0) return finish(reject, new Error(err.trim() || `Notebook worker exited ${code}`));
      try { finish(resolve, JSON.parse(out).text); }
      catch { finish(reject, new Error("Notebook worker returned invalid output")); }
    });
    worker.stdin.end(JSON.stringify({ request, shared_memory: sharedMemory, git_action: gitAction }));
  });
}

if (process.argv.includes("--dry-run")) {
  console.log("WhatsApp bridge dry-run only: pairing disabled, sending disabled, startup disabled.");
}
