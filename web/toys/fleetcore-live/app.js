const VESSEL_COLORS = {
  flagship: "#d8b46a",
  scout: "#8ad7c1",
  "passive-traffic": "#87c5d4"
};

const linkStatusEl = document.querySelector("#linkStatus");
const liveDotEl = document.querySelector("#liveDot");
const authorityStatusEl = document.querySelector("#authorityStatus");
const clockStateEl = document.querySelector("#clockState");
const tickReadoutEl = document.querySelector("#tickReadout");
const simTimeReadoutEl = document.querySelector("#simTimeReadout");
const serverUrlInput = document.querySelector("#serverUrl");
const commandTokenInput = document.querySelector("#commandToken");
const commandFeedbackEl = document.querySelector("#commandFeedback");
const connectButton = document.querySelector("#connectButton");
const pauseResumeButton = document.querySelector("#pauseResumeButton");
const timeScaleInput = document.querySelector("#timeScaleInput");
const applyTimeScaleButton = document.querySelector("#applyTimeScaleButton");
const vesselListEl = document.querySelector("#vesselList");
const watchLogEl = document.querySelector("#watchLog");

const map = L.map("map", { minZoom: 2, worldCopyJump: true }).setView([20, 58], 6);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap contributors"
}).addTo(map);

const state = {
  socket: null,
  reconnectDelayMs: 1000,
  reconnectTimer: null,
  intentionalClose: false,
  connected: false,
  commandAuthority: false,
  hasCenteredMap: false,
  lastClockState: null,
  lastTick: null,
  commandFeedbackTimer: null,
  selectedId: null,
  markers: new Map(),
  renderedWatchEventCount: 0
};

function vesselIcon(kind, selected) {
  const color = VESSEL_COLORS[kind] || "#e8f0ed";
  const size = kind === "flagship" ? 16 : 12;
  return L.divIcon({
    className: "",
    html: `<span style="
      display:block;
      width:${size}px;
      height:${size}px;
      border-radius:50%;
      background:${color};
      box-shadow:0 0 0 2px rgba(4,6,7,0.8)${selected ? `, 0 0 0 5px ${color}55` : ""};
    "></span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2]
  });
}

function setLinkStatus(text, disconnected) {
  linkStatusEl.textContent = text;
  linkStatusEl.classList.toggle("is-disconnected", Boolean(disconnected));
  liveDotEl.classList.toggle("is-live", text === "Live");
}

function showCommandFeedback(message) {
  clearTimeout(state.commandFeedbackTimer);
  commandFeedbackEl.textContent = message;
  commandFeedbackEl.hidden = false;
  state.commandFeedbackTimer = setTimeout(() => {
    commandFeedbackEl.hidden = true;
  }, 5000);
}

function setAuthorityStatus(text, authorized) {
  authorityStatusEl.textContent = text;
  authorityStatusEl.classList.toggle("is-authorized", Boolean(authorized));
  state.commandAuthority = Boolean(authorized);
  updateControlsEnabled();
}

// Controls only ever enable when both connected AND holding command
// authority -- the server is read-only by default (see Sprint.md), so a
// connected-but-unauthorized visitor must not see live-looking buttons that
// the server will just reject.
function updateControlsEnabled() {
  const enabled = state.connected && state.commandAuthority;
  pauseResumeButton.disabled = !enabled;
  timeScaleInput.disabled = !enabled;
  applyTimeScaleButton.disabled = !enabled;
}

function connect() {
  clearTimeout(state.reconnectTimer);
  if (state.socket) {
    state.intentionalClose = true;
    state.socket.close();
  }
  state.intentionalClose = false;
  state.reconnectDelayMs = 1000;

  const url = serverUrlInput.value.trim();
  if (!url) return;
  const token = commandTokenInput.value.trim();
  const connectUrl = token
    ? `${url}${url.includes("?") ? "&" : "?"}token=${encodeURIComponent(token)}`
    : url;

  setLinkStatus("Connecting…", false);
  setAuthorityStatus("—", false);
  state.connected = false;
  updateControlsEnabled();

  const socket = new WebSocket(connectUrl);
  state.socket = socket;

  socket.addEventListener("open", () => {
    setLinkStatus("Live", false);
    state.connected = true;
    updateControlsEnabled();
  });

  socket.addEventListener("message", (event) => {
    let message;
    try {
      message = JSON.parse(event.data);
    } catch (error) {
      console.warn("FleetCore Live: malformed message", error);
      return;
    }
    if (message.type === "connected") {
      setAuthorityStatus(
        message.command_authority ? "Command" : "Read-only",
        message.command_authority
      );
    } else if (message.type === "snapshot") {
      applySnapshot(message.snapshot);
    } else if (message.type === "error") {
      console.warn("FleetCore Live: server rejected a command:", message.message);
      showCommandFeedback(message.message);
    }
  });

  socket.addEventListener("close", () => {
    setLinkStatus("Disconnected", true);
    setAuthorityStatus("—", false);
    state.connected = false;
    updateControlsEnabled();
    if (!state.intentionalClose) scheduleReconnect();
  });

  socket.addEventListener("error", () => {
    setLinkStatus("Connection error", true);
  });
}

function scheduleReconnect() {
  clearTimeout(state.reconnectTimer);
  setLinkStatus(`Reconnecting in ${Math.round(state.reconnectDelayMs / 1000)}s…`, true);
  state.reconnectTimer = setTimeout(() => {
    state.reconnectDelayMs = Math.min(state.reconnectDelayMs * 1.6, 15000);
    connect();
  }, state.reconnectDelayMs);
}

function sendCommand(command) {
  if (!state.socket || state.socket.readyState !== WebSocket.OPEN) return;
  state.socket.send(JSON.stringify(command));
}

function applySnapshot(snapshot) {
  clockStateEl.textContent = snapshot.clock_state === "running" ? "Running" : "Paused";
  tickReadoutEl.textContent = String(snapshot.tick);
  simTimeReadoutEl.textContent = snapshot.sim_time;
  if (state.lastTick !== null && snapshot.tick !== state.lastTick) {
    // Retrigger the one-shot pulse animation even if it's already mid-flight
    // from the previous tick: remove the class, force a reflow, re-add it.
    tickReadoutEl.classList.remove("is-pulse");
    void tickReadoutEl.offsetWidth;
    tickReadoutEl.classList.add("is-pulse");
  }
  state.lastTick = snapshot.tick;
  if (state.lastClockState !== snapshot.clock_state) {
    pauseResumeButton.textContent = snapshot.clock_state === "running" ? "Pause" : "Resume";
    state.lastClockState = snapshot.clock_state;
  }
  if (document.activeElement !== timeScaleInput) {
    timeScaleInput.value = snapshot.time_scale;
  }

  renderVessels(snapshot.vessels);
  renderWatchEvents(snapshot.watch_events);

  if (!state.hasCenteredMap && snapshot.vessels.length) {
    const flagship = snapshot.vessels.find((vessel) => vessel.kind === "flagship") || snapshot.vessels[0];
    map.setView([flagship.position.lat, flagship.position.lng], 7);
    state.hasCenteredMap = true;
  }
}

function renderVessels(vessels) {
  const seenIds = new Set();

  vessels.forEach((vessel) => {
    seenIds.add(vessel.id);
    const latLng = [vessel.position.lat, vessel.position.lng];
    const selected = vessel.id === state.selectedId;
    let marker = state.markers.get(vessel.id);
    if (!marker) {
      marker = L.marker(latLng, { icon: vesselIcon(vessel.kind, selected) }).addTo(map);
      marker.on("click", () => selectVessel(vessel.id));
      state.markers.set(vessel.id, marker);
    } else {
      marker.setLatLng(latLng);
      marker.setIcon(vesselIcon(vessel.kind, selected));
    }
    marker.bindPopup(
      `<strong>${vessel.callsign}</strong><br>${vessel.kind} &middot; ${vessel.status}<br>` +
      `${(vessel.speed_mps * 1.94384).toFixed(1)} kn &middot; ${Math.round(vessel.course)}&deg;`
    );
  });

  for (const [id, marker] of state.markers) {
    if (!seenIds.has(id)) {
      map.removeLayer(marker);
      state.markers.delete(id);
    }
  }

  renderVesselList(vessels);
}

function renderVesselList(vessels) {
  vesselListEl.innerHTML = "";
  if (!vessels.length) {
    vesselListEl.innerHTML = '<li class="empty-note">No vessels reported.</li>';
    return;
  }
  vessels.forEach((vessel) => {
    const item = document.createElement("li");
    item.classList.toggle("is-selected", vessel.id === state.selectedId);
    item.innerHTML =
      `<span class="vessel-name">${vessel.callsign}</span>` +
      `<span class="vessel-meta">${vessel.status}</span>`;
    item.addEventListener("click", () => selectVessel(vessel.id));
    vesselListEl.appendChild(item);
  });
}

function selectVessel(id) {
  state.selectedId = id;
  const marker = state.markers.get(id);
  if (marker) {
    map.panTo(marker.getLatLng());
    marker.openPopup();
  }
}

function renderWatchEvents(watchEvents) {
  if (watchEvents.length === state.renderedWatchEventCount) return;
  watchLogEl.innerHTML = "";
  const recent = watchEvents.slice(-20).reverse();
  if (!recent.length) {
    watchLogEl.innerHTML = '<li class="empty-note">No watch events yet.</li>';
  } else {
    recent.forEach((event, index) => {
      const item = document.createElement("li");
      item.classList.toggle("is-new", index === 0 && watchEvents.length > state.renderedWatchEventCount);
      item.textContent = `[tick ${event.tick}] ${event.message}`;
      watchLogEl.appendChild(item);
    });
  }
  state.renderedWatchEventCount = watchEvents.length;
}

connectButton.addEventListener("click", connect);
serverUrlInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") connect();
});

pauseResumeButton.addEventListener("click", () => {
  const nextCommand = pauseResumeButton.textContent === "Pause" ? "pause-clock" : "resume-clock";
  sendCommand({ type: nextCommand });
});

applyTimeScaleButton.addEventListener("click", () => {
  const scale = Number(timeScaleInput.value);
  if (!Number.isFinite(scale) || scale < 1) return;
  sendCommand({ type: "set-time-scale", scale: Math.round(scale) });
});

connect();
