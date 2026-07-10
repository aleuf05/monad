const TAU = Math.PI * 2;
const FIELD_OF_VIEW = 54;
const MAX_RANGE = 14;

const vessels = [
  {
    id: "alpha",
    name: "Scout Alpha",
    callsign: "SCOUT ALPHA",
    mission: "Research Sweep",
    status: "Nominal",
    report: "Mapping a slow current line east of the Monad track.",
    color: "#8ad7c1",
    baseBearing: 14,
    range: 8.3,
    speed: 0.003,
    wobble: 10,
    rangeDrift: 1.1,
  },
  {
    id: "bravo",
    name: "Scout Bravo",
    callsign: "SCOUT BRAVO",
    mission: "Weather Sounding",
    status: "Reporting at interval",
    report: "Maintaining distance while sampling the forward horizon.",
    color: "#d8b46a",
    baseBearing: 334,
    range: 10.7,
    speed: -0.0022,
    wobble: 14,
    rangeDrift: 0.8,
  },
  {
    id: "charlie",
    name: "Scout Charlie",
    callsign: "SCOUT CHARLIE",
    mission: "Signal Relay",
    status: "Station keeping",
    report: "Holding relay posture and confirming clean channel response.",
    color: "#94bfe8",
    baseBearing: 58,
    range: 6.9,
    speed: 0.0035,
    wobble: 8,
    rangeDrift: 1.4,
  },
];

const canvas = document.querySelector("#periscopeCanvas");
const frame = document.querySelector("#scopeFrame");
const ctx = canvas.getContext("2d");
const bearingReadout = document.querySelector("#bearingReadout");
const bearingBand = document.querySelector("#bearingBand");
const contactStrip = document.querySelector("#contactStrip");
const detailsButton = document.querySelector("#detailsButton");
const panelEmpty = document.querySelector("#panelEmpty");
const panelContent = document.querySelector("#panelContent");
const panelCallsign = document.querySelector("#panelCallsign");
const panelName = document.querySelector("#panelName");
const panelMission = document.querySelector("#panelMission");
const panelStatus = document.querySelector("#panelStatus");
const panelReport = document.querySelector("#panelReport");
const panelBearing = document.querySelector("#panelBearing");
const panelRange = document.querySelector("#panelRange");

const state = {
  bearing: 0,
  targetBearing: 0,
  velocity: 0,
  dragging: false,
  lastX: 0,
  lastTime: 0,
  selectedId: null,
  visibleContacts: [],
  contactButtonsReady: false,
};

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function normalizeDegrees(value) {
  return ((value % 360) + 360) % 360;
}

function shortestDelta(from, to) {
  let delta = normalizeDegrees(to) - normalizeDegrees(from);
  if (delta > 180) delta -= 360;
  if (delta < -180) delta += 360;
  return delta;
}

function formatBearing(value) {
  return `${String(Math.round(normalizeDegrees(value))).padStart(3, "0")}°`;
}

function vesselState(vessel, elapsedSeconds) {
  const path = elapsedSeconds * vessel.speed;
  const drift = Math.sin(elapsedSeconds * 0.19 + vessel.baseBearing) * vessel.wobble;
  const range = vessel.range + Math.cos(elapsedSeconds * 0.16 + vessel.range) * vessel.rangeDrift;
  return {
    ...vessel,
    bearing: normalizeDegrees(vessel.baseBearing + path * 180 + drift),
    range: clamp(range, 3.4, MAX_RANGE),
  };
}

function projectContact(contact) {
  const relative = shortestDelta(state.bearing, contact.bearing);
  const visible = Math.abs(relative) <= FIELD_OF_VIEW / 2;
  const rangeRatio = clamp(contact.range / MAX_RANGE, 0, 1);
  return {
    ...contact,
    relative,
    visible,
    x: 0.5 + relative / FIELD_OF_VIEW,
    y: 0.61 - (1 - rangeRatio) * 0.27,
    scale: 1 - rangeRatio * 0.42,
  };
}

function resizeCanvas() {
  const size = Math.round(canvas.getBoundingClientRect().width);
  const deviceRatio = window.devicePixelRatio || 1;
  const target = Math.max(320, Math.round(size * deviceRatio));
  if (canvas.width !== target || canvas.height !== target) {
    canvas.width = target;
    canvas.height = target;
  }
}

function renderOcean(now) {
  const w = canvas.width;
  const h = canvas.height;
  const horizon = h * 0.45;
  const sky = ctx.createLinearGradient(0, 0, 0, horizon);
  sky.addColorStop(0, "#172027");
  sky.addColorStop(0.58, "#31404a");
  sky.addColorStop(1, "#7f9a9b");
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, w, horizon);

  ctx.fillStyle = "rgba(238, 224, 177, 0.72)";
  ctx.fillRect(0, horizon - 1, w, 2);

  const ocean = ctx.createLinearGradient(0, horizon, 0, h);
  ocean.addColorStop(0, "#1d5963");
  ocean.addColorStop(0.46, "#12333a");
  ocean.addColorStop(1, "#071316");
  ctx.fillStyle = ocean;
  ctx.fillRect(0, horizon, w, h - horizon);

  ctx.lineWidth = Math.max(1, w * 0.0012);
  for (let i = 0; i < 24; i += 1) {
    const y = horizon + h * 0.035 + i * h * 0.026;
    const amplitude = 3 + i * 0.32;
    const speed = now * (0.00022 + i * 0.000003);
    ctx.beginPath();
    for (let x = -30; x <= w + 30; x += 18) {
      const wave = Math.sin(x * 0.017 + speed + i * 0.8) * amplitude;
      if (x === -30) {
        ctx.moveTo(x, y + wave);
      } else {
        ctx.lineTo(x, y + wave);
      }
    }
    ctx.strokeStyle = i % 3 === 0 ? "rgba(189, 225, 219, 0.22)" : "rgba(55, 136, 144, 0.18)";
    ctx.stroke();
  }
}

function renderBridgeOptics() {
  const w = canvas.width;
  const h = canvas.height;
  const cx = w / 2;
  const cy = h / 2;
  const radius = w * 0.485;

  ctx.strokeStyle = "rgba(229, 242, 238, 0.18)";
  ctx.lineWidth = w * 0.002;
  for (let i = -2; i <= 2; i += 1) {
    const y = cy + i * h * 0.092;
    ctx.beginPath();
    ctx.moveTo(cx - radius * 0.54, y);
    ctx.lineTo(cx + radius * 0.54, y);
    ctx.stroke();
  }

  ctx.strokeStyle = "rgba(216, 180, 106, 0.42)";
  ctx.lineWidth = w * 0.003;
  ctx.beginPath();
  ctx.arc(cx, cy, radius * 0.76, Math.PI * 1.15, Math.PI * 1.85);
  ctx.stroke();

  for (let i = -3; i <= 3; i += 1) {
    const angle = -Math.PI / 2 + i * 0.14;
    const inner = radius * 0.72;
    const outer = radius * (i === 0 ? 0.84 : 0.79);
    ctx.beginPath();
    ctx.moveTo(cx + Math.cos(angle) * inner, cy + Math.sin(angle) * inner);
    ctx.lineTo(cx + Math.cos(angle) * outer, cy + Math.sin(angle) * outer);
    ctx.stroke();
  }
}

function renderContact(contact) {
  if (!contact.visible) return;
  const w = canvas.width;
  const h = canvas.height;
  const x = contact.x * w;
  const y = contact.y * h;
  const hull = w * 0.032 * contact.scale;
  const mast = w * 0.035 * contact.scale;

  ctx.save();
  ctx.translate(x, y);
  ctx.strokeStyle = contact.color;
  ctx.fillStyle = contact.color;
  ctx.lineWidth = Math.max(1.5, w * 0.002);

  ctx.beginPath();
  ctx.moveTo(-hull, 0);
  ctx.lineTo(hull * 0.74, 0);
  ctx.lineTo(hull * 0.42, hull * 0.34);
  ctx.lineTo(-hull * 0.72, hull * 0.34);
  ctx.closePath();
  ctx.fill();

  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(0, -mast);
  ctx.moveTo(-hull * 0.42, -mast * 0.42);
  ctx.lineTo(hull * 0.5, -mast * 0.42);
  ctx.stroke();

  ctx.fillStyle = "rgba(4, 9, 11, 0.7)";
  ctx.strokeStyle = "rgba(226, 240, 236, 0.25)";
  const labelWidth = Math.max(w * 0.19, 130);
  const labelHeight = 58;
  const labelX = clamp(16, -x + 24, w - x - labelWidth - 24);
  const labelY = -mast - labelHeight - 16;
  ctx.fillRect(labelX, labelY, labelWidth, labelHeight);
  ctx.strokeRect(labelX, labelY, labelWidth, labelHeight);

  ctx.fillStyle = contact.color;
  ctx.font = `${Math.max(11, w * 0.014)}px Segoe UI, sans-serif`;
  ctx.fillText(contact.callsign, labelX + 10, labelY + 18);
  ctx.fillStyle = "rgba(232, 240, 237, 0.9)";
  ctx.font = `${Math.max(10, w * 0.012)}px Segoe UI, sans-serif`;
  ctx.fillText(`Bearing ${formatBearing(contact.bearing)}`, labelX + 10, labelY + 35);
  ctx.fillText(`Range ${contact.range.toFixed(1)} nm`, labelX + 10, labelY + 50);
  ctx.restore();
}

function updateBearingBand() {
  const marks = [];
  for (let offset = -30; offset <= 30; offset += 10) {
    marks.push(`<span>${formatBearing(state.bearing + offset)}</span>`);
  }
  bearingBand.innerHTML = marks.join("");
}

function updateContactStrip(contacts) {
  if (!state.contactButtonsReady) {
    contactStrip.innerHTML = vessels.map((vessel) => `<button class="contact-card" type="button" data-vessel-id="${vessel.id}">
      <strong>${vessel.callsign}</strong>
      <span>Standing by</span>
    </button>`).join("");
    state.contactButtonsReady = true;
  }

  contacts.forEach((contact) => {
    const button = contactStrip.querySelector(`[data-vessel-id="${contact.id}"]`);
    if (!button) return;
    const status = contact.visible ? "In field" : `${formatBearing(contact.bearing)} / ${contact.range.toFixed(1)} nm`;
    button.classList.toggle("is-visible", contact.visible);
    button.querySelector("strong").textContent = contact.callsign;
    button.querySelector("span").textContent = status;
  });
}

function updateDetailsButton() {
  const nearest = state.visibleContacts
    .sort((a, b) => Math.abs(a.relative) - Math.abs(b.relative))[0];
  if (!nearest) {
    detailsButton.hidden = true;
    detailsButton.dataset.vesselId = "";
    return;
  }
  detailsButton.hidden = false;
  detailsButton.dataset.vesselId = nearest.id;
}

function selectVessel(contact) {
  if (!contact) return;
  state.selectedId = contact.id;
  panelEmpty.hidden = true;
  panelContent.hidden = false;
  panelCallsign.textContent = contact.callsign;
  panelName.textContent = contact.name;
  panelMission.textContent = contact.mission;
  panelStatus.textContent = contact.status;
  panelReport.textContent = contact.report;
  panelBearing.textContent = formatBearing(contact.bearing);
  panelRange.textContent = `${contact.range.toFixed(1)} nm`;
}

function updateSelectedPanel(contacts) {
  if (!state.selectedId) return;
  const contact = contacts.find((item) => item.id === state.selectedId);
  if (contact) {
    selectVessel(contact);
  }
}

function render(now) {
  resizeCanvas();

  if (!state.dragging) {
    state.targetBearing = normalizeDegrees(state.targetBearing + state.velocity);
    state.velocity *= 0.94;
    if (Math.abs(state.velocity) < 0.003) state.velocity = 0;
  }
  state.bearing = normalizeDegrees(state.bearing + shortestDelta(state.bearing, state.targetBearing) * 0.13);

  renderOcean(now);
  renderBridgeOptics();
  const contacts = vessels.map((vessel) => projectContact(vesselState(vessel, now / 1000)));
  state.visibleContacts = contacts.filter((contact) => contact.visible);
  contacts.forEach(renderContact);

  bearingReadout.textContent = formatBearing(state.bearing);
  updateBearingBand();
  updateContactStrip(contacts);
  updateDetailsButton();
  updateSelectedPanel(contacts);

  requestAnimationFrame(render);
}

function pointerX(event) {
  return event.clientX ?? event.touches?.[0]?.clientX ?? 0;
}

frame.addEventListener("pointerdown", (event) => {
  frame.setPointerCapture(event.pointerId);
  state.dragging = true;
  state.lastX = pointerX(event);
  state.lastTime = performance.now();
  state.velocity = 0;
});

frame.addEventListener("pointermove", (event) => {
  if (!state.dragging) return;
  const x = pointerX(event);
  const now = performance.now();
  const dx = x - state.lastX;
  const dt = Math.max(16, now - state.lastTime);
  const deltaBearing = dx * -0.18;
  state.targetBearing = normalizeDegrees(state.targetBearing + deltaBearing);
  state.velocity = deltaBearing * (16 / dt);
  state.lastX = x;
  state.lastTime = now;
});

frame.addEventListener("pointerup", (event) => {
  state.dragging = false;
  frame.releasePointerCapture(event.pointerId);
});

frame.addEventListener("pointercancel", () => {
  state.dragging = false;
});

frame.addEventListener("click", (event) => {
  const rect = canvas.getBoundingClientRect();
  const x = (event.clientX - rect.left) / rect.width;
  const y = (event.clientY - rect.top) / rect.height;
  const contact = state.visibleContacts
    .map((item) => ({ item, distance: Math.hypot(item.x - x, item.y - y) }))
    .filter(({ distance }) => distance < 0.14)
    .sort((a, b) => a.distance - b.distance)[0]?.item;
  if (contact) selectVessel(contact);
});

detailsButton.addEventListener("click", () => {
  const contact = state.visibleContacts.find((item) => item.id === detailsButton.dataset.vesselId);
  selectVessel(contact);
});

contactStrip.addEventListener("click", (event) => {
  const button = event.target.closest("[data-vessel-id]");
  if (!button) return;
  const contact = vessels
    .map((vessel) => projectContact(vesselState(vessel, performance.now() / 1000)))
    .find((item) => item.id === button.dataset.vesselId);
  selectVessel(contact);
});

window.addEventListener("resize", resizeCanvas);
resizeCanvas();
requestAnimationFrame(render);
