#!/usr/bin/env node
import process from "node:process";
import { DEFAULT_MEMORY_PATH, inspect, remember, rollback, supersede } from "./memory.js";
const [command, ...args] = process.argv.slice(2);
const file = process.env.CAPTAIN_MEMORY_PATH || DEFAULT_MEMORY_PATH;
try {
  if (command === "inspect") console.log(JSON.stringify(await inspect(file, args[0] || null), null, 2));
  else if (command === "remember") console.log(JSON.stringify(await remember(file, { scope: args[0], content: args.slice(1).join(" "), source: "Cameron self-chat command" }), null, 2));
  else if (command === "rollback") console.log(JSON.stringify(await rollback(file, args[0]), null, 2));
  else if (command === "correct") console.log(JSON.stringify(await supersede(file, args[0], { content: args.slice(1).join(" "), source: "Cameron explicit correction" }), null, 2));
  else { console.error("usage: inspect [scope] | remember <shared|cameron-private> <text> | correct <id> <text> | rollback <id>"); process.exitCode = 2; }
} catch (error) { console.error(error.message); process.exitCode = 1; }
