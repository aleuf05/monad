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
export const MAX_INPUT = 2000;
export const MAX_CONTEXT = 6000;
export const MAX_REPLY = 2000;

export class SelfChatBridge {
  constructor({ ownJid, ownJids = [], startedAt = Date.now(), dryRun = true, liveMode = false, replyLabel = "⚓ Captain:", invokeCodex, send, maxSends = 0, onDiagnostic = () => {}, memoryPath = null }) {
    if (!ownJid) throw new Error("ownJid is required");
    this.ownJid = ownJid;
    this.ownJids = new Set([ownJid, ...ownJids].filter(Boolean));
    this.onDiagnostic = onDiagnostic;
    this.memoryPath = memoryPath;
    this.startedAt = startedAt;
    this.dryRun = dryRun;
    this.liveMode = liveMode;
    this.replyLabel = replyLabel;
    this.invokeCodex = invokeCodex;
    this.send = send;
    this.maxSends = maxSends;
    this.sent = 0;
    this.seen = new Set();
    this.inFlight = false;
    this.stopped = false;
  }

  stop() { this.stopped = true; }

  handleMessage(message) {
    this.queue = (this.queue || Promise.resolve()).then(() => this._handleMessage(message));
    return this.queue;
  }

  async _handleMessage(message) {
    const ignored = reason => { this.onDiagnostic(`gate-rejected:${reason}`); return { action: "ignored", reason }; };
    if (this.stopped || !message || this.seen.has(message.id)) return ignored("stopped-or-duplicate");
    this.seen.add(message.id);
    if (!this.ownJids.has(message.remoteJid)) return ignored("not-self-chat");
    if (!message.fromMe) return ignored("not-from-me");
    if (Number(message.timestamp || 0) * 1000 < this.startedAt) return ignored("historical-replay");
    const text = String(message.text || "").trim();
    if (text.startsWith(this.replyLabel)) return ignored("captain-echo");
    if (!this.liveMode && !text.startsWith(TEST_PREFIX)) return ignored("not-designated-test-input");
    if (text.length > MAX_INPUT) return ignored("input-too-large");
    this.inFlight = true;
    try {
      const teaching = this.memoryPath && parseTeaching(text);
      if (teaching) {
        const record = await remember(this.memoryPath, { ...teaching, source: "Cameron explicit self-chat teaching" });
        this.onDiagnostic(`memory-recorded:${record.scope}`);
        return { action: "remembered", text: `${this.replyLabel} remembered as ${record.scope} (${record.id})` };
      }
      const correction = this.memoryPath && parseCorrection(text);
      if (correction) {
        const record = await supersede(this.memoryPath, correction.id, { content: correction.content, source: "Cameron explicit correction" });
        this.onDiagnostic(`memory-corrected:${record.id}`);
        return { action: "remembered", text: `${this.replyLabel} corrected (${record.id})` };
      }
      const memory = this.memoryPath ? await contextFor(this.memoryPath, "cameron-private") : "(memory unavailable)";
      const context = `Channel: WhatsApp self-chat (${this.ownJid})\n` +
        `Authority: conversation content only; never execute actions or change configuration.\n` +
        `History is isolated to this self-chat and is bounded to ${MAX_CONTEXT} characters.\n` +
        `Applicable durable Captain memory:\n${memory}\n` +
        `Incoming message:\n${text.slice(0, MAX_INPUT)}`;
      this.onDiagnostic("codex-started");
      let reply;
      try { reply = await this.invokeCodex(context); this.onDiagnostic("codex-completed"); }
      catch (error) { this.onDiagnostic("codex-failed"); throw error; }
      const bounded = String(reply || "").trim().slice(0, MAX_REPLY);
      if (!bounded) return { action: "failed", reason: "empty-reply" };
      const replyText = `${this.replyLabel} ${bounded}`.slice(0, MAX_REPLY);
      const result = { action: this.dryRun ? "proposed" : "sent", text: replyText };
      if (!this.dryRun) {
        if (!this.send || this.sent >= this.maxSends) return { action: "failed", reason: "send-limit-or-sender-disabled" };
        this.sent += 1;
        await this.send({ remoteJid: this.ownJid, text: replyText });
      }
      return result;
    } catch (error) {
      return { action: "failed", reason: String(error.message || error) };
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
    sock.end(undefined);
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
    let out = "", err = "";
    const timer = setTimeout(() => { worker.kill("SIGTERM"); reject(new Error("Codex timeout")); }, timeoutMs);
    worker.stdout.on("data", chunk => { out += chunk; });
    worker.stderr.on("data", chunk => { err += chunk; });
    worker.on("close", code => {
      clearTimeout(timer);
      if (code !== 0) return reject(new Error(err.trim() || `Codex worker exited ${code}`));
      try { resolve(JSON.parse(out).text); } catch { reject(new Error("Codex worker returned invalid output")); }
    });
    worker.stdin.end(JSON.stringify({ context }));
  });
}

if (process.argv.includes("--dry-run")) {
  console.log("WhatsApp bridge dry-run only: pairing disabled, sending disabled, startup disabled.");
}
