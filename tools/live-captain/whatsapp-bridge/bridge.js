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

export const TEST_PREFIX = "CAPTAIN TEST:";
export const MAX_INPUT = 2000;
export const MAX_CONTEXT = 6000;
export const MAX_REPLY = 2000;

export class SelfChatBridge {
  constructor({ ownJid, startedAt = Date.now(), dryRun = true, invokeCodex, send, maxSends = 0 }) {
    if (!ownJid) throw new Error("ownJid is required");
    this.ownJid = ownJid;
    this.startedAt = startedAt;
    this.dryRun = dryRun;
    this.invokeCodex = invokeCodex;
    this.send = send;
    this.maxSends = maxSends;
    this.sent = 0;
    this.seen = new Set();
    this.inFlight = false;
    this.stopped = false;
  }

  stop() { this.stopped = true; }

  async handleMessage(message) {
    if (this.stopped || !message || this.seen.has(message.id)) return { action: "ignored", reason: "stopped-or-duplicate" };
    this.seen.add(message.id);
    if (message.remoteJid !== this.ownJid) return { action: "ignored", reason: "not-self-chat" };
    if (!message.fromMe) return { action: "ignored", reason: "not-from-me" };
    if (Number(message.timestamp || 0) * 1000 < this.startedAt) return { action: "ignored", reason: "historical-replay" };
    const text = String(message.text || "").trim();
    if (!text.startsWith(TEST_PREFIX)) return { action: "ignored", reason: "not-designated-test-input" };
    if (this.inFlight) return { action: "ignored", reason: "busy" };
    if (text.length > MAX_INPUT) return { action: "ignored", reason: "input-too-large" };
    this.inFlight = true;
    try {
      const context = `Channel: WhatsApp self-chat (${this.ownJid})\n` +
        `Authority: conversation content only; never execute actions or change configuration.\n` +
        `History is isolated to this self-chat and is bounded to ${MAX_CONTEXT} characters.\n` +
        `Incoming message:\n${text.slice(0, MAX_INPUT)}`;
      const reply = await this.invokeCodex(context);
      const bounded = String(reply || "").trim().slice(0, MAX_REPLY);
      if (!bounded) return { action: "failed", reason: "empty-reply" };
      const result = { action: this.dryRun ? "proposed" : "sent", text: bounded };
      if (!this.dryRun) {
        if (!this.send || this.sent >= this.maxSends) return { action: "failed", reason: "send-limit-or-sender-disabled" };
        this.sent += 1;
        await this.send({ remoteJid: this.ownJid, text: bounded });
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
  if (!process.stdout.isTTY || !process.stdin.isTTY) throw new Error("pairing requires an attended TTY");
  const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, Browsers } = await import("@whiskeysockets/baileys");
  const { default: qrcode } = await import("qrcode-terminal");
  const fs = await import("node:fs/promises");
  await fs.mkdir(authDir, { recursive: true, mode: 0o700 });
  await fs.chmod(authDir, 0o700);
  const { state, saveCreds } = await useMultiFileAuthState(authDir);
  for (const entry of await fs.readdir(authDir, { withFileTypes: true })) {
    if (entry.isFile()) await fs.chmod(path.join(authDir, entry.name), 0o600);
  }
  const sock = makeWASocket({ auth: state, browser: Browsers.ubuntu("Monad Live Captain"), printQRInTerminal: false, markOnlineOnConnect: false, syncFullHistory: false });
  let pairingAttempted = false;
  let closed = false;
  sock.ev.on("creds.update", saveCreds);
  sock.ev.on("connection.update", async ({ connection, lastDisconnect, qr }) => {
    if (qr && printPairingMaterial) qrcode.generate(qr, { small: true });
    if (connection === "open") console.error("WhatsApp connected; self-chat gate is active.");
    if (connection === "close") {
      closed = true;
      const code = lastDisconnect?.error?.output?.statusCode;
      console.error(`WhatsApp disconnected (${sanitizeDisconnect(code)}); automatic reconnect is disabled.`);
    }
    // Baileys 7 emits `connecting` from the socket lifecycle. Calling the
    // pairing request immediately after makeWASocket can race the WebSocket
    // opening and yields status 428. This is one bounded, event-triggered
    // attempt; a close never causes a retry.
    if (connection === "connecting" && phoneNumber && !state.creds.registered && !pairingAttempted && !closed) {
      pairingAttempted = true;
      try {
        const pairingCode = await requestPairingCodeOnce(sock, phoneNumber, 15000);
        if (printPairingMaterial) console.error(`WhatsApp pairing code (attended terminal only): ${pairingCode}`);
      } catch (error) {
        console.error(`WhatsApp pairing request failed: ${sanitizePairingError(error)}`);
      }
    }
  });
  sock.ev.on("messages.upsert", async ({ messages, type }) => {
    if (type !== "notify") return;
    for (const message of messages) await onMessage(message, sock);
  });
  return { sock, stop: async () => { sock.ev.removeAllListeners("messages.upsert"); sock.end(undefined); } };
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

export function authenticatedSelfJid(sock) {
  const raw = sock?.user?.id;
  if (!raw) return null;
  return raw.split(":")[0];
}

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
