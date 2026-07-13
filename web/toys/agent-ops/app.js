const linkStatus = document.querySelector("#linkStatus");
const liveDot = document.querySelector("#liveDot");
const tickReadout = document.querySelector("#tickReadout");
const fleetState = document.querySelector("#fleetState");
const decisionCount = document.querySelector("#decisionCount");
const fleetPauseButton = document.querySelector("#fleetPauseButton");
const captainGrid = document.querySelector("#captainGrid");
const historyBody = document.querySelector("#historyBody");
const feedback = document.querySelector("#feedback");

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

fleetPauseButton.addEventListener("click", () => {
  send({ type: "set-agent-fleet-paused", paused: !state.snapshot.agent_fleet_paused });
});

captainGrid.addEventListener("click", (event) => {
  const button = event.target.closest("[data-vessel-id]");
  if (!button) return;
  send({ type: "set-captain-enabled", vessel_id: button.dataset.vesselId, enabled: button.dataset.enabled !== "true" });
});

connect();
