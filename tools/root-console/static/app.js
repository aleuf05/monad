const loginGate = document.getElementById("login-gate");
const loginForm = document.getElementById("login-form");
const loginPassword = document.getElementById("login-password");
const loginError = document.getElementById("login-error");

const terminalEl = document.getElementById("terminal");
const promptRowEl = document.getElementById("prompt-row");
const connEl = document.getElementById("conn");
const connTextEl = document.getElementById("conn-text");
const input = document.getElementById("input");

const telPid = document.getElementById("tel-pid");
const telUptime = document.getElementById("tel-uptime");
const telThread = document.getElementById("tel-thread");
const telTokens = document.getElementById("tel-tokens");
const telRatelimit = document.getElementById("tel-ratelimit");
const telSubs = document.getElementById("tel-subs");
const commissionLive = document.getElementById("commission-live");
const commissionCodex = document.getElementById("commission-codex");
const commissionTarget = document.getElementById("commission-target");
const commissionHandoff = document.getElementById("commission-handoff");
const commissionAuthority = document.getElementById("commission-authority");
const commissionMission = document.getElementById("commission-mission");

let authenticated = false;
let statusPollHandle = null;
let streamSource = null;

function timestamp() {
  return new Date().toTimeString().slice(0, 8);
}

function flashTile(valueEl) {
  const tile = valueEl.closest(".tile");
  tile.classList.remove("flash");
  void tile.offsetWidth;
  tile.classList.add("flash");
}

function setTelemetry(el, value) {
  if (el.textContent === String(value)) return;
  el.textContent = value;
  flashTile(el);
}

function fmtUptime(seconds) {
  const s = Math.floor(seconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return `${h}h${m}m${sec}s`;
}

function shortThread(threadId) {
  return threadId ? threadId.slice(0, 8) : "—";
}

// Every row is inserted directly before the permanent prompt line, so the
// prompt always stays the last line of one continuous scrollback.
function addRow(cssClass, src, body) {
  const row = document.createElement("div");
  row.className = `row ${cssClass}`;
  const ts = document.createElement("span");
  ts.className = "ts";
  ts.textContent = timestamp();
  const srcEl = document.createElement("span");
  srcEl.className = "src";
  srcEl.textContent = src;
  const bodyEl = document.createElement("span");
  bodyEl.className = "body";
  bodyEl.textContent = body;
  row.append(ts, srcEl, bodyEl);
  terminalEl.insertBefore(row, promptRowEl);
  terminalEl.scrollTop = terminalEl.scrollHeight;
  return bodyEl;
}

const SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
let thinkingBodyEl = null;
let thinkingInterval = null;

function startThinking() {
  if (thinkingBodyEl) return;
  thinkingBodyEl = addRow("thinking", "captain", SPINNER_FRAMES[0]);
  let frame = 0;
  thinkingInterval = setInterval(() => {
    frame = (frame + 1) % SPINNER_FRAMES.length;
    thinkingBodyEl.textContent = SPINNER_FRAMES[frame];
  }, 80);
}

function stopThinking() {
  if (thinkingInterval) {
    clearInterval(thinkingInterval);
    thinkingInterval = null;
  }
  if (thinkingBodyEl) {
    thinkingBodyEl.closest(".row")?.remove();
    thinkingBodyEl = null;
  }
}

async function pollStatus() {
  try {
    const response = await fetch("/api/status");
    if (response.status === 401) {
      showLoginGate();
      return;
    }
    if (!authenticated) onAuthenticated();
    const status = await response.json();
    telPid.textContent = status.pid;
    telUptime.textContent = fmtUptime(status.uptime_seconds);
    setTelemetry(telThread, shortThread(status.active_thread_id));
    setTelemetry(telSubs, status.subscriber_count);
    const commissioning = status.commissioning || {};
    commissionLive.textContent = commissioning.liveCaptain || "UNKNOWN";
    commissionCodex.textContent = commissioning.codexEmbodiment || "UNKNOWN";
    commissionTarget.textContent = commissioning.rootConsoleTarget || "UNKNOWN";
    commissionHandoff.textContent = commissioning.handoffChannel || "UNKNOWN";
    commissionAuthority.textContent = commissioning.authorityMode || "UNKNOWN";
    commissionMission.textContent = commissioning.currentMission || "UNKNOWN";
  } catch (err) {
    // status endpoint unreachable; telemetry goes stale, connection indicator still reflects reality
  }
}

function showLoginGate() {
  authenticated = false;
  loginGate.classList.remove("hidden");
  if (streamSource) {
    streamSource.close();
    streamSource = null;
  }
  if (statusPollHandle) {
    clearInterval(statusPollHandle);
    statusPollHandle = null;
  }
}

function onAuthenticated() {
  if (authenticated) return;
  authenticated = true;
  loginGate.classList.add("hidden");
  loginError.textContent = "";
  connect();
  if (!statusPollHandle) statusPollHandle = setInterval(pollStatus, 4000);
  input.focus();
}

loginForm.addEventListener("submit", async (submitEvent) => {
  submitEvent.preventDefault();
  const password = loginPassword.value;
  loginPassword.value = "";
  try {
    const response = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      loginError.textContent = body.error || `HTTP ${response.status}`;
      return;
    }
    onAuthenticated();
  } catch (err) {
    loginError.textContent = String(err);
  }
});

function summarizeItem(item) {
  if (item.type === "agentMessage") return item.text || "";
  if (item.type === "userMessage") {
    return (item.content || []).map((c) => c.text || "").join(" ");
  }
  if (item.type === "reasoning") return item.text || item.summary || "(reasoning)";
  if (item.type === "commandExecution" || item.type === "command") {
    return item.command || item.text || "(command)";
  }
  const stringField = Object.entries(item).find(
    ([key, value]) => typeof value === "string" && value && key !== "type" && key !== "id"
  );
  return stringField ? stringField[1] : "";
}

function rowClassForItemType(type) {
  if (type === "agentMessage") return "agent";
  if (type === "userMessage") return "injected";
  return "tool";
}

const streamingRows = new Map(); // itemId -> body element being streamed into

function handleCodexEvent(event) {
  const method = event.method;
  const params = event.params || {};

  if (method === "item/agentMessage/delta") {
    let bodyEl = streamingRows.get(params.itemId);
    if (!bodyEl) {
      stopThinking();
      bodyEl = addRow("agent", "captain", "");
      streamingRows.set(params.itemId, bodyEl);
    }
    bodyEl.textContent += params.delta || "";
    terminalEl.scrollTop = terminalEl.scrollHeight;
    return;
  }

  if (method === "item/completed") {
    const item = params.item || {};
    if (item.type === "agentMessage") {
      stopThinking();
      let bodyEl = streamingRows.get(item.id);
      if (!bodyEl) bodyEl = addRow("agent", "captain", "");
      bodyEl.textContent = item.text || "";
      streamingRows.delete(item.id);
      terminalEl.scrollTop = terminalEl.scrollHeight;
      return;
    }
    if (item.type === "userMessage") return;
    addRow(rowClassForItemType(item.type), item.type || "item", summarizeItem(item) || "(completed)");
    return;
  }

  if (method === "item/started") {
    // The spinner already communicates liveness. Wait for completed items so
    // the scrollback records useful work instead of every protocol transition.
    return;
  }

  if (method === "turn/started") {
    return;
  }
  if (method === "turn/completed") {
    stopThinking();
    return;
  }
  if (method === "thread/status/changed") {
    return;
  }
  if (method === "thread/tokenUsage/updated") {
    const total = (params.tokenUsage || {}).total || {};
    setTelemetry(telTokens, `${total.inputTokens ?? 0} in / ${total.outputTokens ?? 0} out`);
    return;
  }
  if (method === "account/rateLimits/updated") {
    const primary = (params.rateLimits || {}).primary || {};
    setTelemetry(telRatelimit, primary.usedPercent != null ? `${primary.usedPercent}%` : "—");
    return;
  }
  if (method === "mcpServer/startupStatus/updated") {
    return;
  }
  if (method === "thread/started") return;
}

function handleEvent(event) {
  if (event.type === "captain_handoff_available") {
    addRow("tool", "handoff", `${event.taskId}: ${event.publicationState}`);
    return;
  }
  if (event.type === "turn_started") {
    addRow("injected", "you", event.text);
    return;
  }
  if (event.type === "codex_event") {
    handleCodexEvent(event);
    return;
  }
}

function connect() {
  if (streamSource) return;
  streamSource = new EventSource("/api/stream");
  streamSource.onopen = () => {
    connEl.classList.add("live");
    connTextEl.textContent = "live";
  };
  streamSource.onerror = () => {
    connEl.classList.remove("live");
    connTextEl.textContent = "reconnecting…";
  };
  streamSource.onmessage = (raw) => {
    try {
      handleEvent(JSON.parse(raw.data));
    } catch (err) {
      console.error("bad event", err, raw.data);
    }
  };
}

async function submitDirective() {
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  startThinking();
  try {
    const response = await fetch("/api/turn", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!response.ok) {
      stopThinking();
      const body = await response.json().catch(() => ({}));
      addRow("error", "error", body.error || `HTTP ${response.status}`);
    }
  } catch (err) {
    stopThinking();
    addRow("error", "error", String(err));
  }
  input.focus();
}

input.addEventListener("keydown", (keyEvent) => {
  if (keyEvent.key === "Enter") {
    keyEvent.preventDefault();
    submitDirective();
  }
});

terminalEl.addEventListener("click", () => input.focus());

pollStatus();
