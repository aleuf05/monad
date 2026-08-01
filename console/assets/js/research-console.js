// Research Cockpit frontend, served live at cameronlampley.com/root/research.html
// (same file_server root as the main Captain terminal -- no separate deploy).
// Talks to the same root-console daemon (tools/root-console/server.py) through
// the existing /root-console-api/* Caddy proxy, via the new /api/research/*
// routes added for Phase 1A. Shares the session cookie set by the login form
// on / -- this page does not implement its own login.
const API_BASE = "/root-console-api/api";

const els = {
  connBadge: document.getElementById("conn"),
  connText: document.getElementById("conn-text"),
  modeBadge: document.getElementById("mode-badge"),
  packetSelect: document.getElementById("packet-select"),
  missingNote: document.getElementById("missing-note"),
  replayToggle: document.getElementById("replay-toggle"),
  replayReset: document.getElementById("replay-reset"),
  loginNote: document.getElementById("login-note"),
  body: document.getElementById("body"),
  ahId: document.getElementById("ah-id"),
  ahTitle: document.getElementById("ah-title"),
  ahStatus: document.getElementById("ah-status"),
  ahGen: document.getElementById("ah-gen"),
  ahRuns: document.getElementById("ah-runs"),
  ahAuthority: document.getElementById("ah-authority"),
  situation: document.getElementById("situation-content"),
  inquiry: document.getElementById("inquiry-content"),
  experiment: document.getElementById("experiment-content"),
  timeline: document.getElementById("timeline-content"),
  authority: document.getElementById("authority-content"),
  commandRail: document.getElementById("command-rail"),
  cmdError: document.getElementById("cmd-error"),
  rawEvidence: document.getElementById("raw-evidence"),
  rawEvidenceText: document.getElementById("raw-evidence-text"),
  eventsScroll: document.getElementById("events-scroll"),
};

let packets = [];
let currentArcId = null;
let currentArc = null;
let currentEvents = [];
let pollHandle = null;
let replaying = false;
let replayFrames = [];
let replayIndex = 0;
let replayTimer = null;
let rawEvidenceOpen = false;

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function api(path, opts) {
  const response = await fetch(`${API_BASE}${path}`, { credentials: "same-origin", ...opts });
  if (response.status === 401) {
    showLoggedOut();
    throw new Error("authentication required");
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.error || `HTTP ${response.status}`);
  }
  return body;
}

function showLoggedOut() {
  els.loginNote.style.display = "block";
  els.body.style.display = "none";
  els.connBadge.className = "error";
  els.connText.textContent = "not authenticated";
  if (pollHandle) { clearInterval(pollHandle); pollHandle = null; }
}

function setConn(state, text) {
  els.connBadge.className = state;
  els.connText.textContent = text;
}

// ---------------------------------------------------------------------------
// Packet registry
// ---------------------------------------------------------------------------

async function loadPacketRegistry() {
  const data = await api("/research/packets");
  packets = data.packets || [];
  els.packetSelect.innerHTML = "";
  for (const p of packets) {
    const opt = document.createElement("option");
    opt.value = p.researchArcId;
    opt.textContent = `${p.researchArcId} — ${p.title}${p.canonical ? "" : " (demo)"}`;
    els.packetSelect.appendChild(opt);
  }
  if (data.missingCanonicalIds && data.missingCanonicalIds.length) {
    els.missingNote.textContent = `Absent from archive: ${data.missingCanonicalIds.join(", ")}`;
  } else {
    els.missingNote.textContent = "";
  }
  // Section 3: prefer CAP-ARI-003 for initial testing. The real archived
  // CAP-ARI-003 has no execution backend (like 001/002, commands are
  // disabled), so default to the interactive demo walkthrough of the same
  // question -- CAP-ARI-003-DEMO -- and fall back to the real record.
  const preferred =
    packets.find((p) => p.researchArcId === "CAP-ARI-003-DEMO") ||
    packets.find((p) => p.researchArcId === "CAP-ARI-003") ||
    packets[0];
  if (preferred) {
    els.packetSelect.value = preferred.researchArcId;
    currentArcId = preferred.researchArcId;
  }
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

function renderModeBadge(mode) {
  els.modeBadge.textContent = mode || "—";
  els.modeBadge.className = `badge mode-${mode || ""}`;
}

function renderHeader(arc) {
  els.ahId.textContent = arc.researchArcId;
  els.ahTitle.textContent = arc.title;
  els.ahStatus.textContent = arc.status;
  els.ahStatus.className = `status-pill s-${arc.status}`;
  els.ahGen.textContent = arc.generationLimit ? `${arc.currentGeneration} / ${arc.generationLimit}` : `${arc.currentGeneration} / —`;
  els.ahRuns.textContent = arc.runBudget ? `${arc.runsUsed} / ${arc.runBudget}` : `${arc.runsUsed} / —`;
  els.ahAuthority.textContent =
    arc.status === "RUNNING" ? "Captain operating within approved envelope"
    : arc.status === "PAUSED" ? "Paused -- Captain holding at last safe step"
    : arc.status === "AWAITING_ADMIRAL" ? "Awaiting Admiral decision"
    : arc.status === "TERMINATED" ? "Terminated -- no autonomy remaining"
    : arc.canonical ? "Authorized, not yet started (no execution backend)"
    : "No autonomy active";
}

function renderSituation(arc) {
  if (!arc.captainAssessment) {
    els.situation.innerHTML = `<div class="empty">${esc(arc.notStartedReason || "No Captain assessment yet -- no generation has completed.")}</div>`;
    return;
  }
  const a = arc.captainAssessment;
  els.situation.innerHTML = `
    <div class="field-row"><span class="k">Observation</span><span class="v observation">${esc(a.observation)}</span></div>
    <div class="field-row"><span class="k">Interpretation</span><span class="v interpretation">${esc(a.interpretation)}</span></div>
    <div class="field-row"><span class="k">Confidence</span><span class="v conf ${esc(a.confidence)}">${esc(a.confidence)}</span></div>
    <div class="field-row"><span class="k">Alternative</span><span class="v alt">${esc(a.alternative)}</span></div>
    ${a.recommendedAction ? `<div class="field-row"><span class="k">Recommended</span><span class="v">${esc(a.recommendedAction)}</span></div>` : ""}
  `;
}

function renderInquiry(arc) {
  const latestGen = arc.recentGenerations[arc.recentGenerations.length - 1];
  const why = arc.activeExperiment
    ? arc.activeExperiment.purpose
    : latestGen ? latestGen.decision : "Arc has not started; no experiment selected yet.";
  els.inquiry.innerHTML = `
    <div class="field-row"><span class="k">Objective</span><span class="v">${esc(arc.primaryQuestion)}</span></div>
    ${arc.leadingHypothesis ? `<div class="field-row"><span class="k">Leading hyp.</span><span class="v">${esc(arc.leadingHypothesis)}</span></div>` : ""}
    ${arc.strongestAlternative ? `<div class="field-row"><span class="k">Strongest alt.</span><span class="v v alt">${esc(arc.strongestAlternative)}</span></div>` : ""}
    ${arc.unresolvedQuestion ? `<div class="field-row"><span class="k">Unresolved</span><span class="v">${esc(arc.unresolvedQuestion)}</span></div>` : ""}
    <div class="field-row"><span class="k">Why this experiment</span><span class="v">${esc(why)}</span></div>
  `;
}

function renderExperiment(arc) {
  const exp = arc.activeExperiment;
  if (!exp) {
    let reason = "no approved preset available";
    if (arc.status === "AUTHORIZED_NOT_STARTED") reason = "waiting for authorization";
    else if (arc.status === "AWAITING_ADMIRAL") reason = "natural stopping point reached; awaiting Admiral";
    else if (arc.status === "TERMINATED") reason = "arc terminated";
    else if (arc.status === "RUNNING" || arc.status === "PAUSED") reason = "selecting next experiment";
    els.experiment.innerHTML = `<div class="empty">No experiment active -- ${esc(reason)}.</div>`;
    return;
  }
  els.experiment.innerHTML = `
    <div class="exp-grid">
      <div><span class="k">ID</span><br>${esc(exp.experimentId)}</div>
      <div><span class="k">Status</span><br>${esc(exp.status)}</div>
      <div><span class="k">Condition</span><br>${esc(exp.condition || "—")}</div>
      <div><span class="k">Control</span><br>${esc(exp.control || "—")}</div>
      <div><span class="k">Seed</span><br>${esc(exp.seed ?? "—")}</div>
      <div><span class="k">Started</span><br>${esc(exp.startedAt || "—")}</div>
    </div>
    <div style="margin:0.5rem 0;"><span class="k" style="color:var(--dim); font-size:0.68rem;">${esc(exp.purpose)}</span></div>
    <progress max="100" value="${exp.progress || 0}"></progress>
  `;
}

function renderTimeline(arc) {
  if (!arc.recentGenerations.length) {
    els.timeline.innerHTML = `<div class="empty">No generations yet.</div>`;
    return;
  }
  const items = [...arc.recentGenerations].reverse().map((g) => `
    <details class="gen-item">
      <summary><span class="gid">${esc(g.generationId)}</span> ${esc(g.hypothesis).slice(0, 90)}</summary>
      <div class="gen-body">
        <div class="field-row"><span class="k">Question</span><span class="v">${esc(g.question)}</span></div>
        <div class="field-row"><span class="k">Hypothesis</span><span class="v">${esc(g.hypothesis)}</span></div>
        <div class="field-row"><span class="k">Experiment</span><span class="v">${esc(g.experiment)}</span></div>
        <div class="field-row"><span class="k">Result</span><span class="v">${esc(g.result || "—")}</span></div>
        <div class="field-row"><span class="k">Interpretation</span><span class="v interpretation">${esc(g.interpretation || "—")}</span></div>
        <div class="field-row"><span class="k">Confidence</span><span class="v conf ${esc(g.confidence)}">${esc(g.confidence || "—")}</span></div>
        <div class="field-row"><span class="k">Decision</span><span class="v">${esc(g.decision || "—")}</span></div>
      </div>
    </details>
  `).join("");
  els.timeline.innerHTML = items;
}

function renderAuthority(arc) {
  const genLeft = arc.generationLimit ? Math.max(arc.generationLimit - arc.currentGeneration, 0) : "—";
  const runsLeft = arc.runBudget ? Math.max(arc.runBudget - arc.runsUsed, 0) : "—";
  const list = (label, items) => items && items.length
    ? `<div class="field-row"><span class="k">${label}</span><span class="v"><ul class="plain">${items.map((i) => `<li>${esc(i)}</li>`).join("")}</ul></span></div>`
    : "";
  els.authority.innerHTML = `
    <div class="field-row"><span class="k">Autonomy</span><span class="v">${arc.status === "RUNNING" ? "Enabled" : "Not enabled"}</span></div>
    <div class="field-row"><span class="k">Gens remaining</span><span class="v">${esc(genLeft)}</span></div>
    <div class="field-row"><span class="k">Runs remaining</span><span class="v">${esc(runsLeft)}</span></div>
    ${list("Permitted", arc.permittedActions)}
    ${list("Prohibited", arc.prohibitedActions)}
    ${list("Stop conditions", arc.stopConditions)}
    ${list("Escalation", arc.escalationConditions)}
  `;
}

function renderEvents(events) {
  els.eventsScroll.innerHTML = events.map((e) => `
    <div class="event-row">
      <span class="ts">${esc((e.timestamp || "").slice(11, 19))}</span>
      <span class="type">${esc(e.type)}</span>
      <span class="summary">${esc(e.summary)}</span>
    </div>
  `).join("");
  els.eventsScroll.scrollTop = els.eventsScroll.scrollHeight;
}

function renderCommandRail(arc) {
  const disabledAll = replaying;
  const canonical = !!arc.canonical;
  const status = arc.status;
  const buttons = [
    { cmd: "start", label: "Start authorized arc", show: status === "AUTHORIZED_NOT_STARTED" },
    { cmd: "pause", label: "Pause", show: status === "RUNNING" },
    { cmd: "resume", label: "Resume", show: status === "PAUSED" },
    { cmd: "approve_next_experiment", label: "Approve next experiment", show: status === "RUNNING" },
    { cmd: "stop", label: "Stop arc", show: status === "RUNNING" || status === "PAUSED", cls: "danger" },
    { cmd: "return_control", label: "Return control", show: status === "RUNNING" || status === "PAUSED" },
    { cmd: "request_summary", label: "Request summary", show: true },
    { cmd: "export_packet", label: "Export return packet", show: true, cls: "primary" },
    { cmd: "__raw", label: "Inspect raw evidence", show: true },
  ];
  els.commandRail.innerHTML = "";
  for (const b of buttons.filter((b) => b.show)) {
    const btn = document.createElement("button");
    btn.textContent = b.label;
    if (b.cls) btn.className = b.cls;
    btn.disabled = disabledAll || (canonical && b.cmd !== "__raw");
    if (canonical && b.cmd !== "__raw") btn.title = arc.notStartedReason || "Not available for real archived packets in Phase 1A.";
    btn.addEventListener("click", () => b.cmd === "__raw" ? toggleRawEvidence() : runCommand(b.cmd));
    els.commandRail.appendChild(btn);
  }
}

function toggleRawEvidence() {
  rawEvidenceOpen = !rawEvidenceOpen;
  els.rawEvidence.classList.toggle("open", rawEvidenceOpen);
  if (rawEvidenceOpen) {
    els.rawEvidenceText.textContent = JSON.stringify({ arc: currentArc, events: currentEvents }, null, 2);
  }
}

function renderArc(arc, events) {
  currentArc = arc;
  currentEvents = events;
  els.body.style.display = "grid";
  els.loginNote.style.display = "none";
  renderModeBadge(arc.dataMode);
  renderHeader(arc);
  renderSituation(arc);
  renderInquiry(arc);
  renderExperiment(arc);
  renderTimeline(arc);
  renderAuthority(arc);
  renderEvents(events);
  renderCommandRail(arc);
  if (rawEvidenceOpen) els.rawEvidenceText.textContent = JSON.stringify({ arc, events }, null, 2);
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

async function runCommand(command) {
  els.cmdError.textContent = "";
  try {
    const result = await api("/research/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ arcId: currentArcId, command }),
    });
    if (command === "export_packet") {
      downloadJSON(result, `${currentArcId}-return-packet.json`);
    }
    await refresh();
  } catch (err) {
    els.cmdError.textContent = String(err.message || err);
  }
}

function downloadJSON(obj, filename) {
  const blob = new Blob([JSON.stringify(obj, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Fetch + poll (non-replay)
// ---------------------------------------------------------------------------

async function refresh() {
  if (replaying || !currentArcId) return;
  try {
    const [arc, eventsResp] = await Promise.all([
      api(`/research/arc?id=${encodeURIComponent(currentArcId)}`),
      api(`/research/events?id=${encodeURIComponent(currentArcId)}`),
    ]);
    setConn("live", "live");
    renderArc(arc, eventsResp.events || []);
  } catch (err) {
    setConn("error", String(err.message || err));
  }
}

els.packetSelect.addEventListener("change", () => {
  stopReplay();
  currentArcId = els.packetSelect.value;
  refresh();
});

// ---------------------------------------------------------------------------
// Replay (Mode 2 -- deterministic, CAP-ARI-003-DEMO only)
// ---------------------------------------------------------------------------

async function startReplay() {
  if (currentArcId !== "CAP-ARI-003-DEMO") {
    els.cmdError.textContent = "Deterministic replay is only available for CAP-ARI-003-DEMO.";
    return;
  }
  try {
    const resp = await api(`/research/replay?id=${encodeURIComponent(currentArcId)}`);
    replayFrames = resp.events || [];
  } catch (err) {
    els.cmdError.textContent = String(err.message || err);
    return;
  }
  if (!replayFrames.length) return;
  replaying = true;
  replayIndex = 0;
  els.replayToggle.textContent = "Stop replay";
  els.replayReset.style.display = "inline-block";
  if (pollHandle) { clearInterval(pollHandle); pollHandle = null; }
  playNextFrame();
}

function playNextFrame() {
  if (!replaying) return;
  if (replayIndex >= replayFrames.length) {
    replayTimer = null;
    return;
  }
  const shown = replayFrames.slice(0, replayIndex + 1).map((f) => f.event);
  const frame = replayFrames[replayIndex];
  const arc = { ...frame.arc, dataMode: "REPLAY" };
  renderArc(arc, shown);
  replayIndex += 1;
  replayTimer = setTimeout(playNextFrame, 900);
}

function stopReplay() {
  replaying = false;
  if (replayTimer) { clearTimeout(replayTimer); replayTimer = null; }
  els.replayToggle.textContent = "Replay demo";
  els.replayReset.style.display = "none";
  if (!pollHandle) pollHandle = setInterval(refresh, 4000);
}

els.replayToggle.addEventListener("click", () => {
  if (replaying) stopReplay(); else startReplay();
  if (!replaying) refresh();
});
els.replayReset.addEventListener("click", () => {
  stopReplay();
  refresh();
});

// ---------------------------------------------------------------------------
// Ask Captain -- brief question box, answer streams inline on this page
// (same daemon/thread as the main terminal's /api/turn + /api/stream;
// this panel just filters that stream down to the agent's reply text).
// ---------------------------------------------------------------------------

const askForm = document.getElementById("ask-form");
const askInput = document.getElementById("ask-input");
const askExchange = document.getElementById("ask-exchange");
const askStatus = document.getElementById("ask-status");

let askStream = null;
let askAnswerEl = null;

function connectAskStream() {
  if (askStream) return;
  askStream = new EventSource(`${API_BASE}/stream`);
  askStream.onopen = () => { askStatus.textContent = ""; };
  askStream.onerror = () => { askStatus.textContent = "(stream reconnecting…)"; };
  askStream.onmessage = (raw) => {
    let event;
    try { event = JSON.parse(raw.data); } catch { return; }
    if (event.type !== "codex_event") return;
    const method = event.method;
    const params = event.params || {};
    if (method === "item/agentMessage/delta") {
      if (!askAnswerEl) return;
      askAnswerEl.textContent += params.delta || "";
      return;
    }
    if (method === "item/completed" && (params.item || {}).type === "agentMessage") {
      askStatus.textContent = "";
      if (askAnswerEl) askAnswerEl.textContent = params.item.text || askAnswerEl.textContent;
      askAnswerEl = null;
      return;
    }
    if (method === "turn/started") { askStatus.textContent = "thinking…"; }
  };
}

askForm.addEventListener("submit", async (submitEvent) => {
  submitEvent.preventDefault();
  const text = askInput.value.trim();
  if (!text) return;
  askInput.value = "";
  connectAskStream();

  const youLine = document.createElement("div");
  youLine.className = "ask-line you";
  youLine.innerHTML = `<span class="who">you</span>`;
  youLine.appendChild(document.createTextNode(text));
  askExchange.appendChild(youLine);

  const captainLine = document.createElement("div");
  captainLine.className = "ask-line captain";
  captainLine.innerHTML = `<span class="who">captain</span>`;
  const bodySpan = document.createElement("span");
  captainLine.appendChild(bodySpan);
  askExchange.appendChild(captainLine);
  askAnswerEl = bodySpan;
  askStatus.textContent = "thinking…";

  try {
    const response = await fetch(`${API_BASE}/turn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      askStatus.textContent = "";
      bodySpan.textContent = `(error: ${body.error || response.status})`;
      askAnswerEl = null;
    }
  } catch (err) {
    askStatus.textContent = "";
    bodySpan.textContent = `(error: ${err})`;
    askAnswerEl = null;
  }
});

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

async function boot() {
  try {
    await loadPacketRegistry();
  } catch (err) {
    return; // 401 already handled by api() via showLoggedOut()
  }
  await refresh();
  pollHandle = setInterval(refresh, 4000);
}

boot();
