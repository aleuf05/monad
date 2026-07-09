const fallbackFleet = {
  map: {
    center: [26.56, 56.25],
    zoom: 6,
    status: {
      ao: "Strait of Hormuz",
      conn: "Captain T",
      watch: "Persistent"
    }
  },
  markers: [
    {
      id: "monad",
      name: "MONAD FLAGSHIP",
      type: "flagship",
      position: [26.32, 56.05],
      status: "FORMING",
      detail: "Cognitive operations vessel",
      signal: "AIS simulated"
    },
    {
      id: "gantry",
      name: "GANTRY",
      type: "vessel",
      position: [25.68, 55.18],
      status: "STANDBY",
      detail: "Development yard / workstation",
      signal: "Codex bounded"
    },
    {
      id: "granite",
      name: "GRANITE",
      type: "vessel",
      position: [26.08, 56.84],
      status: "ONLINE",
      detail: "Engine-room server",
      signal: "Caddy verified"
    },
    {
      id: "hormuz",
      name: "STRAIT OF HORMUZ",
      type: "station",
      position: [26.56, 56.25],
      status: "WATCHLIST",
      detail: "Area of operations",
      signal: "Passage monitored"
    },
    {
      id: "persian-gulf",
      name: "PERSIAN GULF",
      type: "area",
      position: [26.72, 52.62],
      status: "WATCHLIST",
      detail: "Regional operating area",
      signal: "Simulated theater marker"
    }
  ],
  vessels: [
    {
      id: "gantry",
      name: "GANTRY",
      hull: "FFG-01",
      role: "Development yard / workstation",
      status: "STANDBY",
      mission: "Builds repo changes and Codex tasks",
      signal: "Codex bounded"
    },
    {
      id: "granite",
      name: "GRANITE",
      hull: "DDG-02",
      role: "Engine-room server",
      status: "ONLINE",
      mission: "Serves Monad over LAN",
      signal: "Caddy verified / HTTP 200"
    },
    {
      id: "monad",
      name: "MONAD",
      hull: "FLAGSHIP",
      role: "Cognitive operations vessel",
      status: "FORMING",
      mission: "Coordinates intent, machines, memory, agents, and artifacts",
      signal: "Public live"
    }
  ],
  missions: [
    "Fleet Map MVP commissioned",
    "Simulated Strait of Hormuz watch active",
    "Live AIS integration held for future review"
  ]
};

const statusClass = {
  ONLINE: "status-online",
  STANDBY: "status-standby",
  DOCKED: "status-docked",
  FORMING: "status-forming",
  WATCHLIST: "status-watchlist"
};

const markerLayers = new Map();
const contactRecords = new Map();
let fleetMap;
let monadMarker;
let selectedContactId;

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function badge(status) {
  const safeStatus = escapeHtml(status);
  return `<span class="status-badge ${statusClass[status] || ""}">${safeStatus}</span>`;
}

function contactIcon(type) {
  const safeType = ["flagship", "station", "area"].includes(type) ? type : "vessel";
  return L.divIcon({
    className: "fleet-contact-icon",
    html: `<span class="contact-marker ${safeType}"></span>`,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -20]
  });
}

function popupContent(contact) {
  return `
    <div class="contact-popup">
      <p class="label">${escapeHtml(contact.type)} / ${escapeHtml(contact.status)}</p>
      <h3>${escapeHtml(contact.name)}</h3>
      <p>${escapeHtml(contact.detail)}</p>
      <p><strong>Signal:</strong> ${escapeHtml(contact.signal)}</p>
      <p><strong>Position:</strong> ${contact.position.map(Number).join(", ")}</p>
    </div>
  `;
}

function renderStatusPanel(status) {
  document.querySelector("#aoStatus").textContent = status.ao;
  document.querySelector("#connStatus").textContent = status.conn;
  document.querySelector("#watchStatus").textContent = status.watch;
}

function renderMap(data) {
  if (typeof L === "undefined") {
    document.querySelector("#fleetMap").textContent = "MAP SYSTEM UNAVAILABLE";
    return;
  }

  fleetMap = L.map("fleetMap", {
    center: data.map.center,
    zoom: data.map.zoom,
    minZoom: 4,
    maxZoom: 12,
    zoomControl: true,
    attributionControl: true
  });

  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  }).addTo(fleetMap);

  data.markers.forEach((contact) => {
    contactRecords.set(contact.id, contact);
    const marker = L.marker(contact.position, {
      icon: contactIcon(contact.type),
      title: contact.name,
      alt: `${contact.name}, simulated position`
    })
      .bindPopup(popupContent(contact))
      .bindTooltip(contact.name, {
        direction: "top",
        offset: [0, -18]
      })
      .addTo(fleetMap);

    marker.on("click", () => selectContact(contact.id));
    markerLayers.set(contact.id, marker);
    if (contact.id === "monad") {
      monadMarker = marker;
    }
  });
}

function renderRoster(data) {
  const rosterBody = document.querySelector("#rosterBody");
  const missionList = document.querySelector("#missionList");

  rosterBody.innerHTML = data.vessels.map((vessel) => `
    <tr data-contact-id="${escapeHtml(vessel.id)}">
      <td>
        <button
          class="roster-contact-button"
          type="button"
          data-select-contact="${escapeHtml(vessel.id)}"
        >${escapeHtml(vessel.name)}</button>
      </td>
      <td>${escapeHtml(vessel.hull)}</td>
      <td>${escapeHtml(vessel.role)}</td>
      <td>${badge(vessel.status)}</td>
      <td>${escapeHtml(vessel.mission)}</td>
      <td>${escapeHtml(vessel.signal)}</td>
    </tr>
  `).join("");

  missionList.innerHTML = data.missions
    .map((mission) => `<li>${escapeHtml(mission)}</li>`)
    .join("");

  rosterBody.querySelectorAll("[data-select-contact]").forEach((button) => {
    button.addEventListener("click", () => {
      selectContact(button.dataset.selectContact, true);
    });
  });
}

function clearContactSelection() {
  if (selectedContactId) {
    markerLayers.get(selectedContactId)?.getElement()?.classList.remove("is-selected");
    document
      .querySelector(`tr[data-contact-id="${selectedContactId}"]`)
      ?.classList.remove("is-selected");
  }

  selectedContactId = undefined;
  document.querySelector("#contactPanel").hidden = true;
}

function selectContact(contactId, centerMap = false) {
  const contact = contactRecords.get(contactId);
  const marker = markerLayers.get(contactId);
  if (!contact || !marker || !fleetMap.hasLayer(marker)) {
    return;
  }

  clearContactSelection();
  selectedContactId = contactId;
  marker.getElement()?.classList.add("is-selected");
  document
    .querySelector(`tr[data-contact-id="${contactId}"]`)
    ?.classList.add("is-selected");

  document.querySelector("#contactType").textContent =
    `${contact.type} / ${contact.status}`;
  document.querySelector("#contactName").textContent = contact.name;
  document.querySelector("#contactRole").textContent = contact.detail;
  document.querySelector("#contactStatus").textContent = contact.status;
  document.querySelector("#contactPosition").textContent =
    contact.position.map((coordinate) => Number(coordinate).toFixed(3)).join(", ");
  document.querySelector("#contactSignal").textContent = contact.signal;
  document.querySelector("#contactPanel").hidden = false;

  if (centerMap) {
    centerSelectedContact();
  }
}

function centerSelectedContact() {
  const contact = contactRecords.get(selectedContactId);
  if (!contact || !fleetMap) {
    return;
  }
  fleetMap.flyTo(contact.position, Math.max(fleetMap.getZoom(), 8), {
    duration: 0.6
  });
}

function setAisState(enabled) {
  const status = document.querySelector("#aisStatus");
  status.textContent = enabled ? "ON" : "OFF";

  if (!fleetMap || !monadMarker) {
    return;
  }
  if (enabled && !fleetMap.hasLayer(monadMarker)) {
    monadMarker.addTo(fleetMap);
  }
  if (!enabled && fleetMap.hasLayer(monadMarker)) {
    fleetMap.removeLayer(monadMarker);
    if (selectedContactId === "monad") {
      clearContactSelection();
    }
  }
}

function renderFleet(data) {
  renderStatusPanel(data.map.status);
  renderMap(data);
  renderRoster(data);

  const aisToggle = document.querySelector("#aisToggle");
  setAisState(aisToggle.checked);
  aisToggle.addEventListener("change", () => setAisState(aisToggle.checked));
  document.querySelector("#closeContact").addEventListener("click", clearContactSelection);
  document.querySelector("#centerContact").addEventListener("click", centerSelectedContact);
}

fetch("fleet.json?v=2")
  .then((response) => {
    if (!response.ok) {
      throw new Error(`Fleet status unavailable: ${response.status}`);
    }
    return response.json();
  })
  .then(renderFleet)
  .catch(() => renderFleet(fallbackFleet));
