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
  renderedWatchEventCount: 0,
  // Vessel-events consumption state -- see processVesselEvents()/
  // derivedStatusText() below. routeTotals tracks, per vessel, the leg
  // count a route started with (from the event that installed it) so "leg
  // X of Y" can be computed as legs shrink; lastVesselEvent tracks each
  // vessel's most recent event so a fresh route_replaced can show a brief
  // "Route changed" callout before settling back into leg wording.
  // lastVesselEventSeq cursors on each event's own event_seq (GitHub issue
  // #6), not array length/index -- vessel_events is now a bounded tail
  // (fleetcore-serve's --vessel-event-retention), and a length-based cursor
  // silently drops everything once the array can shrink/rotate. -1 so
  // event_seq 0 (the very first event ever) still counts as new.
  lastVesselEventSeq: -1,
  routeTotals: new Map(),
  lastVesselEvent: new Map()
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

  setLinkStatus("Connecting…", false);
  setAuthorityStatus("—", false);
  state.connected = false;
  updateControlsEnabled();

  const socket = new WebSocket(url);
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

  processVesselEvents(snapshot.vessel_events || []);
  renderVessels(snapshot.vessels);
  renderWatchEvents(snapshot.watch_events);

  if (!state.hasCenteredMap && snapshot.vessels.length) {
    const flagship = snapshot.vessels.find((vessel) => vessel.kind === "flagship") || snapshot.vessels[0];
    map.setView([flagship.position.lat, flagship.position.lng], 7);
    state.hasCenteredMap = true;
  }
}

// fleetcore-serve's speed_mps is the vessel's rated/commanded speed, not its
// instantaneous velocity -- it's never reset to 0 on arrival (there's no
// set-speed Command, so world.rs relies on the field staying nonzero for a
// vessel to be able to move again on its next set-route). A vessel only
// actually has way on while "underway" or "transiting"; "arrived",
// "holding", and "paused" mean it's stationary regardless of what
// speed_mps says.
function actualSpeedMps(vessel) {
  return vessel.status === "underway" || vessel.status === "transiting" ? vessel.speed_mps : 0;
}

// vessel_events (docs/architecture/fleetcore-api.md's "Vessel Events",
// docs/architecture/vessel-events-retention-investigation.md) is a bounded
// tail as of GitHub issue #6 -- fleetcore-serve keeps only the newest
// --vessel-event-retention entries, so array length/index is not a safe
// cursor (a rotated/shrunk array makes a length-based cursor silently stop
// seeing new events forever, including across this page's own WebSocket
// auto-reconnect, which never reloads the page or resets state). Cursor on
// each event's own event_seq instead -- stable regardless of how the array
// itself has rotated.
function processVesselEvents(vesselEvents) {
  if (!vesselEvents.length) return;
  const oldestRetainedSeq = vesselEvents[0].event_seq;
  if (state.lastVesselEventSeq >= 0 && oldestRetainedSeq > state.lastVesselEventSeq + 1) {
    // A real gap: events this client hasn't processed yet have already
    // aged out of the server's retained window (e.g. this tab sat
    // disconnected/backgrounded through more than --vessel-event-retention
    // worth of activity). Nothing to backfill from here -- the full history
    // remains durable server-side in events.jsonl -- but this should be
    // visible, not silent.
    console.warn(
      `fleetcore-live: vessel_events gap detected -- last seen event_seq ${state.lastVesselEventSeq}, oldest retained is now ${oldestRetainedSeq}. Some events were never processed by this client.`
    );
  }
  const newEvents = vesselEvents.filter((event) => event.event_seq > state.lastVesselEventSeq);
  if (!newEvents.length) return;
  newEvents.forEach((event) => {
    state.lastVesselEvent.set(event.vessel_id, event);
    if (event.type === "route_replaced") {
      state.routeTotals.set(event.vessel_id, { routeId: event.new_route_id, total: event.remaining_leg_count });
    } else if (event.type === "waypoint_reached") {
      const existing = state.routeTotals.get(event.vessel_id);
      // No route_replaced seen yet for this route_id (e.g. this is this
      // session's first snapshot, or the server restarted) -- best
      // available total is "however many legs remain, plus the one just
      // completed."
      if (!existing || existing.routeId !== event.route_id) {
        state.routeTotals.set(event.vessel_id, { routeId: event.route_id, total: event.remaining_leg_count + 1 });
      }
    } else if (event.type === "route_completed" || event.type === "holding") {
      state.routeTotals.delete(event.vessel_id);
    }
  });
  state.lastVesselEventSeq = newEvents[newEvents.length - 1].event_seq;
}

// Status wording derives from the vessel_events stream, not from
// re-inferring intent out of status/route the way the popup used to --
// that inference is exactly what made a route replacement landing near an
// old waypoint indistinguishable from a genuine arrival. See "Vessel
// Events" in docs/architecture/fleetcore-api.md for the full event model.
function derivedStatusText(vessel) {
  const lastEvent = state.lastVesselEvent.get(vessel.id);
  // Brief one-tick callout right when a replacement lands -- matching the
  // event's own tick against the snapshot we're rendering right now is
  // what makes this "just happened" rather than stale history.
  if (lastEvent && lastEvent.type === "route_replaced" && lastEvent.tick === state.lastTick) {
    return "Route changed";
  }
  if (vessel.status === "arrived") return "Arrived — complete";
  if (vessel.status === "holding") return "Holding";
  if (vessel.status === "underway") {
    const totals = state.routeTotals.get(vessel.id);
    if (totals && totals.routeId === vessel.route_id) {
      const remaining = vessel.route.length;
      const currentLeg = Math.max(1, totals.total - remaining + 1);
      return `Underway — leg ${currentLeg} of ${totals.total}`;
    }
    return "Underway";
  }
  return vessel.status.charAt(0).toUpperCase() + vessel.status.slice(1);
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
      `<strong>${vessel.callsign}</strong><br>${vessel.kind} &middot; ${derivedStatusText(vessel)}<br>` +
      `${(actualSpeedMps(vessel) * 1.94384).toFixed(1)} kn &middot; ${Math.round(vessel.course)}&deg;`
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
      `<span class="vessel-meta">${derivedStatusText(vessel)}</span>`;
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
