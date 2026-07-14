import {
  createPeriscopeState,
  currentContacts,
  currentOptics,
  formatBearing,
  projectContact,
  selectVessel,
  autoAcquireSharedContact,
  tickBearing,
  focusContactForOptics,
  OPTICS_TIERS,
} from "./state.js";
import { createPeriscopeScene } from "./scene.js";
import { resolveDuckContactVisual } from "./duck.js";

const canvas = document.querySelector("#periscopeCanvas");
const overlayCanvas = document.querySelector("#periscopeOverlay");
const frame = document.querySelector("#scopeFrame");
const bearingReadout = document.querySelector("#bearingReadout");
const dataSourceReadout = document.querySelector("#dataSourceReadout");
const bearingBand = document.querySelector("#bearingBand");
const contactStrip = document.querySelector("#contactStrip");
const detailsButton = document.querySelector("#detailsButton");
const fieldNote = document.querySelector("#fieldNote");
const magnificationReadout = document.querySelector("#magnificationReadout");
const lightReadout = document.querySelector("#lightReadout");
const magnificationButtons = Array.from(document.querySelectorAll("[data-magnification]"));
const panelEmpty = document.querySelector("#panelEmpty");
const panelContent = document.querySelector("#panelContent");
const panelCallsign = document.querySelector("#panelCallsign");
const panelName = document.querySelector("#panelName");
const panelMission = document.querySelector("#panelMission");
const panelStatus = document.querySelector("#panelStatus");
const panelReport = document.querySelector("#panelReport");
const panelBearing = document.querySelector("#panelBearing");
const panelRange = document.querySelector("#panelRange");

const periscope = createPeriscopeState();
const scene = createPeriscopeScene({ canvas, overlayCanvas });
scene.setContactVisualResolver(resolveDuckContactVisual);

let latestContacts = [];
let contactButtonsReady = false;
let contactSourceKey = "";

function pointerX(event) {
  return event.clientX ?? event.touches?.[0]?.clientX ?? 0;
}

function updateBearingBand() {
  const marks = [];
  const optics = currentOptics(periscope);
  const half = Math.ceil(optics.fov / 2 / 5) * 5;
  const step = optics.fov <= 16 ? 5 : 10;
  for (let offset = -half; offset <= half; offset += step) {
    marks.push(`<span>${formatBearing(periscope.bearing + offset)}</span>`);
  }
  bearingBand.innerHTML = marks.join("");
}

function updateOpticsControls() {
  const optics = currentOptics(periscope);
  if (magnificationReadout) magnificationReadout.textContent = optics.label;
  magnificationButtons.forEach((button) => {
    const active = button.dataset.magnification === optics.id;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
}

function setOpticsMode(mode) {
  if (!OPTICS_TIERS[mode] || periscope.opticsMode === mode) return;
  periscope.opticsMode = mode;
  focusContactForOptics(periscope, latestContacts);
  updateOpticsControls();
}

function updateContactStrip(contacts) {
  const sourceKey = contacts.map((contact) => contact.id).join("|");
  if (!contactButtonsReady || contactSourceKey !== sourceKey) {
    contactStrip.innerHTML = contacts
      .map(
        (contact) => `<button class="contact-card" type="button" data-vessel-id="${contact.id}">
      <strong>${contact.callsign}</strong>
      <span>Standing by</span>
    </button>`
      )
      .join("");
    contactButtonsReady = true;
    contactSourceKey = sourceKey;
  }

  contacts.forEach((contact) => {
    const button = contactStrip.querySelector(`[data-vessel-id="${contact.id}"]`);
    if (!button) return;
    const status = contact.visible ? "In field" : `${formatBearing(contact.bearing)} / ${contact.range.toFixed(1)} nm`;
    button.classList.toggle("is-visible", contact.visible);
    button.classList.toggle("is-selected", periscope.selectedId === contact.id);
    button.querySelector("strong").textContent = contact.callsign;
    button.querySelector("span").textContent = status;
  });
}

function updateDetailsButton() {
  const nearest = periscope.visibleContacts.slice().sort((a, b) => Math.abs(a.relative) - Math.abs(b.relative))[0];
  if (!nearest) {
    detailsButton.hidden = true;
    detailsButton.dataset.vesselId = "";
    return;
  }
  detailsButton.hidden = false;
  detailsButton.dataset.vesselId = nearest.id;
}

function syncSelectedPanel(contacts) {
  const contact = contacts.find((item) => item.id === periscope.selectedId);
  if (!contact) return;
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

function updateFieldNote() {
  if (!fieldNote) return;
  const cue = periscope.acquisitionCue;
  const cueAge = performance.now() - cue.startedAt;
  if (cue.contactId && cueAge >= 0 && cueAge < 2400) {
    fieldNote.textContent = cue.label;
    fieldNote.classList.add("is-acquiring");
    return;
  }
  const selected = periscope.visibleContacts.find((contact) => contact.id === periscope.selectedId);
  if (selected) {
    fieldNote.textContent = `Tracking ${selected.callsign}`;
  } else {
    fieldNote.textContent = "Drag to rotate bearing";
  }
  fieldNote.classList.toggle("is-acquiring", Boolean(selected));
}

function updateDataSourceIndicator() {
  if (!dataSourceReadout) return;
  if (periscope.dataSource === "fleetcore-live") {
    dataSourceReadout.textContent = "FleetCore Live";
    dataSourceReadout.classList.add("is-live");
  } else if (periscope.dataSource) {
    dataSourceReadout.textContent = "Fleet Motion (Local Sim)";
    dataSourceReadout.classList.remove("is-live");
  } else {
    dataSourceReadout.textContent = "Local Demo";
    dataSourceReadout.classList.remove("is-live");
  }
}

function selectContactById(id, options) {
  const contact = latestContacts.find((item) => item.id === id);
  if (contact) selectVessel(periscope, contact, options);
}

function render(now) {
  tickBearing(periscope);
  periscope.optics = currentOptics(periscope);

  const rawContacts = currentContacts(periscope, now / 1000, now);
  autoAcquireSharedContact(periscope, rawContacts);
  const contacts = rawContacts.map((contact) => projectContact(periscope, contact));
  latestContacts = contacts;
  periscope.visibleContacts = contacts.filter((contact) => contact.visible);

  scene.render(periscope, contacts, now);
  if (lightReadout) lightReadout.textContent = scene.getDaylightLabel();

  bearingReadout.textContent = formatBearing(periscope.bearing);
  updateBearingBand();
  updateContactStrip(contacts);
  updateDetailsButton();
  syncSelectedPanel(contacts);
  updateFieldNote();
  updateDataSourceIndicator();

  requestAnimationFrame(render);
}

frame.addEventListener("pointerdown", (event) => {
  frame.setPointerCapture(event.pointerId);
  periscope.dragging = true;
  periscope.lastX = pointerX(event);
  periscope.lastTime = performance.now();
  periscope.velocity = 0;
});

frame.addEventListener("pointermove", (event) => {
  if (!periscope.dragging) return;
  const x = pointerX(event);
  const now = performance.now();
  const dx = x - periscope.lastX;
  const dt = Math.max(16, now - periscope.lastTime);
  const deltaBearing = dx * -0.18;
  periscope.targetBearing = (((periscope.targetBearing + deltaBearing) % 360) + 360) % 360;
  periscope.velocity = deltaBearing * (16 / dt);
  periscope.lastX = x;
  periscope.lastTime = now;
});

frame.addEventListener("pointerup", (event) => {
  periscope.dragging = false;
  frame.releasePointerCapture(event.pointerId);
});

frame.addEventListener("pointercancel", () => {
  periscope.dragging = false;
});

frame.addEventListener("click", (event) => {
  const id = scene.hitTest(event.clientX, event.clientY);
  if (id) selectContactById(id, { propagate: true });
});

detailsButton.addEventListener("click", () => {
  selectContactById(detailsButton.dataset.vesselId, { propagate: true });
});

magnificationButtons.forEach((button) => {
  button.addEventListener("click", () => setOpticsMode(button.dataset.magnification));
});

contactStrip.addEventListener("click", (event) => {
  const button = event.target.closest("[data-vessel-id]");
  if (!button) return;
  selectContactById(button.dataset.vesselId, { propagate: true });
});

// Bridge Station embeds this toy as one of three fixed-height Live Console
// panels; this toy's own page also runs standalone at full page height.
// See style.css's body.is-embedded rules for what actually changes.
try {
  if (window.self !== window.top) {
    document.body.classList.add("is-embedded");
  }
} catch (error) {
  // Cross-origin embedding would throw reading window.top; treat that the
  // same as embedded, since a same-origin check failing at all means this
  // definitely isn't the standalone top-level page.
  document.body.classList.add("is-embedded");
}

updateOpticsControls();
requestAnimationFrame(render);
