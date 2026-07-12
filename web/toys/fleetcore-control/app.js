const linkStatusEl = document.querySelector("#linkStatus");
const liveDotEl = document.querySelector("#liveDot");
const authorityStatusEl = document.querySelector("#authorityStatus");
const clockStateEl = document.querySelector("#clockState");
const tickReadoutEl = document.querySelector("#tickReadout");
const vesselCountEl = document.querySelector("#vesselCount");
const serverUrlInput = document.querySelector("#serverUrl");
const commandTokenInput = document.querySelector("#commandToken");
const commandFeedbackEl = document.querySelector("#commandFeedback");
const connectButton = document.querySelector("#connectButton");
const pauseResumeButton = document.querySelector("#pauseResumeButton");
const timeScaleInput = document.querySelector("#timeScaleInput");
const applyTimeScaleButton = document.querySelector("#applyTimeScaleButton");
const vesselListEl = document.querySelector("#vesselList");
const watchLogEl = document.querySelector("#watchLog");
const scenarioButtons = Array.from(document.querySelectorAll(".scenario-button"));
const spawnForm = document.querySelector("#spawnForm");
const spawnSubmitButton = spawnForm.querySelector("button[type=submit]");
const routeForm = document.querySelector("#routeForm");
const routeSubmitButton = routeForm.querySelector("button[type=submit]");
const routeVesselSelect = document.querySelector("#routeVesselSelect");

const state = {
  socket: null,
  reconnectDelayMs: 1000,
  reconnectTimer: null,
  intentionalClose: false,
  connected: false,
  commandAuthority: false,
  lastClockState: null,
  lastTick: null,
  commandFeedbackTimer: null,
  renderedWatchEventCount: 0,
  lastSnapshot: null
};

// Every generated id gets this suffix so repeated scenario runs (or repeated
// manual spawns) never collide with an earlier run still sitting in the
// world -- there is no despawn command, so a collision would just be a
// permanent, confusing rejection (world.rs's spawn-passive-contact command
// errors on a duplicate id) rather than something that self-heals.
function idSuffix() {
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
}

function setLinkStatus(text, disconnected) {
  linkStatusEl.textContent = text;
  linkStatusEl.classList.toggle("is-disconnected", Boolean(disconnected));
  liveDotEl.classList.toggle("is-live", text === "Live");
}

function showCommandFeedback(message, isError = true) {
  clearTimeout(state.commandFeedbackTimer);
  commandFeedbackEl.textContent = message;
  commandFeedbackEl.classList.toggle("is-error", isError);
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

// Every write control in this toy only ever enables when both connected AND
// holding command authority -- same rule toys/fleetcore-live/ and Bridge's
// Command Token field already follow, since the server is read-only by
// default and a connected-but-unauthorized visitor must not see live-looking
// controls the server will just reject.
function updateControlsEnabled() {
  const enabled = state.connected && state.commandAuthority;
  pauseResumeButton.disabled = !enabled;
  timeScaleInput.disabled = !enabled;
  applyTimeScaleButton.disabled = !enabled;
  spawnSubmitButton.disabled = !enabled;
  routeSubmitButton.disabled = !enabled;
  scenarioButtons.forEach((button) => { button.disabled = !enabled; });
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
      console.warn("FleetCore Control Center: malformed message", error);
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
      console.warn("FleetCore Control Center: server rejected a command:", message.message);
      showCommandFeedback(message.message);
    }
  });

  socket.addEventListener("close", () => {
    setLinkStatus("Disconnected", true);
    setAuthorityStatus("—", false);
    state.connected = false;
    state.lastSnapshot = null;
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
  state.lastSnapshot = snapshot;
  clockStateEl.textContent = snapshot.clock_state === "running" ? "Running" : "Paused";
  tickReadoutEl.textContent = String(snapshot.tick);
  vesselCountEl.textContent = String(snapshot.vessels.length);
  if (state.lastTick !== null && snapshot.tick !== state.lastTick) {
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

  renderVesselList(snapshot.vessels);
  renderRouteVesselOptions(snapshot.vessels);
  renderWatchEvents(snapshot.watch_events);
}

function renderVesselList(vessels) {
  vesselListEl.innerHTML = "";
  if (!vessels.length) {
    vesselListEl.innerHTML = '<li class="empty-note">No vessels reported.</li>';
    return;
  }
  vessels.forEach((vessel) => {
    const item = document.createElement("li");
    item.innerHTML =
      `<span class="vessel-name">${vessel.callsign}</span>` +
      `<span class="vessel-meta">${vessel.kind} &middot; ${vessel.status} &middot; ${vessel.position.lat.toFixed(3)}, ${vessel.position.lng.toFixed(3)}</span>`;
    vesselListEl.appendChild(item);
  });
}

// Kept separate from renderVesselList (rather than reusing its DOM) since a
// <select>'s options and a vessel-list <li>'s markup need different shapes,
// and preserving the operator's current dropdown pick across every incoming
// snapshot matters here -- losing it mid-scenario would be a bad surprise.
function renderRouteVesselOptions(vessels) {
  const previousValue = routeVesselSelect.value;
  routeVesselSelect.innerHTML = "";
  vessels.forEach((vessel) => {
    const option = document.createElement("option");
    option.value = vessel.id;
    option.textContent = `${vessel.callsign} (${vessel.kind})`;
    routeVesselSelect.appendChild(option);
  });
  if (vessels.some((vessel) => vessel.id === previousValue)) {
    routeVesselSelect.value = previousValue;
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

spawnForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const lat = Number(document.querySelector("#spawnLat").value);
  const lng = Number(document.querySelector("#spawnLng").value);
  const course = Number(document.querySelector("#spawnCourse").value);
  const speed = Number(document.querySelector("#spawnSpeed").value);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    showCommandFeedback("Lat/Lng must be numbers.");
    return;
  }
  const name = document.querySelector("#spawnName").value.trim() || "Unnamed Contact";
  const callsign = document.querySelector("#spawnCallsign").value.trim() || name.toUpperCase();
  sendCommand({
    type: "spawn-passive-contact",
    id: `manual-${idSuffix()}`,
    name,
    callsign,
    position: { lat, lng },
    course: Number.isFinite(course) ? course : 0,
    speed_mps: Number.isFinite(speed) ? speed : 0
  });
});

function parseWaypoints(text) {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const parts = line.split(",").map((part) => Number(part.trim()));
      if (parts.length !== 2 || !parts.every(Number.isFinite)) return null;
      return { lat: parts[0], lng: parts[1] };
    });
}

routeForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const vesselId = routeVesselSelect.value;
  if (!vesselId) {
    showCommandFeedback("No vessel selected -- world state may not have loaded yet.");
    return;
  }
  const waypoints = parseWaypoints(document.querySelector("#routeWaypoints").value);
  if (!waypoints.length || waypoints.includes(null)) {
    showCommandFeedback('Each waypoint line must be "lat,lng" with two numbers.');
    return;
  }
  sendCommand({ type: "set-route", vessel_id: vesselId, route: waypoints });
});

function flagshipPosition() {
  const flagship = state.lastSnapshot?.vessels.find((vessel) => vessel.kind === "flagship");
  return flagship ? flagship.position : null;
}

// Each scenario is a short, hardcoded command sequence -- spawn(s), an
// optional route, and a record-watch-event describing what just happened.
// All positions are offsets from the flagship's position at the moment the
// button is clicked, not a live-tracking route: FleetCore's set-route takes
// a fixed waypoint list, so a "collision course" scenario converges on
// where the flagship *was*, not a moving target. That is a real limitation
// worth knowing before relying on this for anything but a one-shot setup.
const SCENARIOS = {
  "distress-call": () => {
    const flagship = flagshipPosition();
    if (!flagship) return showCommandFeedback("No flagship position yet -- wait for the first snapshot.");
    const suffix = idSuffix();
    const callsign = `MAYDAY ${suffix.slice(-4).toUpperCase()}`;
    sendCommand({
      type: "spawn-passive-contact",
      id: `distress-${suffix}`,
      name: "Distressed Vessel",
      callsign,
      position: { lat: flagship.lat + 0.06, lng: flagship.lng + 0.04 },
      course: 0,
      speed_mps: 0
    });
    sendCommand({ type: "record-watch-event", message: `Distress call received from ${callsign}` });
  },
  "storm-convoy": () => {
    const flagship = flagshipPosition();
    if (!flagship) return showCommandFeedback("No flagship position yet -- wait for the first snapshot.");
    const suffix = idSuffix();
    const legOffsets = [-0.12, 0, 0.12];
    legOffsets.forEach((offset, index) => {
      const id = `storm-${suffix}-${index}`;
      const start = { lat: flagship.lat + 0.35, lng: flagship.lng + offset };
      const routeTarget = { lat: flagship.lat + 0.1, lng: flagship.lng + offset * 0.4 };
      sendCommand({
        type: "spawn-passive-contact",
        id,
        name: `Storm Convoy ${index + 1}`,
        callsign: `CONVOY ${index + 1}`,
        position: start,
        course: 180,
        speed_mps: 7
      });
      sendCommand({ type: "set-route", vessel_id: id, route: [routeTarget] });
    });
    sendCommand({ type: "record-watch-event", message: "Storm convoy of 3 vessels reported entering the area" });
  },
  "collision-course": () => {
    const flagship = flagshipPosition();
    if (!flagship) return showCommandFeedback("No flagship position yet -- wait for the first snapshot.");
    const suffix = idSuffix();
    const id = `collision-${suffix}`;
    const start = { lat: flagship.lat + 0.4, lng: flagship.lng + 0.4 };
    sendCommand({
      type: "spawn-passive-contact",
      id,
      name: "Unidentified Contact",
      callsign: `BOGEY ${suffix.slice(-4).toUpperCase()}`,
      position: start,
      course: 225,
      speed_mps: 9
    });
    sendCommand({ type: "set-route", vessel_id: id, route: [flagship] });
    sendCommand({ type: "record-watch-event", message: "Contact on possible collision bearing with flagship" });
  }
};

scenarioButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const scenario = SCENARIOS[button.dataset.scenario];
    if (scenario) scenario();
  });
});

connect();
