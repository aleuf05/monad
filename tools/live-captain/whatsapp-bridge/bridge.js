#!/usr/bin/env node

/**
 * Inert WhatsApp companion bridge boundary.
 *
 * The Baileys client is deliberately not constructed by this module. Pairing,
 * sending, and startup remain explicit future operations. The event gate and
 * Codex boundary are fully testable without a WhatsApp account.
 */
import { spawn } from "node:child_process";

export const TEST_PREFIX = "CAPTAIN TEST:";
export const MAX_INPUT = 2000;
export const MAX_CONTEXT = 6000;
export const MAX_REPLY = 2000;

export class SelfChatBridge {
  constructor({ ownJid, startedAt = Date.now(), dryRun = true, invokeCodex, send }) {
    if (!ownJid) throw new Error("ownJid is required");
    this.ownJid = ownJid;
    this.startedAt = startedAt;
    this.dryRun = dryRun;
    this.invokeCodex = invokeCodex;
    this.send = send;
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
      const result = { action: this.dryRun ? "proposed" : "sent-disabled", text: bounded };
      if (!this.dryRun && this.send) await this.send({ remoteJid: this.ownJid, text: bounded });
      return result;
    } catch (error) {
      return { action: "failed", reason: String(error.message || error) };
    } finally {
      this.inFlight = false;
    }
  }
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
