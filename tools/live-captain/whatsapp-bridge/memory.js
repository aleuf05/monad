import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";

export const DEFAULT_MEMORY_PATH = path.resolve(new URL(".", import.meta.url).pathname, "memory-state.json");
const MAX_RECORDS = 200;
const MAX_CONTENT = 1200;

async function readState(file) {
  try {
    const data = JSON.parse(await fs.readFile(file, "utf8"));
    if (!data || !Array.isArray(data.records)) throw new Error("invalid memory shape");
    return data;
  } catch (error) {
    if (error.code === "ENOENT") return { version: 1, records: [] };
    throw new Error(`memory unavailable: ${error.message}`);
  }
}

async function writeState(file, state) {
  await fs.mkdir(path.dirname(file), { recursive: true, mode: 0o700 });
  const temp = `${file}.tmp-${process.pid}-${crypto.randomUUID()}`;
  await fs.writeFile(temp, JSON.stringify(state, null, 2) + "\n", { mode: 0o600 });
  await fs.rename(temp, file);
}

export async function remember(file, { scope, content, source, verification = "user-provided", uncertainty = "not independently verified" }) {
  if (!["shared", "cameron-private", "mike-private"].includes(scope)) throw new Error("invalid memory scope");
  const text = String(content || "").trim();
  if (!text || text.length > MAX_CONTENT) throw new Error("memory content is empty or too large");
  const state = await readState(file);
  const record = { id: `mem-${Date.now()}-${crypto.randomBytes(4).toString("hex")}`, scope, content: text, source, verification, uncertainty, status: "active", createdAt: new Date().toISOString(), supersedes: null };
  state.records.push(record);
  state.records = state.records.slice(-MAX_RECORDS);
  await writeState(file, state);
  return record;
}

export async function supersede(file, id, replacement) {
  const state = await readState(file);
  const prior = state.records.find(r => r.id === id && r.status === "active");
  if (!prior) throw new Error("active memory record not found");
  prior.status = "superseded";
  await writeState(file, state);
  const next = await remember(file, { ...replacement, scope: prior.scope, source: replacement.source || "explicit correction", uncertainty: replacement.uncertainty || "not independently verified" });
  const updated = await readState(file);
  const created = updated.records.find(r => r.id === next.id);
  created.supersedes = id;
  await writeState(file, updated);
  return created;
}

export async function rollback(file, id) {
  const state = await readState(file);
  const record = state.records.find(r => r.id === id && r.status === "active");
  if (!record) throw new Error("active memory record not found");
  record.status = "rolled_back";
  await writeState(file, state);
  return record;
}

export async function inspect(file, scope = null) {
  const state = await readState(file);
  return state.records.filter(r => !scope || r.scope === scope);
}

export async function contextFor(file, recipientScope = "cameron-private") {
  const records = await inspect(file);
  return records.filter(r => r.status === "active" && (r.scope === "shared" || r.scope === recipientScope))
    .slice(-40).map(r => `- [${r.scope}; ${r.verification}; ${r.uncertainty}; ${r.id}] ${r.content}`).join("\n") || "(no applicable durable Captain memory)";
}

export function parseTeaching(text) {
  const shared = text.match(/^Remember for everyone:\s*(.+)$/is);
  if (shared) return { scope: "shared", content: shared[1].trim() };
  const own = text.match(/^Remember privately:\s*(.+)$/is);
  if (own) return { scope: "cameron-private", content: own[1].trim() };
  return null;
}

export function parseCorrection(text) {
  const match = text.match(/^Correct memory\s+(mem-[^\s:]+):\s*(.+)$/is);
  return match ? { id: match[1], content: match[2].trim() } : null;
}
