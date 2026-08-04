// Root Console frontend, served live at cameronlampley.com/root.
// Talks to the root-console daemon (tools/root-console/server.py, port
// 4792) through Caddy's /root-console-api/* reverse proxy -- there is no
// separate dev deployment, this file IS the live page.
const API_BASE = "/root-console-api/api";
// The conversation surface itself (turn/stream only) is served by the
// separate Live Captain minimum-context bootstrap
// (tools/live-captain/server.py, port 4778) -- see
// LIVE-CAPTAIN-MINIMUM-CONTEXT-BOOTSTRAP-0.1. Login, status, and handoffs
// stay on root-console.service above; only the actual Captain
// conversation moved.
//
// NON-OBVIOUS AND COSTLY IF MISSED: these two services are not
// independent. live-captain-bootstrap imports the SAME
// tools/root-console/generated_images.py module root-console.service uses,
// and every image URL it mints still points back at
// root-console.service's /api/generated-image/ route -- root-console is
// the ONLY service that ever serves the actual image bytes, even for a
// conversation running entirely on live-captain-bootstrap. Restarting only
// one of the two, or checking only one of the two before declaring
// something broken/fixed, WILL produce misleading results. Always check
// and restart both together.
const LIVE_CAPTAIN_API_BASE = "/live-captain-bootstrap-api/api";

const bearingIndicatorEl = document.getElementById("bearing-indicator");
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
const shipLogList = document.getElementById("ship-log-list");
const shipLogRefresh = document.getElementById("ship-log-refresh");
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

// An image card that just rendered was getting shoved out of the visible
// terminal within a second by the next chat row's own auto-scroll-to-
// bottom -- still in the DOM, just immediately unseeable. Pin the view in
// place for a few seconds after an image lands instead of always
// snapping to the newest row.
let imagePinnedUntil = 0;

function followTerminalBottom() {
  if (Date.now() < imagePinnedUntil) return;
  terminalEl.scrollTop = terminalEl.scrollHeight;
}

// Deterministic per-message "living glyph" -- same 5x5 symmetric block
// identicon already shipped in the Document Viewer (console/documents.html),
// ported here so every Captain row carries its own hashed visual signature
// instead of only the bare word "captain". Hashed from the row's own text,
// not stored anywhere -- matches this console's live-off-disk rule.
function hashString(s) {
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

function identiconSvg(seed, size) {
  const h = hashString(seed);
  const hue = h % 360;
  const color = `hsl(${hue}, 62%, 58%)`;
  const cols = 3, rows = 5, cell = size / rows;
  const cells = [];
  let bit = 0;
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < cols; x++) {
      bit++;
      if (((h >> bit) & 1) !== 1) continue;
      cells.push([x, y]);
      if (x < cols - 1) cells.push([2 * cols - 2 - x, y]);
    }
  }
  const rects = cells.map(([x, y]) => `<rect x="${x * cell}" y="${y * cell}" width="${cell}" height="${cell}" fill="${color}"/>`).join("");
  return `<svg class="glyph" width="${size}" height="${size}" viewBox="0 0 ${cell * 5} ${cell * rows}" style="border-radius:2px;background:rgba(255,255,255,0.06);flex:none;">${rects}</svg>`;
}

function addRow(cssClass, src, body) {
  const row = document.createElement("div");
  row.className = `row ${cssClass}`;
  const ts = document.createElement("span");
  ts.className = "ts";
  ts.textContent = timestamp();
  const srcEl = document.createElement("span");
  srcEl.className = "src";
  if (src === "captain") srcEl.innerHTML = identiconSvg(body || cssClass + ts.textContent, 13);
  srcEl.append(document.createTextNode(src));
  const bodyEl = document.createElement("span");
  bodyEl.className = "body";
  bodyEl.textContent = body;
  row.append(ts, srcEl, bodyEl);
  terminalEl.insertBefore(row, promptRowEl);
  followTerminalBottom();
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
  imagePinnedUntil = Date.now() + 5000;
  bodyEl.closest(".row")?.scrollIntoView({ block: "center", behavior: "smooth" });
  return bodyEl;
}

// Live wiring for the Semantic Text Metamorphosis capability
// (console/assets/js/semantic-metamorphosis.js, capability card
// semantic-metamorphosis.capability.json): captain-kernel.md documents this
// trigger syntax so the Captain itself can compose a real, physics-driven
// choreography from plain conversational text -- not a single fixed
// preset. The tag is stripped from the displayed message; phrases named in
// it must already appear verbatim elsewhere in the same message (the
// component locates and lifts real rendered text, it doesn't fabricate the
// source words).
//
// General form: ⟦fx: phrases="a, b, c" | op1(args) | op2(args) | ...⟧
// Legacy form (kept working): ⟦metamorphose: phrases="a, b, c" => "result"⟧
const FX_TRIGGER = /⟦fx:\s*([^⟧]+)⟧\s*/i;
const LEGACY_METAMORPHOSIS_TRIGGER = /⟦metamorphose:\s*phrases="([^"]+)"\s*=>\s*"([^"]+)"⟧\s*/i;

const FX_POSITIONAL_KEY = { orbit: "turns", scatter: "radius", shed: "fraction", morph: "to", merge: "into", pulse: "strength", crystallize: "glyph", trail: "on" };

function parseFxStepArgs(argsStr) {
  const args = {};
  const parts = (argsStr.match(/(?:[^,"]+|"[^"]*")+/g) || []).map((s) => s.trim()).filter(Boolean);
  parts.forEach((part, i) => {
    const kv = /^([a-zA-Z_]+)\s*=\s*(.+)$/.exec(part);
    let key, raw;
    if (kv) { key = kv[1]; raw = kv[2].trim(); } else { key = `_pos${i}`; raw = part; }
    let val;
    if (/^".*"$/.test(raw)) val = raw.slice(1, -1);
    else if (raw !== "" && !isNaN(Number(raw))) val = Number(raw);
    else val = raw;
    args[key] = val;
  });
  return args;
}

function remapFxPositional(op, args) {
  const posKey = FX_POSITIONAL_KEY[op];
  if (posKey && args._pos0 !== undefined && args[posKey] === undefined) args[posKey] = args._pos0;
  Object.keys(args).forEach((k) => { if (k.startsWith("_pos")) delete args[k]; });
  return args;
}

function parseFxTrigger(text) {
  const m = FX_TRIGGER.exec(text);
  if (!m) return null;
  const segments = m[1].split("|").map((s) => s.trim()).filter(Boolean);
  const first = segments.length ? /^phrases\s*=\s*"([^"]*)"$/i.exec(segments[0]) : null;
  if (!first) return null;
  const phrases = first[1].split(",").map((p) => p.trim()).filter(Boolean).slice(0, 6);
  const steps = [];
  let resultText = "";
  for (let i = 1; i < segments.length; i++) {
    const seg = /^([a-zA-Z_]+)(?:\(([^)]*)\))?$/.exec(segments[i]);
    if (!seg) continue;
    const op = seg[1];
    const args = remapFxPositional(op, parseFxStepArgs(seg[2] || ""));
    if (args.to) resultText = args.to;
    if (args.into) resultText = args.into;
    steps.push({ op, args });
  }
  return { matchedText: m[0], phrases, steps, resultText };
}

function runMetamorphosisTrigger(bodyEl) {
  if (!window.liveCaptainMetamorphosis) return;
  const text = bodyEl.textContent || "";

  const fx = parseFxTrigger(text);
  if (fx) {
    bodyEl.textContent = text.replace(fx.matchedText, "");
    if (!fx.phrases.length || !fx.steps.length) return;
    const landTarget = document.createElement("span");
    landTarget.className = "metamorphosis-land-wrap";
    bodyEl.parentElement.appendChild(landTarget);
    // A trigger arriving while a previous metamorphosis is still animating
    // is dropped, not queued (the component only runs one choreography at
    // a time) -- catch that rejection so it doesn't surface as an
    // unhandled promise error; the tag is still stripped from the message
    // either way so the raw syntax never leaks into the visible transcript.
    window.liveCaptainMetamorphosis.run(fx.steps, {
      sourceContainer: bodyEl,
      phrases: fx.phrases,
      resultText: fx.resultText,
      landTarget,
    }).done.catch(() => {});
    return;
  }

  const legacy = LEGACY_METAMORPHOSIS_TRIGGER.exec(text);
  if (legacy) {
    const phrases = legacy[1].split(",").map((p) => p.trim()).filter(Boolean).slice(0, 6);
    const resultText = legacy[2].trim();
    bodyEl.textContent = text.replace(LEGACY_METAMORPHOSIS_TRIGGER, "");
    if (!phrases.length || !resultText) return;
    const landTarget = document.createElement("span");
    landTarget.className = "metamorphosis-land-wrap";
    bodyEl.parentElement.appendChild(landTarget);
    window.liveCaptainMetamorphosis.perform({ sourceContainer: bodyEl, phrases, resultText, landTarget }).done.catch(() => {});
  }
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
  const trustedImageUrl = (candidate) => /^(?:data:image\/|https?:\/\/|\/root-console-api\/api\/generated-image\/)/.test(candidate);
  if (depth > 5 || value == null) return found;
  if (typeof value === "string") {
    // The generated-image endpoint is server-validated and single-purpose
    // (server.py mints it only for paths resolved inside GENERATED_IMAGE_DIR),
    // so it's safe to recognize wherever it appears -- not just under the
    // known field-name allow-list below, and not just in agentMessage prose.
    for (const match of value.matchAll(/\/root-console-api\/api\/generated-image\/[A-Za-z0-9_-]+/g)) {
      if (!found.has(match[0])) found.set(match[0], "Captain image artifact");
    }
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
      if (typeof entry === "string" && /^(image_url|imageUrl|url|src|data|path)$/.test(key) && trustedImageUrl(entry)) {
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

function fmtShipLogTimestamp(epochSeconds) {
  if (!epochSeconds) return "—";
  const d = new Date(epochSeconds * 1000);
  return d.toISOString().replace("T", " ").replace(/\.\d+Z$/, "Z");
}

function renderShipLog(entries) {
  shipLogList.innerHTML = "";
  if (!entries.length) {
    const empty = document.createElement("div");
    empty.className = "sl-empty";
    empty.textContent = "Nothing on disk yet.";
    shipLogList.appendChild(empty);
    return;
  }
  for (const entry of entries) {
    const row = document.createElement("div");
    row.className = "sl-row";

    const head = document.createElement("div");
    head.className = "sl-head";
    const title = document.createElement("span");
    title.className = "sl-title";
    title.textContent = entry.title || entry.file;
    const source = document.createElement("span");
    source.className = "sl-source";
    source.textContent = entry.source;
    head.appendChild(title);
    head.appendChild(source);

    const meta = document.createElement("div");
    meta.className = "sl-meta";
    meta.textContent = `${fmtShipLogTimestamp(entry.timestamp)} · ${entry.file}`;

    const excerpt = document.createElement("div");
    excerpt.className = "sl-excerpt";
    excerpt.textContent = entry.excerpt || "";

    row.appendChild(head);
    row.appendChild(meta);
    row.appendChild(excerpt);
    shipLogList.appendChild(row);
  }
}

async function pollShipLog() {
  try {
    const response = await fetch(`${API_BASE}/ship-log`);
    if (response.status === 401) return;
    const body = await response.json();
    renderShipLog(body.entries || []);
  } catch (err) {
    // ship-log endpoint unreachable; list just goes stale
  }
}

shipLogRefresh.addEventListener("click", pollShipLog);
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
  try {
    const bearingResponse = await fetch(`${LIVE_CAPTAIN_API_BASE}/status`);
    if (!bearingResponse.ok) {
      bearingIndicatorEl.textContent = `Live Captain — status unavailable (HTTP ${bearingResponse.status})`;
      return;
    }
    const bearing = await bearingResponse.json();
    bearingIndicatorEl.textContent =
      `${bearing.label} · kernel ${bearing.kernel_digest.slice(0, 8)} · ` +
      `bearing ${bearing.bearing_digest.slice(0, 8)} · restarts ${bearing.restart_count}`;
  } catch (err) {
    bearingIndicatorEl.textContent = "Live Captain — status unavailable";
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
  pollHandoffs();
  pollShipLog();
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

// Image-gen status widget: separate from the generic tool/reasoning lights
// because generation can run long, and the point is "still obviously
// working," not a 2.4s blip like the other activity pulses.
const imageGenWidget = document.querySelector('.status-widget[data-cat="image"]');
const imageGenCaption = imageGenWidget.querySelector(".caption");
const imageGenCountEl = imageGenWidget.querySelector(".count");
let imageGenTimer = null;
let imageGenActiveItemId = null;
let imageGenDoneCount = 0;

function looksLikeImageGen(item) {
  if (!item) return false;
  const haystack = JSON.stringify(item).toLowerCase();
  return /image[_-]?gen|generate[_-]?image|gpt-image|generated_images/.test(haystack);
}

function startImageGenIndicator(itemId) {
  imageGenActiveItemId = itemId || imageGenActiveItemId || true;
  if (imageGenTimer) return;
  imageGenWidget.classList.remove("done-flash");
  imageGenWidget.classList.add("spinning");
  let frame = 0;
  imageGenCaption.textContent = `${SPINNER_FRAMES[0]} generating…`;
  imageGenTimer = setInterval(() => {
    frame = (frame + 1) % SPINNER_FRAMES.length;
    imageGenCaption.textContent = `${SPINNER_FRAMES[frame]} generating…`;
  }, 80);
}

function stopImageGenIndicator(doneLabel) {
  if (imageGenTimer) {
    clearInterval(imageGenTimer);
    imageGenTimer = null;
  }
  const wasActive = imageGenActiveItemId != null;
  imageGenActiveItemId = null;
  imageGenWidget.classList.remove("spinning");
  if (doneLabel && wasActive) {
    imageGenDoneCount += 1;
    imageGenCountEl.textContent = imageGenDoneCount;
    imageGenCaption.textContent = doneLabel;
    imageGenWidget.classList.add("done-flash");
    setTimeout(() => imageGenWidget.classList.remove("done-flash"), 2400);
  } else {
    imageGenCaption.textContent = "";
  }
}

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
    followTerminalBottom();
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
      runMetamorphosisTrigger(bodyEl);
      followTerminalBottom();
      return;
    }
    if (item.type === "userMessage") return;
    const artifacts = imageArtifactsFrom(item, { scanFreeText: false });
    if (artifacts.size) {
      stopThinking();
      stopImageGenIndicator("✓ image ready");
      for (const [url, label] of artifacts) addImageArtifact(url, label);
      return;
    }
    if (imageGenActiveItemId != null && (item.id === imageGenActiveItemId || looksLikeImageGen(item))) {
      stopImageGenIndicator();
    }
    recordActivity(categoryForItemType(item.type), item.type || "item", summarizeItem(item) || "(completed)");
    return;
  }

  if (method === "item/started") {
    // The spinner already communicates liveness, and the completed event
    // for this same item lands moments later with an actual summary --
    // logging both would double every tool call in the activity log. The
    // image-gen widget is the one exception: it needs the start signal
    // because generation can run long and "still working" is the point.
    const item = params.item || {};
    if (looksLikeImageGen(item)) startImageGenIndicator(item.id);
    return;
  }

  if (method === "turn/started") {
    recordActivity("thread", "turn", "started");
    return;
  }
  if (method === "turn/completed") {
    stopThinking();
    stopImageGenIndicator();
    const turn = params.turn || {};
    const status = turn.status || "completed";
    recordActivity("thread", "turn", `completed (${status})`);
    if (status === "failed") {
      // Turn.error is only populated when status is "failed" -- it's the
      // one place the actual reason lives. Previously this branch discarded
      // it and showed only the bare word "failed", making every failure
      // unexplainable after the fact.
      const error = turn.error || {};
      const detail = [error.message, error.additionalDetails].filter(Boolean).join(" -- ") || "no error detail provided by Codex";
      addRow("error", "error", `Turn failed: ${detail}`);
    }
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
  streamSource = new EventSource(`${LIVE_CAPTAIN_API_BASE}/stream`);
  streamSource.onopen = () => {
    connEl.classList.add("live");
    connTextEl.textContent = "live";
    // A fresh connection (first load OR a reconnect after the backend
    // restarted) means any "in progress" state we were tracking from the
    // old connection is orphaned -- its completion event can never arrive,
    // so left alone it spins forever. Clear it silently rather than lie
    // about work still being done.
    stopThinking();
    stopImageGenIndicator();
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
    const response = await fetch(`${LIVE_CAPTAIN_API_BASE}/turn`, {
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

terminalEl.addEventListener("click", () => {
  // A drag-select ends with a click on this same element -- refocusing the
  // input unconditionally stole focus the instant the mouse button was
  // released and collapsed the selection (Chrome clears window selection
  // when focus moves to a text input). Only steal focus back when the user
  // isn't in the middle of selecting text.
  if (window.getSelection().toString()) return;
  input.focus();
});

// --- .docx packet drop box -------------------------------------------------
// Uploads land in docs/incoming/ as staged material; the panel says so
// explicitly, because "the file arrived" and "the packet is filed" are two
// different states and the readout shouldn't blur them.
const DOCX_API_BASE = "/docx-intake-api/api";
const docxDrop = document.getElementById("docx-drop");
const docxFileInput = document.getElementById("docx-file");
const docxResult = document.getElementById("docx-result");
const docxRecent = document.getElementById("docx-recent");

function docxSay(message, kind) {
  docxResult.textContent = message;
  docxResult.className = kind || "";
}

const docxCommitBtn = document.getElementById("docx-commit");
const docxClearBtn = document.getElementById("docx-clear");

async function loadDocxRecent() {
  try {
    const response = await fetch(`${DOCX_API_BASE}/recent`);
    if (!response.ok) return;
    const body = await response.json();
    const entries = body.entries || [];
    docxRecent.innerHTML = entries.length
      ? `<div class="docx-recent-item">staged: ${entries.length}</div>` +
        entries.slice(0, 4).map((e) => `<div class="docx-recent-item">· ${e.name}</div>`).join("")
      : "";
    docxCommitBtn.disabled = entries.length === 0;
    docxClearBtn.disabled = entries.length === 0;
  } catch (err) {
    /* panel is supplementary; a failed listing shouldn't shout */
  }
}

async function docxAction(endpoint, button, workingLabel) {
  const original = button.textContent;
  button.textContent = workingLabel;
  docxCommitBtn.disabled = true;
  docxClearBtn.disabled = true;
  try {
    const response = await fetch(`${DOCX_API_BASE}/${endpoint}`, { method: "POST" });
    const body = await response.json().catch(() => ({}));
    if (response.ok && body.ok) return body;
    docxSay(`✗ ${body.error || `HTTP ${response.status}`}`, "err");
    return null;
  } catch (err) {
    docxSay(`✗ ${String(err)}`, "err");
    return null;
  } finally {
    button.textContent = original;
    loadDocxRecent();
  }
}

docxCommitBtn.addEventListener("click", async () => {
  const result = await docxAction("commit", docxCommitBtn, "pushing…");
  if (result) {
    docxSay(`✓ Committed ${result.commit} (${result.count} packet(s)) and pushed to ${result.branch}`, "ok");
  }
});

docxClearBtn.addEventListener("click", async () => {
  if (!window.confirm("Delete all staged packets and their originals? Anything already committed stays in git history.")) return;
  const result = await docxAction("clear", docxClearBtn, "clearing…");
  if (result) {
    docxSay(`✓ Cleared ${result.removed} staged packet(s)`, "ok");
  }
});

async function uploadDocx(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".docx")) {
    docxSay("That's not a .docx — Word documents only.", "err");
    return;
  }
  docxDrop.classList.add("busy");
  docxSay(`Uploading ${file.name}…`, "");
  try {
    const form = new FormData();
    form.append("file", file, file.name);
    const response = await fetch(`${DOCX_API_BASE}/upload`, { method: "POST", body: form });
    const body = await response.json().catch(() => ({}));
    if (response.ok && body.ok) {
      docxSay(`✓ Staged ${body.words} words → ${body.markdown_path} (awaiting evaluation)`, "ok");
      loadDocxRecent();
    } else {
      docxSay(`✗ ${body.error || `HTTP ${response.status}`}`, "err");
    }
  } catch (err) {
    docxSay(`✗ ${String(err)}`, "err");
  } finally {
    docxDrop.classList.remove("busy");
    docxFileInput.value = "";
  }
}

docxDrop.addEventListener("click", () => docxFileInput.click());
docxDrop.addEventListener("keydown", (keyEvent) => {
  if (keyEvent.key === "Enter" || keyEvent.key === " ") {
    keyEvent.preventDefault();
    docxFileInput.click();
  }
});
docxFileInput.addEventListener("change", () => uploadDocx(docxFileInput.files[0]));

for (const eventName of ["dragenter", "dragover"]) {
  docxDrop.addEventListener(eventName, (dragEvent) => {
    dragEvent.preventDefault();
    docxDrop.classList.add("dragover");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  docxDrop.addEventListener(eventName, (dragEvent) => {
    dragEvent.preventDefault();
    docxDrop.classList.remove("dragover");
  });
}
docxDrop.addEventListener("drop", (dropEvent) => {
  uploadDocx(dropEvent.dataTransfer.files[0]);
});

loadDocxRecent();

pollStatus();
