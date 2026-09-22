#!/usr/bin/env node
import process from "node:process";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
import { SelfChatBridge, createPairedClient, authenticatedSelfJids, invokeCodexViaVerifiedAdapter, invokeNotebookViaVerifiedAdapter } from "./bridge.js";
import { DEFAULT_MEMORY_PATH } from "./memory.js";

const identityFingerprint = value => value
  ? crypto.createHash("sha256").update(String(value)).digest("hex").slice(0, 12)
  : null;
const identityForm = value => {
  if (!value) return "missing";
  if (String(value).endsWith("@lid")) return "@lid";
  if (String(value).endsWith("@s.whatsapp.net")) return "@s.whatsapp.net";
  if (String(value).endsWith("@g.us")) return "group";
  return "other";
};
const identityDiagnostic = (message, mikeJids, ownJids) => {
  const key = message?.key || {};
  const fields = {
    remoteJid: key.remoteJid,
    remoteJidAlt: key.remoteJidAlt,
    participant: key.participant,
    participantAlt: key.participantAlt,
    senderPn: key.senderPn,
    senderLid: key.senderLid,
  };
  return Object.fromEntries(Object.entries(fields)
    .filter(([, value]) => value)
    .map(([name, value]) => [name, {
      form: identityForm(value),
      fingerprint: identityFingerprint(value),
      self: ownJids.includes(value),
      mike: mikeJids.includes(value),
    }]));
};

const args = new Set(process.argv.slice(2));
const pair = args.has("--pair");
const sendOnce = args.has("--send-once");
const liveMode = args.has("--live");
const fresh = args.has("--fresh");
if (!pair && !sendOnce && !liveMode) { console.error("Refusing to start: choose --pair, --send-once, or --live explicitly."); process.exit(2); }
if (pair && (!process.stdout.isTTY || !process.stdin.isTTY)) { console.error("--pair requires an attended TTY."); process.exit(2); }
if (fresh && !pair) { console.error("--fresh requires --pair and never deletes an existing auth directory."); process.exit(2); }
if (process.env.WHATSAPP_PAIR_PHONE) { console.error("Phone-code pairing is disabled for this Baileys version; use fresh QR pairing with --fresh --pair."); process.exit(2); }
const defaultAuth = path.resolve(path.dirname(fileURLToPath(import.meta.url)), fresh ? "auth-state-fresh" : "auth-state");
const authDir = process.env.WHATSAPP_AUTH_DIR || defaultAuth;
const mikeJids = String(process.env.WHATSAPP_MIKE_JIDS || "").split(",").map(value => value.trim()).filter(Boolean);
if (mikeJids.some(jid => !/^(?:\d+@s\.whatsapp\.net|\d+@lid)$/.test(jid))) {
  console.error("WHATSAPP_MIKE_JIDS must contain verified phone JIDs (@s.whatsapp.net) or LIDs (@lid); groups are rejected.");
  process.exit(2);
}
const startedAt = Date.now();
let bridge, client, stopped = false;
const stop = async () => { if (stopped) return; stopped = true; await client?.stop(); process.exit(0); };
process.once("SIGINT", stop); process.once("SIGTERM", stop);

try { client = await createPairedClient({
  authDir,
  phoneNumber: undefined,
  onMessage: async (message, sock) => {
    const ownJids = authenticatedSelfJids(sock);
    const ownJid = ownJids[0];
    if (!ownJid) return;
    const text = message.message?.conversation || message.message?.extendedTextMessage?.text || "";
    console.error(`WhatsApp identity diagnostic: ${JSON.stringify(identityDiagnostic(message, mikeJids, ownJids))}`);
    console.error(`WhatsApp message event: text=${Boolean(text)} fromMe=${Boolean(message.key.fromMe)} selfChat=${ownJids.includes(message.key.remoteJid)} mikeChat=${mikeJids.includes(message.key.remoteJid)} timestamp=${Boolean(message.messageTimestamp)}`);
    if (!bridge) {
      bridge = new SelfChatBridge({ ownJid, ownJids, mikeJids, startedAt, liveMode, dryRun: !liveMode && !sendOnce, maxSends: sendOnce ? 1 : (liveMode ? Number.MAX_SAFE_INTEGER : 0), memoryPath: process.env.CAPTAIN_MEMORY_PATH || DEFAULT_MEMORY_PATH,
        onDiagnostic: phase => console.error(`WhatsApp Codex worker: ${phase}`),
        invokeCodex: context => invokeCodexViaVerifiedAdapter(context),
        invokeNotebook: (request, sharedMemory, gitAction) => invokeNotebookViaVerifiedAdapter(request, sharedMemory, { gitAction }),
        send: async payload => await sock.sendMessage(payload.remoteJid, { text: payload.text }) });
      console.error("Authenticated WhatsApp self-chat identity verified (identifier withheld).");
      console.error(mikeJids.length ? "Mike route configured with verified identities (identifiers withheld)." : "Mike route disabled: no verified identity configured.");
    }
    const result = await bridge.handleMessage({ id: message.key.id, remoteJid: message.key.remoteJid,
      fromMe: Boolean(message.key.fromMe), timestamp: Number(message.messageTimestamp || 0),
      text });
    if (result.action === "ignored") console.error(`WhatsApp self-chat gate: ${result.reason}`);
    if (result.action === "remembered") console.log(JSON.stringify({ type: "memory_ack", text: result.text }));
    if (result.action === "proposed") console.log(JSON.stringify({ type: "dry_run_proposal", text: result.text }));
    if (result.action === "sent") console.error("One designated self-chat reply sent; send limit reached.");
    if (result.action === "failed") console.error(`Bridge failed without retry/send: ${result.reason}`);
  }
  });
} catch (error) {
  console.error(`WhatsApp startup blocked: ${String(error.message || error).replace(/\b\d{8,}\b/g, "<redacted>")}`);
  process.exit(1);
}
