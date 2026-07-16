const linkStatus = document.querySelector("#linkStatus");
const liveDot = document.querySelector("#liveDot");
const tickReadout = document.querySelector("#tickReadout");
const fleetState = document.querySelector("#fleetState");
const decisionCount = document.querySelector("#decisionCount");
const fleetPauseButton = document.querySelector("#fleetPauseButton");
const captainGrid = document.querySelector("#captainGrid");
const historyBody = document.querySelector("#historyBody");
const feedback = document.querySelector("#feedback");
const memoryGrid = document.querySelector("#memoryGrid");
const fleetNarrative = document.querySelector("#fleetNarrative");
const fleetNarrativeList = document.querySelector("#fleetNarrativeList");
const inquiryQuestion = document.querySelector("#inquiryQuestion");
const inquiryStatus = document.querySelector("#inquiryStatus");
const inquiryEvidence = document.querySelector("#inquiryEvidence");
const inquiryFindings = document.querySelector("#inquiryFindings");
const inquiryDecision = document.querySelector("#inquiryDecision");
const artifactGrid = document.querySelector("#artifactGrid");
const registryFreshness = document.querySelector("#registryFreshness");
const reviewGrid = document.querySelector("#reviewGrid");
const reviewSummary = document.querySelector("#reviewSummary");

const state = { socket: null, authority: false, snapshot: null, reconnectTimer: null };

function serverUrl() {
  if (location.protocol === "https:") return `wss://${location.host}/fleetcore-ws/ws`;
  if (location.hostname && location.hostname !== "localhost" && location.hostname !== "127.0.0.1") {
    return `ws://${location.host}/fleetcore-ws/ws`;
  }
  return "ws://localhost:4771/ws";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function title(value) {
  return String(value || "—").replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function showFeedback(message, error = false) {
  feedback.textContent = message;
  feedback.classList.toggle("is-error", error);
  feedback.hidden = false;
  window.clearTimeout(showFeedback.timer);
  showFeedback.timer = window.setTimeout(() => { feedback.hidden = true; }, 4200);
}

function connect() {
  window.clearTimeout(state.reconnectTimer);
  state.socket?.close();
  linkStatus.textContent = "Connecting…";
  liveDot.classList.remove("is-live");
  const socket = new WebSocket(serverUrl());
  state.socket = socket;
  socket.addEventListener("open", () => { linkStatus.textContent = "Linked"; liveDot.classList.add("is-live"); });
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.type === "connected") {
      state.authority = Boolean(message.command_authority);
    } else if (message.type === "snapshot") {
      state.snapshot = message.snapshot;
      render();
    } else if (message.type === "error") {
      showFeedback(message.message, true);
    }
  });
  socket.addEventListener("close", () => {
    state.authority = false;
    linkStatus.textContent = "Reconnecting";
    liveDot.classList.remove("is-live");
    fleetPauseButton.disabled = true;
    state.reconnectTimer = window.setTimeout(connect, 1800);
  });
  socket.addEventListener("error", () => socket.close());
}

function send(command) {
  if (!state.authority || state.socket?.readyState !== WebSocket.OPEN) {
    showFeedback("FleetCore command authority is unavailable.", true);
    return;
  }
  state.socket.send(JSON.stringify(command));
}

function currentIntent(vesselId) {
  return state.snapshot?.escort_intents?.find((intent) => intent.vessel_id === vesselId) || null;
}

function lastDecision(vesselId) {
  return [...(state.snapshot?.agent_decisions || [])].reverse().find((decision) => decision.vessel_id === vesselId) || null;
}

function renderCaptains() {
  const controls = state.snapshot?.captain_controls || [];
  captainGrid.innerHTML = controls.map((control) => {
    const intent = currentIntent(control.vessel_id);
    const decision = lastDecision(control.vessel_id);
    const overdue = intent && intent.reconsider_at_tick < state.snapshot.tick;
    const posture = control.enabled && intent && !overdue ? title(intent.posture) : "Deterministic fallback";
    const resultClass = decision?.outcome === "accepted" ? "accepted" : "rejected";
    return `<article class="captain-card ${control.enabled ? "" : "is-disabled"}">
      <header>
        <div><p class="eyebrow">${escapeHtml(control.role)}</p><h3>${escapeHtml(control.captain_id.replace("captain.", "Captain ").toUpperCase())}</h3></div>
        <span class="runtime-status status-${escapeHtml(control.runtime_status)}">${escapeHtml(title(control.runtime_status))}</span>
      </header>
      <div class="posture"><small>Current Posture</small><strong>${escapeHtml(posture)}</strong></div>
      <dl>
        <div><dt>Objective</dt><dd>${escapeHtml(intent?.objective || "Awaiting current intent.")}</dd></div>
        <div><dt>Assessment</dt><dd>${escapeHtml(intent?.assessment || control.status_message)}</dd></div>
        <div><dt>Runtime</dt><dd>${escapeHtml(control.provider)} · ${escapeHtml(control.status_message)}</dd></div>
        <div><dt>Last Decision</dt><dd class="${resultClass}">${decision ? `${escapeHtml(title(decision.outcome))}: ${escapeHtml(decision.result)}` : "No decision recorded."}</dd></div>
        <div><dt>Consequence</dt><dd>${escapeHtml(intent?.consequence || "No translated consequence yet.")}</dd></div>
      </dl>
      <footer><span>${escapeHtml(control.vessel_id)}</span><button type="button" data-vessel-id="${escapeHtml(control.vessel_id)}" data-enabled="${control.enabled}">${control.enabled ? "Disable" : "Enable"} Captain</button></footer>
    </article>`;
  }).join("");
}

function renderHistory() {
  const decisions = [...(state.snapshot?.agent_decisions || [])].slice(-20).reverse();
  if (!decisions.length) {
    historyBody.innerHTML = '<tr><td colspan="5">No captain decisions recorded yet.</td></tr>';
    return;
  }
  historyBody.innerHTML = decisions.map((decision) => {
    const consequence = decision.consequence || (decision.outcome === "rejected" ? decision.result : "Awaiting next world tick");
    return `<tr><td>${decision.submitted_tick}</td><td>${escapeHtml(decision.captain_id)}</td><td>${escapeHtml(title(decision.posture))}</td><td><span class="outcome ${decision.outcome}">${escapeHtml(title(decision.outcome))}</span></td><td>${escapeHtml(consequence)}</td></tr>`;
  }).join("");
}

function render() {
  tickReadout.textContent = state.snapshot.tick;
  fleetState.textContent = state.snapshot.agent_fleet_paused ? "Agent Fleet Paused" : "Captains Active";
  fleetState.classList.toggle("is-paused", state.snapshot.agent_fleet_paused);
  decisionCount.textContent = state.snapshot.agent_decisions?.length || 0;
  fleetPauseButton.textContent = state.snapshot.agent_fleet_paused ? "Resume Agent Fleet" : "Pause Agent Fleet";
  fleetPauseButton.disabled = !state.authority;
  renderCaptains();
  renderHistory();
}

// Captain Memory & Identity (Effort B): a separate, portless-service-backed
// read-only API (tools/living-fleet/memory/inspector_server.py, reached
// publicly through Caddy's /captain-memory-api/* reverse proxy -- see
// docs/deployment.md), polled independently of the FleetCore WebSocket
// above since it reports on a different backend.
function memoryApiUrl(path) {
  return `${location.origin}/captain-memory-api${path}`;
}

function renderMemory(data) {
  memoryGrid.innerHTML = (data.captains || []).map((captain) => {
    const traits = captain.traits || {};
    const traitRows = Object.entries(traits)
      .map(
        ([trait, value]) => `<div class="trait-bar">
      <span>${escapeHtml(title(trait))}</span>
      <div class="trait-bar-track"><div class="trait-bar-fill" style="width:${Math.round(value * 100)}%"></div></div>
      <span>${value.toFixed(2)}</span>
    </div>`
      )
      .join("");
    const relationship = captain.lieutenant_relationship || { trust: 0.5, friction: 0 };
    const beliefCounts = captain.belief_counts || { active: 0, superseded: 0 };
    return `<article class="captain-card memory-card">
      <header>
        <div><p class="eyebrow">${escapeHtml(captain.role || "")}</p><h3>${escapeHtml(captain.captain_id.replace("captain.", "Captain ").toUpperCase())}</h3></div>
      </header>
      <div class="trait-bars">${traitRows}</div>
      <dl>
        <div><dt>Lieutenant Trust / Friction</dt><dd>${relationship.trust.toFixed(2)} / ${relationship.friction.toFixed(2)}</dd></div>
        <div><dt>Beliefs</dt><dd>${beliefCounts.active} active, ${beliefCounts.superseded} superseded</dd></div>
        <div><dt>Latest Reflection</dt><dd>${captain.latest_reflection ? escapeHtml(captain.latest_reflection.summary) : "No reflection recorded yet."}</dd></div>
        <div><dt>Most Salient Memory</dt><dd>${captain.top_episode ? escapeHtml(captain.top_episode.what) : "No memories recorded yet."}</dd></div>
      </dl>
    </article>`;
  }).join("");

  if (data.fleet_narrative && data.fleet_narrative.length) {
    fleetNarrative.hidden = false;
    fleetNarrativeList.innerHTML = data.fleet_narrative
      .map(
        (item) => `<div>
      <strong>${escapeHtml(item.title)}</strong>
      <div class="narrative-pair">
        <div><small>Fact</small><p>${escapeHtml(item.fact_summary)}</p></div>
        <div class="mythology"><small>Fleet Lore</small><p>${escapeHtml(item.mythology)}</p></div>
      </div>
    </div>`
      )
      .join("");
  } else {
    fleetNarrative.hidden = true;
  }
}

async function refreshMemory() {
  try {
    const response = await fetch(memoryApiUrl("/captains/summary"), { cache: "no-store" });
    if (!response.ok) throw new Error(`status ${response.status}`);
    renderMemory(await response.json());
  } catch (error) {
    memoryGrid.innerHTML = `<p class="memory-unavailable">Captain memory API unavailable (${escapeHtml(error.message)}).</p>`;
  }
}

refreshMemory();
setInterval(refreshMemory, 8000);

async function refreshInquiry() {
  try {
    const response = await fetch("../../data/mission-ops.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`status ${response.status}`);
    const data = await response.json();
    inquiryQuestion.textContent = data.mission.objective;
    inquiryStatus.textContent = title(data.mission.status);
    inquiryEvidence.innerHTML = (data.evidence || []).map((item) => `<p><strong>${escapeHtml(title(item.classification))}</strong><br>${escapeHtml(item.claim)}</p>`).join("") || "No evidence recorded.";
    inquiryFindings.innerHTML = (data.findings || []).map((item) => `<p><strong>${escapeHtml(title(item.data.name))}</strong><br>${escapeHtml(item.data.finding)}<small>Counterevidence: ${escapeHtml(item.data.counterevidence)}</small></p>`).join("") || "No findings recorded.";
    const decision = data.decision?.data;
    inquiryDecision.innerHTML = decision
      ? `<p><strong>${escapeHtml(title(decision.action))}</strong> by ${escapeHtml(decision.decided_by.id)}</p><p>${escapeHtml(decision.reason)}</p>`
      : `<p>Human review required.</p><p>${escapeHtml(data.recommendation?.data?.recommendation || "")}</p>`;
  } catch (error) {
    inquiryStatus.textContent = "Unavailable";
    inquiryEvidence.textContent = `Mission projection unavailable (${error.message}).`;
  }
}
refreshInquiry();
setInterval(refreshInquiry, 10000);

async function refreshRegistry() {
  try {
    const response = await fetch("../../data/mission-artifacts.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`status ${response.status}`);
    const data = await response.json();
    const artifacts = data.artifacts || [];
    registryFreshness.textContent = `${artifacts.length} current artifacts · Mission Record cursor ${data.source_record_cursor}`;
    artifactGrid.innerHTML = artifacts.map((item) => `<article class="artifact-card">
      <header><strong>${escapeHtml(item.title)}</strong><span class="runtime-status">${escapeHtml(title(item.status))}</span></header>
      <p>${escapeHtml(title(item.artifact_type))} · ${escapeHtml(title(item.classification))}</p>
      <small>${escapeHtml(item.artifact_id)}</small>
      <small>Provenance: ${escapeHtml(item.locator?.value || "unavailable")}</small>
    </article>`).join("") || "No public Mission Record artifacts.";
  } catch (error) {
    registryFreshness.textContent = "Registry unavailable";
    artifactGrid.textContent = `Artifact projection unavailable (${error.message}).`;
  }
}
refreshRegistry();
setInterval(refreshRegistry, 10000);

async function refreshReviews() {
  try {
    const response = await fetch("../../data/mission-reviews.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`status ${response.status}`);
    const data = await response.json();
    reviewSummary.textContent = `${data.pending_count} pending · Mission Record cursor ${data.source_record_cursor}`;
    reviewGrid.innerHTML = (data.cards || []).map((card) => `<article class="artifact-card review-${escapeHtml(card.status)}">
      <header><strong>${escapeHtml(title(card.artifact_type))}</strong><span class="runtime-status">${escapeHtml(title(card.status))}</span></header>
      <p>${escapeHtml(card.summary)}</p>
      <small>Requires: ${escapeHtml(title(card.required_authority))} · revision ${escapeHtml(card.revision)}</small>
      <small>Accept does not mutate FleetCore.</small>
      <small>${escapeHtml(card.artifact_id)}</small>
    </article>`).join("") || "No review cards recorded.";
  } catch (error) {
    reviewSummary.textContent = "Review projection unavailable";
    reviewGrid.textContent = `Review cards unavailable (${error.message}).`;
  }
}
refreshReviews();
setInterval(refreshReviews, 10000);

fleetPauseButton.addEventListener("click", () => {
  send({ type: "set-agent-fleet-paused", paused: !state.snapshot.agent_fleet_paused });
});

captainGrid.addEventListener("click", (event) => {
  const button = event.target.closest("[data-vessel-id]");
  if (!button) return;
  send({ type: "set-captain-enabled", vessel_id: button.dataset.vesselId, enabled: button.dataset.enabled !== "true" });
});

connect();
