#!/usr/bin/env node
import process from "node:process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SelfChatBridge, createPairedClient, authenticatedSelfJid, invokeCodexViaVerifiedAdapter } from "./bridge.js";

const args = new Set(process.argv.slice(2));
const pair = args.has("--pair");
const sendOnce = args.has("--send-once");
const fresh = args.has("--fresh");
if (!pair && !sendOnce) { console.error("Refusing to start: choose --pair or --send-once explicitly."); process.exit(2); }
if (fresh && !pair) { console.error("--fresh requires --pair and never deletes an existing auth directory."); process.exit(2); }
if (process.env.WHATSAPP_PAIR_PHONE) { console.error("Phone-code pairing is disabled for this Baileys version; use fresh QR pairing with --fresh --pair."); process.exit(2); }
const defaultAuth = path.resolve(path.dirname(fileURLToPath(import.meta.url)), fresh ? "auth-state-fresh" : "auth-state");
const authDir = process.env.WHATSAPP_AUTH_DIR || defaultAuth;
const startedAt = Date.now();
let bridge, client, stopped = false;
const stop = async () => { if (stopped) return; stopped = true; await client?.stop(); process.exit(0); };
process.once("SIGINT", stop); process.once("SIGTERM", stop);

try { client = await createPairedClient({
  authDir,
  phoneNumber: undefined,
  onMessage: async (message, sock) => {
    const ownJid = authenticatedSelfJid(sock);
    if (!ownJid) return;
    if (!bridge) {
      bridge = new SelfChatBridge({ ownJid, startedAt, dryRun: !sendOnce, maxSends: sendOnce ? 1 : 0,
        invokeCodex: context => invokeCodexViaVerifiedAdapter(context),
        send: async payload => sock.sendMessage(payload.remoteJid, { text: payload.text }) });
      console.error("Authenticated WhatsApp self-chat identity verified (identifier withheld).");
    }
    const result = await bridge.handleMessage({ id: message.key.id, remoteJid: message.key.remoteJid,
      fromMe: Boolean(message.key.fromMe), timestamp: Number(message.messageTimestamp || 0),
      text: message.message?.conversation || message.message?.extendedTextMessage?.text || "" });
    if (result.action === "proposed") console.log(JSON.stringify({ type: "dry_run_proposal", text: result.text }));
    if (result.action === "sent") console.error("One designated self-chat reply sent; send limit reached.");
    if (result.action === "failed") console.error(`Bridge failed without retry/send: ${result.reason}`);
  }
  });
} catch (error) {
  console.error(`WhatsApp startup blocked: ${String(error.message || error).replace(/\b\d{8,}\b/g, "<redacted>")}`);
  process.exit(1);
}
