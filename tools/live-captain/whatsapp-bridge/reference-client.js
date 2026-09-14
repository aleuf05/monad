#!/usr/bin/env node

// Minimal Baileys reference diagnostic. It deliberately has no message
// handler and no send capability. It uses the package's default protocol,
// browser, presence, and history settings; only auth persistence, QR output,
// silent logging, and one bounded post-pair-success restart are added.
import process from "node:process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const args = process.argv.slice(2);
if (!process.stdout.isTTY || !process.stdin.isTTY) throw new Error("reference diagnostic requires an attended TTY");
if (args.includes("--fresh")) throw new Error("refusing --fresh: choose a new --auth-dir without deleting existing state");
const supplied = args.indexOf("--auth-dir");
const authDir = supplied >= 0 ? args[supplied + 1] : path.resolve(path.dirname(fileURLToPath(import.meta.url)), "reference-auth-state");
if (!authDir) throw new Error("--auth-dir requires a path");

const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = await import("@whiskeysockets/baileys");
const { default: qrcode } = await import("qrcode-terminal");
const { default: pino } = await import("pino");
const fs = await import("node:fs/promises");
await fs.mkdir(authDir, { recursive: true, mode: 0o700 });
await fs.chmod(authDir, 0o700);
const { state, saveCreds } = await useMultiFileAuthState(authDir);
for (const entry of await fs.readdir(authDir, { withFileTypes: true })) if (entry.isFile()) await fs.chmod(path.join(authDir, entry.name), 0o600);

let restartCount = 0;
let stopped = false;
let pendingWrites = new Set();
let sock;
const persist = () => {
  const write = Promise.resolve(saveCreds());
  pendingWrites.add(write);
  void write.finally(() => pendingWrites.delete(write));
};
const status = code => Number.isInteger(code) ? `status ${code}` : "unknown status";

async function start() {
  sock = makeWASocket({ auth: state, logger: pino({ level: "silent" }), printQRInTerminal: false });
  sock.ev.on("creds.update", persist);
  sock.ev.on("connection.update", async ({ connection, qr, isNewLogin, lastDisconnect }) => {
    if (qr) qrcode.generate(qr, { small: true });
    if (connection === "open") console.error("REFERENCE: connected; no message handlers are installed.");
    if (isNewLogin && restartCount === 0) {
      restartCount += 1;
      await Promise.allSettled([...pendingWrites]);
      console.error("REFERENCE: pair-success persisted; performing one required bounded restart.");
      sock.end(undefined);
      await new Promise(resolve => setTimeout(resolve, 100));
      if (!stopped) await start();
    }
    if (connection === "close" && !stopped && restartCount <= 1) {
      console.error(`REFERENCE: disconnected (${status(lastDisconnect?.error?.output?.statusCode)}). No automatic reconnect.`);
      if (restartCount === 1) process.exitCode = 1;
    }
  });
}
const stop = async () => { stopped = true; await Promise.allSettled([...pendingWrites]); sock?.end(undefined); };
process.once("SIGINT", stop);
process.once("SIGTERM", stop);
await start();
