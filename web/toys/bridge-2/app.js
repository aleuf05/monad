// Bridge Station 2.0: one live view, one data source. A single WebSocket
// connection to fleetcore-serve feeds both the map panel and the optics
// panel -- there is exactly one `state.snapshot` object in this file, and
// both renderers read from it. That is the whole pitch: not two toys
// sharing a nav bar, but one instrument observing one world.
//
// Read-only by design (see Sprint.md's "Bridge Station 2.0" scope: "Out of
// Scope: Write/command authority from this view"). This page never sends a
// Command over the socket, and never presents controls that would.
const FIELD_OF_VIEW = 60;
const VESSEL_COLORS = {
  flagship: "#d8b46a",
  scout: "#8ad7c1",
  "passive-traffic": "#87c5d4"
};

const { bearingDegrees, distanceKm, normalizeDegrees } = window.MonadFleetState.utils;

const linkStatusEl = document.querySelector("#linkStatus");
const liveDotEl = document.querySelector("#liveDot");
const bearingReadoutEl = document.querySelector("#bearingReadout");
const canvas = document.querySelector("#opticsCanvas");
const ctx = canvas.getContext("2d");

const map = L.map("map", { minZoom: 2, worldCopyJump: true, attributionControl: false }).setView([20, 58], 6);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19 }).addTo(map);

const state = {
  snapshot: null,
  markers: new Map(),
  hasCenteredMap: false,
  bearing: 0,
  targetBearing: 0,
  velocity: 0,
  dragging: false,
  lastX: 0,
  lastTime: 0,
  reconnectDelayMs: 1000,
  reconnectTimer: null
};

function serverUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("server") || `ws://${window.location.hostname || "localhost"}:4771/ws`;
}

function setLinkStatus(text, disconnected) {
  linkStatusEl.textContent = text;
  linkStatusEl.parentElement.classList.toggle("is-disconnected", Boolean(disconnected));
  liveDotEl.classList.toggle("is-live", text === "Live");
}

function connect() {
  clearTimeout(state.reconnectTimer);
  setLinkStatus("Connecting…", false);
  const socket = new WebSocket(serverUrl());

  socket.addEventListener("open", () => {
    setLinkStatus("Live", false);
    state.reconnectDelayMs = 1000;
  });

  socket.addEventListener("message", (event) => {
    let message;
    try {
      message = JSON.parse(event.data);
    } catch (error) {
      return;
    }
    if (message.type === "snapshot") {
      applySnapshot(message.snapshot);
    }
  });

  socket.addEventListener("close", () => {
    setLinkStatus("Reconnecting…", true);
    state.reconnectTimer = setTimeout(() => {
      state.reconnectDelayMs = Math.min(state.reconnectDelayMs * 1.6, 15000);
      connect();
    }, state.reconnectDelayMs);
  });

  socket.addEventListener("error", () => setLinkStatus("Connection error", true));
}

// The one place both panels branch from a single shared snapshot. The map
// updates its markers immediately; the optics panel just stores the
// snapshot and lets the animation-frame loop (renderLoop) pick it up, so
// drag inertia keeps running smoothly between snapshots rather than only
// repainting when new data arrives.
function applySnapshot(snapshot) {
  state.snapshot = snapshot;
  updateMap(snapshot);
}

function vesselIcon(kind) {
  const color = VESSEL_COLORS[kind] || "#e8f0ed";
  const size = kind === "flagship" ? 16 : 11;
  return L.divIcon({
    className: "",
    html: `<span style="display:block;width:${size}px;height:${size}px;border-radius:50%;background:${color};box-shadow:0 0 0 2px rgba(4,6,7,0.85);"></span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2]
  });
}

function updateMap(snapshot) {
  const seen = new Set();
  snapshot.vessels.forEach((vessel) => {
    seen.add(vessel.id);
    const latLng = [vessel.position.lat, vessel.position.lng];
    let marker = state.markers.get(vessel.id);
    if (!marker) {
      marker = L.marker(latLng, { icon: vesselIcon(vessel.kind) }).addTo(map);
      state.markers.set(vessel.id, marker);
    } else {
      marker.setLatLng(latLng);
    }
    marker.bindTooltip(`${vessel.callsign} · ${vessel.status}`, { direction: "top" });
  });
  for (const [id, marker] of state.markers) {
    if (!seen.has(id)) {
      map.removeLayer(marker);
      state.markers.delete(id);
    }
  }
  if (!state.hasCenteredMap && snapshot.vessels.length) {
    const flagship = snapshot.vessels.find((v) => v.kind === "flagship") || snapshot.vessels[0];
    map.setView([flagship.position.lat, flagship.position.lng], 7);
    state.hasCenteredMap = true;
  }
}

function shortestDelta(from, to) {
  let delta = normalizeDegrees(to) - normalizeDegrees(from);
  if (delta > 180) delta -= 360;
  if (delta < -180) delta += 360;
  return delta;
}

function contactsFromSnapshot(snapshot) {
  const flagship = snapshot.vessels.find((v) => v.kind === "flagship");
  if (!flagship) return [];
  return snapshot.vessels
    .filter((v) => v.id !== flagship.id)
    .map((vessel) => ({
      id: vessel.id,
      callsign: vessel.callsign,
      kind: vessel.kind,
      bearing: bearingDegrees(flagship.position, vessel.position),
      rangeNm: distanceKm(flagship.position, vessel.position) * 0.539957
    }));
}

function resizeCanvas() {
  const rect = canvas.parentElement.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = rect.width * ratio;
  canvas.height = rect.height * ratio;
  canvas.style.width = `${rect.width}px`;
  canvas.style.height = `${rect.height}px`;
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
}

function drawOptics(width, height) {
  const horizonY = height * 0.42;
  const sky = ctx.createLinearGradient(0, 0, 0, horizonY);
  sky.addColorStop(0, "#26343c");
  sky.addColorStop(1, "#3d5058");
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, width, horizonY);

  const sea = ctx.createLinearGradient(0, horizonY, 0, height);
  sea.addColorStop(0, "#1c2b30");
  sea.addColorStop(1, "#0a1214");
  ctx.fillStyle = sea;
  ctx.fillRect(0, horizonY, width, height - horizonY);

  ctx.strokeStyle = "rgba(216, 180, 106, 0.5)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, horizonY);
  ctx.lineTo(width, horizonY);
  ctx.stroke();

  ctx.strokeStyle = "rgba(232, 240, 237, 0.35)";
  ctx.fillStyle = "rgba(149, 170, 166, 0.85)";
  ctx.font = "11px system-ui, sans-serif";
  ctx.textAlign = "center";
  for (let deg = -180; deg <= 180; deg += 5) {
    const bearing = normalizeDegrees(state.bearing + deg);
    const x = width / 2 + (deg / FIELD_OF_VIEW) * width;
    if (x < -20 || x > width + 20) continue;
    const isMajor = bearing % 10 === 0;
    ctx.beginPath();
    ctx.moveTo(x, horizonY - (isMajor ? 14 : 8));
    ctx.lineTo(x, horizonY);
    ctx.stroke();
    if (isMajor) {
      ctx.fillText(String(Math.round(bearing)).padStart(3, "0"), x, horizonY - 18);
    }
  }

  // Contacts aren't ordered by bearing (the snapshot sorts vessels by id),
  // so two contacts can land close together on screen after rotation. Sort
  // by screen x first, then stagger label rows for anything within label-
  // width of the previous one, rather than letting text collide.
  const LABEL_COLLISION_PX = 95;
  const visibleContacts = (state.snapshot ? contactsFromSnapshot(state.snapshot) : [])
    .map((contact) => {
      const relative = shortestDelta(state.bearing, contact.bearing);
      return { contact, relative, x: width / 2 + (relative / FIELD_OF_VIEW) * width };
    })
    .filter(({ relative }) => Math.abs(relative) <= FIELD_OF_VIEW / 2)
    .sort((a, b) => a.x - b.x);

  let lastX = -Infinity;
  let row = 0;
  visibleContacts.forEach(({ contact, x }) => {
    row = x - lastX < LABEL_COLLISION_PX ? row + 1 : 0;
    lastX = x;
    const y = horizonY + 18 + row * 46;
    const color = VESSEL_COLORS[contact.kind] || "#e8f0ed";
    ctx.beginPath();
    ctx.arc(x, y, 5, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.strokeStyle = "rgba(4,6,7,0.85)";
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.fillStyle = "rgba(232, 240, 237, 0.92)";
    ctx.font = "11px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(contact.callsign, x, y - 12);
    ctx.fillStyle = "rgba(149, 170, 166, 0.85)";
    ctx.fillText(`${contact.rangeNm.toFixed(1)} nm`, x, y + 20);
  });

  bearingReadoutEl.textContent = `${String(Math.round(normalizeDegrees(state.bearing))).padStart(3, "0")}°`;
}

function renderLoop() {
  if (!state.dragging) {
    state.targetBearing = normalizeDegrees(state.targetBearing + state.velocity);
    state.velocity *= 0.94;
    if (Math.abs(state.velocity) < 0.003) state.velocity = 0;
  }
  state.bearing = normalizeDegrees(state.bearing + shortestDelta(state.bearing, state.targetBearing) * 0.15);
  const rect = canvas.getBoundingClientRect();
  drawOptics(rect.width, rect.height);
  requestAnimationFrame(renderLoop);
}

function pointerX(event) {
  return event.clientX ?? event.touches?.[0]?.clientX ?? 0;
}

canvas.addEventListener("pointerdown", (event) => {
  canvas.setPointerCapture(event.pointerId);
  state.dragging = true;
  state.lastX = pointerX(event);
  state.lastTime = performance.now();
  state.velocity = 0;
});

canvas.addEventListener("pointermove", (event) => {
  if (!state.dragging) return;
  const x = pointerX(event);
  const now = performance.now();
  const dx = x - state.lastX;
  const dt = Math.max(16, now - state.lastTime);
  const deltaBearing = dx * -0.2;
  state.targetBearing = normalizeDegrees(state.targetBearing + deltaBearing);
  state.velocity = deltaBearing * (16 / dt);
  state.lastX = x;
  state.lastTime = now;
});

canvas.addEventListener("pointerup", (event) => {
  state.dragging = false;
  canvas.releasePointerCapture(event.pointerId);
});
canvas.addEventListener("pointercancel", () => { state.dragging = false; });

window.addEventListener("resize", resizeCanvas);
resizeCanvas();
requestAnimationFrame(renderLoop);
connect();
