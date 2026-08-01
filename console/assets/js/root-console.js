// Root Console frontend, served live at cameronlampley.com/root.
// Talks to the root-console daemon (tools/root-console/server.py, port
// 4792) through Caddy's /root-console-api/* reverse proxy -- there is no
// separate dev deployment, this file IS the live page.
const API_BASE = "/root-console-api/api";

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
const fleetEl = document.getElementById("fleet");
const imageStage = document.getElementById("image-stage");
const imageStageImage = document.getElementById("image-stage-image");
const imageStageTitle = document.getElementById("image-stage-title");
const imageStageOpen = document.getElementById("image-stage-open");
const imageStageClose = document.getElementById("image-stage-close");
const imageStageCanvas = document.getElementById("image-stage-canvas");

const activityToggle = document.getElementById("activity-toggle");
const activityLog = document.getElementById("activity-log");

const handoffsList = document.getElementById("handoffs-list");
const handoffsRefresh = document.getElementById("handoffs-refresh");
const handoffDetail = document.getElementById("handoff-detail");
const handoffDetailTitle = document.getElementById("handoff-detail-title");
const handoffDetailBody = document.getElementById("handoff-detail-body");
const handoffDetailClose = document.getElementById("handoff-detail-close");
const dispatchViewLatest = document.getElementById("dispatch-view-latest");
let latestHandoffFile = null;
const activityLights = {};
for (const el of document.querySelectorAll(".status-widget")) {
  activityLights[el.dataset.cat] = { el, count: 0, timer: null };
}

let authenticated = false;
let statusPollHandle = null;
let fleetPollHandle = null;
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

function openImageStage(url, label) {
  imageStageImage.src = url;
  imageStageImage.alt = label || "Captain image artifact";
  imageStageImage.classList.remove("actual");
  imageStageTitle.textContent = label || "Captain image artifact";
  imageStageOpen.href = url;
  imageStage.hidden = false;
  document.body.style.overflow = "hidden";
  imageStageClose.focus();
}

function closeImageStage() {
  if (imageStage.hidden) return;
  imageStage.classList.add("closing");
  window.setTimeout(() => {
    imageStage.hidden = true;
    imageStage.classList.remove("closing");
    imageStageImage.src = "";
    document.body.style.overflow = "";
    input.focus();
  }, 180);
}

function addImageArtifact(url, label = "Captain image artifact") {
  const bodyEl = addRow("agent image-artifact", "captain", "");
  const button = document.createElement("button");
  button.type = "button";
  button.className = "image-preview";
  button.setAttribute("aria-label", `Open image preview: ${label}`);
  const image = document.createElement("img");
  image.src = url;
  image.alt = label;
  image.loading = "lazy";
  const badge = document.createElement("span");
  badge.className = "artifact-label";
  badge.textContent = "CAPTAIN · IMAGE";
  button.append(image, badge);
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    openImageStage(url, label);
  });
  bodyEl.appendChild(button);
  return bodyEl;
}

function imageArtifactsFrom(value, opts = {}, found = new Map(), depth = 0) {
  // scanFreeText: only true for the Captain's actual agentMessage prose.
  // Tool/reasoning/command items get structured-field detection only
  // (an explicit image_url/src key) -- this repo is full of incidental
  // image file paths in command output and reasoning text (web/toys,
  // GLB intake, image-gen tooling), and a loose extension regex over
  // every completed item's every string field was matching those and
  // flooding the dialogue with false-positive preview cards. Bare local
  // filesystem paths are dropped entirely -- they aren't browser-fetchable
  // anyway, so matching them can only ever produce a broken image, never
  // a real preview.
  const { scanFreeText = true } = opts;
  if (depth > 5 || value == null) return found;
  if (typeof value === "string") {
    if (scanFreeText) {
      const markdownImages = value.matchAll(/!\[([^\]]*)\]\(([^\s)]+)(?:\s+["'][^"']*["'])?\)/g);
      for (const match of markdownImages) found.set(match[2], match[1] || "Captain image artifact");
      const imageUrls = value.match(/https?:\/\/[^\s<>'"()]+\.(?:avif|gif|jpe?g|png|webp)(?:\?[^\s<>'"()]*)?/gi) || [];
      for (const url of imageUrls) if (!found.has(url)) found.set(url, "Captain image artifact");
      if (value.startsWith("data:image/")) found.set(value, "Captain image artifact");
    }
    return found;
  }
  if (Array.isArray(value)) {
    for (const entry of value) imageArtifactsFrom(entry, opts, found, depth + 1);
    return found;
  }
  if (typeof value === "object") {
    const label = value.output_hint || value.prompt || value.alt || value.title;
    for (const [key, entry] of Object.entries(value)) {
      if (typeof entry === "string" && /^(image_url|imageUrl|url|src|data)$/.test(key) && /^(?:data:image\/|https?:\/\/)/.test(entry)) {
        found.set(entry, typeof label === "string" ? label : "Captain image artifact");
      } else {
        imageArtifactsFrom(entry, opts, found, depth + 1);
      }
    }
  }
  return found;
}

imageStageClose.addEventListener("click", closeImageStage);
imageStage.addEventListener("click", (event) => {
  if (event.target === imageStage || event.target === imageStageCanvas) closeImageStage();
});
imageStageImage.addEventListener("click", () => imageStageImage.classList.toggle("actual"));
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !imageStage.hidden) closeImageStage();
  if (event.key === "Escape" && !handoffDetail.hidden) closeHandoffDetail();
});

function closeHandoffDetail() {
  handoffDetail.hidden = true;
  handoffDetailBody.textContent = "";
}

async function openHandoffDetail(file) {
  handoffDetailTitle.textContent = file;
  handoffDetailBody.textContent = "loading…";
  handoffDetail.hidden = false;
  handoffDetailClose.focus();
  try {
    const response = await fetch(`${API_BASE}/handoffs/detail?file=${encodeURIComponent(file)}`);
    const body = await response.json();
    handoffDetailBody.textContent = response.ok ? body.content : (body.error || `HTTP ${response.status}`);
  } catch (err) {
    handoffDetailBody.textContent = String(err);
  }
}

handoffDetailClose.addEventListener("click", closeHandoffDetail);
handoffDetail.addEventListener("click", (event) => {
  if (event.target === handoffDetail) closeHandoffDetail();
});

function fmtHandoffTimestamp(ts) {
  // ts is YYYYMMDDTHHMMSSZ
  const match = /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$/.exec(ts || "");
  if (!match) return ts || "—";
  const [, y, mo, d, h, mi, s] = match;
  return `${y}-${mo}-${d} ${h}:${mi}:${s}Z`;
}

function renderHandoffs(items) {
  handoffsList.innerHTML = "";
  latestHandoffFile = items.length ? items[0].file : null;
  dispatchViewLatest.disabled = !latestHandoffFile;
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "h-empty";
    empty.textContent = "No handoffs yet.";
    handoffsList.appendChild(empty);
    return;
  }
  for (const item of items) {
    const row = document.createElement("div");
    row.className = "h-row";
    row.tabIndex = 0;

    const head = document.createElement("div");
    head.className = "h-head";
    const task = document.createElement("span");
    task.className = "h-task";
    task.textContent = `${item.agent} · ${item.taskId}`;
    const badge = document.createElement("span");
    badge.className = `h-badge${item.publicationState === "PUBLISHED" ? " published" : ""}`;
    badge.textContent = item.publicationState === "PUBLISHED" ? "published" : "local-only";
    head.appendChild(task);
    head.appendChild(badge);

    const meta = document.createElement("div");
    meta.className = "h-meta";
    meta.textContent = `${fmtHandoffTimestamp(item.timestamp)} · ${item.branch || "—"}`;

    const path = document.createElement("div");
    path.className = "h-path";
    path.textContent = item.path;

    row.appendChild(head);
    row.appendChild(meta);
    row.appendChild(path);
    row.addEventListener("click", () => openHandoffDetail(item.file));
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter") openHandoffDetail(item.file);
    });
    handoffsList.appendChild(row);
  }
}

async function pollHandoffs() {
  try {
    const response = await fetch(`${API_BASE}/handoffs`);
    if (response.status === 401) return; // pollStatus's own 401 handling covers the gate
    const body = await response.json();
    renderHandoffs(body.handoffs || []);
  } catch (err) {
    // handoffs endpoint unreachable; list just goes stale
  }
}

handoffsRefresh.addEventListener("click", pollHandoffs);
dispatchViewLatest.addEventListener("click", () => {
  if (latestHandoffFile) openHandoffDetail(latestHandoffFile);
});

let activityLogOpen = false;
let activityEntryCount = 0;
const ACTIVITY_LOG_CAP = 60;

function pulseLight(cat, summary) {
  const light = activityLights[cat];
  if (!light) return;
  light.count += 1;
  light.el.querySelector(".count").textContent = light.count;
  light.el.querySelector(".caption").textContent = summary || "";
  light.el.classList.add("pulse");
  clearTimeout(light.timer);
  // Long enough to actually read the caption, short enough to stay "blinky"
  // rather than becoming another wall of standing text.
  light.timer = setTimeout(() => light.el.classList.remove("pulse"), 2400);
}

function recordActivity(cat, label, summary) {
  pulseLight(cat, summary);
  if (activityEntryCount === 0) activityLog.innerHTML = "";
  const row = document.createElement("div");
  row.className = "a-row";
  row.innerHTML = `<span class="ts">${timestamp()}</span><span class="cat">${label}</span><span class="sum"></span>`;
  row.querySelector(".sum").textContent = summary;
  activityLog.insertBefore(row, activityLog.firstChild);
  activityEntryCount += 1;
  while (activityLog.children.length > ACTIVITY_LOG_CAP) {
    activityLog.removeChild(activityLog.lastChild);
  }
}

activityToggle.addEventListener("click", () => {
  activityLogOpen = !activityLogOpen;
  activityLog.classList.toggle("open", activityLogOpen);
  activityToggle.textContent = activityLogOpen ? "activity log ▴" : "activity log ▾";
});

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
    const response = await fetch(`${API_BASE}/status`);
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
  } catch (err) {
    // status endpoint unreachable; telemetry goes stale, connection indicator still reflects reality
  }
}

async function pollFleet() {
  try {
    const response = await fetch(`${API_BASE}/fleet`);
    if (response.status === 401) return; // pollStatus's own 401 handling covers the gate
    const body = await response.json();
    fleetEl.innerHTML = "";
    for (const item of body.fleet || []) {
      const el = document.createElement("span");
      el.className = `fleet-item ${item.state === "active" ? "active" : "down"}`;
      el.title = item.unit;
      const dot = document.createElement("span");
      dot.className = "dot";
      el.appendChild(dot);
      el.appendChild(document.createTextNode(item.name));
      fleetEl.appendChild(el);
    }
  } catch (err) {
    // fleet endpoint unreachable; strip just goes stale
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
  if (fleetPollHandle) {
    clearInterval(fleetPollHandle);
    fleetPollHandle = null;
  }
}

function onAuthenticated() {
  if (authenticated) return;
  authenticated = true;
  loginGate.classList.add("hidden");
  loginError.textContent = "";
  connect();
  if (!statusPollHandle) statusPollHandle = setInterval(pollStatus, 4000);
  if (!fleetPollHandle) {
    pollFleet();
    fleetPollHandle = setInterval(pollFleet, 10000);
  }
  pollHandoffs();
  input.focus();
}

loginForm.addEventListener("submit", async (submitEvent) => {
  submitEvent.preventDefault();
  const password = loginPassword.value;
  loginPassword.value = "";
  try {
    const response = await fetch(`${API_BASE}/login`, {
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

function categoryForItemType(type) {
  return type === "reasoning" ? "reasoning" : "tool";
}

const streamingRows = new Map();

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
      for (const [url, label] of imageArtifactsFrom(item, { scanFreeText: true })) addImageArtifact(url, label);
      terminalEl.scrollTop = terminalEl.scrollHeight;
      return;
    }
    if (item.type === "userMessage") return;
    const artifacts = imageArtifactsFrom(item, { scanFreeText: false });
    if (artifacts.size) {
      stopThinking();
      for (const [url, label] of artifacts) addImageArtifact(url, label);
      return;
    }
    recordActivity(categoryForItemType(item.type), item.type || "item", summarizeItem(item) || "(completed)");
    return;
  }

  if (method === "item/started") {
    // The spinner already communicates liveness, and the completed event
    // for this same item lands moments later with an actual summary --
    // logging both would double every tool call in the activity log.
    return;
  }

  if (method === "turn/started") {
    recordActivity("thread", "turn", "started");
    return;
  }
  if (method === "turn/completed") {
    stopThinking();
    const status = (params.turn || {}).status || "completed";
    recordActivity("thread", "turn", `completed (${status})`);
    return;
  }
  if (method === "thread/status/changed") {
    recordActivity("thread", "thread", (params.status || {}).type || "status changed");
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
    recordActivity("mcp", `mcp:${params.name}`, params.status || "");
    return;
  }
  if (method === "thread/started") return;

  // Unknown/future protocol methods -- log them rather than silently
  // dropping (which is how noise-suppression regressed once already),
  // but keep them out of chat.
  recordActivity("thread", method, JSON.stringify(params));
}

function handleEvent(event) {
  if (event.type === "turn_started") {
    addRow("injected", "you", event.text);
    return;
  }
  if (event.type === "codex_event") {
    handleCodexEvent(event);
    return;
  }
  if (event.type === "captain_handoff_available") {
    pollHandoffs();
    return;
  }
}

function connect() {
  if (streamSource) return;
  streamSource = new EventSource(`${API_BASE}/stream`);
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
    const response = await fetch(`${API_BASE}/turn`, {
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
