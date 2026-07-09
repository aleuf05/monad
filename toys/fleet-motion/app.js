const HOME = { lat: 26.56, lng: 56.25 };
const BASE_SPEED_KMH = 180;
const TRAIL_LIMIT = 180;
const LOG_LIMIT = 9;
const FORMATION = [
  { id: "escort-alpha", name: "ESCORT ALPHA", lat: -0.22, lng: -0.32 },
  { id: "escort-bravo", name: "ESCORT BRAVO", lat: -0.22, lng: 0.32 },
  { id: "escort-charlie", name: "ESCORT CHARLIE", lat: 0.28, lng: 0 }
];

const map = L.map("map", {
  center: [HOME.lat, HOME.lng],
  zoom: 7,
  minZoom: 3,
  worldCopyJump: true
});

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap contributors"
}).addTo(map);

function shipIcon(kind, selected = false) {
  const size = kind === "flagship" ? 32 : 24;
  const selectedClass = selected ? " selected" : "";
  return L.divIcon({
    className: "fleet-dot",
    html: `<span class="ship-dot ${kind}${selectedClass}"></span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2]
  });
}

const courseLine = L.polyline([], {
  color: "#0d8192",
  weight: 3,
  opacity: 0.9,
  dashArray: "10 8"
}).addTo(map);

const trailStyle = {
  color: "#25d9e8",
  weight: 2,
  opacity: 0.62,
  className: "fleet-trail"
};

const flagshipMarker = L.marker([HOME.lat, HOME.lng], {
  icon: shipIcon("flagship", true),
  title: "MONAD"
})
  .bindTooltip("MONAD", { permanent: true, direction: "top", offset: [0, -18] })
  .addTo(map);

const escortMarkers = FORMATION.map((escort) =>
  L.marker([HOME.lat + escort.lat, HOME.lng + escort.lng], {
    icon: shipIcon("escort"),
    title: escort.name
  })
    .bindTooltip(escort.name, { direction: "top", offset: [0, -14] })
    .addTo(map)
);

const trails = [
  L.polyline([], { ...trailStyle, color: "#e8b95d", opacity: 0.74 }).addTo(map),
  ...FORMATION.map(() => L.polyline([], trailStyle).addTo(map))
];

const currentPosition = document.querySelector("#currentPosition");
const destinationPosition = document.querySelector("#destinationPosition");
const distanceValue = document.querySelector("#distanceValue");
const motionStatus = document.querySelector("#motionStatus");
const speedValue = document.querySelector("#speedValue");
const warpValue = document.querySelector("#warpValue");
const pauseButton = document.querySelector("#pauseButton");
const homeButton = document.querySelector("#homeButton");
const resetButton = document.querySelector("#resetButton");
const warpButtons = document.querySelectorAll(".warp-button");
const shipInfoHeading = document.querySelector("#shipInfoHeading");
const shipPosition = document.querySelector("#shipPosition");
const shipSpeed = document.querySelector("#shipSpeed");
const shipHeading = document.querySelector("#shipHeading");
const shipStatus = document.querySelector("#shipStatus");
const shipDestination = document.querySelector("#shipDestination");
const captainsLog = document.querySelector("#captainsLog");

let flagship = { ...HOME };
let destination = null;
let timeWarp = 1;
let lastMovingWarp = 1;
let selectedShipId = "monad";
let previousFrame;
let lastStatus = "Holding";
let headingDegrees = null;
let logEntries = [];
let shipTrails = [];

function createInitialTrails() {
  shipTrails = [
    [[HOME.lat, HOME.lng]],
    ...FORMATION.map((escort) => [[HOME.lat + escort.lat, HOME.lng + escort.lng]])
  ];
}

function toRadians(degrees) {
  return degrees * (Math.PI / 180);
}

function toDegrees(radians) {
  return radians * (180 / Math.PI);
}

function distanceKm(start, end) {
  const earthRadiusKm = 6371;
  const latitudeDelta = toRadians(end.lat - start.lat);
  const longitudeDelta = toRadians(end.lng - start.lng);
  const startLatitude = toRadians(start.lat);
  const endLatitude = toRadians(end.lat);
  const haversine =
    Math.sin(latitudeDelta / 2) ** 2 +
    Math.cos(startLatitude) *
      Math.cos(endLatitude) *
      Math.sin(longitudeDelta / 2) ** 2;
  return earthRadiusKm * 2 * Math.atan2(Math.sqrt(haversine), Math.sqrt(1 - haversine));
}

function bearingDegrees(start, end) {
  const startLatitude = toRadians(start.lat);
  const endLatitude = toRadians(end.lat);
  const longitudeDelta = toRadians(end.lng - start.lng);
  const y = Math.sin(longitudeDelta) * Math.cos(endLatitude);
  const x =
    Math.cos(startLatitude) * Math.sin(endLatitude) -
    Math.sin(startLatitude) * Math.cos(endLatitude) * Math.cos(longitudeDelta);
  return (toDegrees(Math.atan2(y, x)) + 360) % 360;
}

function formatPosition(position) {
  return `${position.lat.toFixed(4)}, ${position.lng.toFixed(4)}`;
}

function formatEta(distance) {
  const effectiveSpeed = BASE_SPEED_KMH * Math.max(timeWarp, 1);
  const totalMinutes = Math.ceil((distance / effectiveSpeed) * 60);
  if (totalMinutes < 1) {
    return "<1 min";
  }
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return hours ? `${hours}h ${minutes}m` : `${minutes}m`;
}

function currentStatus() {
  if (destination && timeWarp > 0) {
    return "Underway";
  }
  if (lastStatus === "Arrived") {
    return "Arrived";
  }
  return "Holding";
}

function getShipPosition(id) {
  if (id === "monad") {
    return { ...flagship };
  }
  const escort = FORMATION.find((ship) => ship.id === id) || FORMATION[0];
  return { lat: flagship.lat + escort.lat, lng: flagship.lng + escort.lng };
}

function getSelectedShip() {
  if (selectedShipId === "monad") {
    return { id: "monad", name: "MONAD", kind: "flagship", position: getShipPosition("monad") };
  }
  const escort = FORMATION.find((ship) => ship.id === selectedShipId) || FORMATION[0];
  return {
    id: escort.id,
    name: escort.name,
    kind: "escort",
    position: getShipPosition(escort.id)
  };
}

function addTrailPoint(index, position) {
  const trail = shipTrails[index];
  const last = trail[trail.length - 1];
  if (!last || Math.abs(last[0] - position.lat) > 0.0003 || Math.abs(last[1] - position.lng) > 0.0003) {
    trail.push([position.lat, position.lng]);
    if (trail.length > TRAIL_LIMIT) {
      trail.shift();
    }
  }
}

function syncTrails() {
  addTrailPoint(0, flagship);
  FORMATION.forEach((escort, index) => {
    addTrailPoint(index + 1, {
      lat: flagship.lat + escort.lat,
      lng: flagship.lng + escort.lng
    });
  });
  trails.forEach((trail, index) => trail.setLatLngs(shipTrails[index]));
}

function updateMarkerIcons() {
  flagshipMarker.setIcon(shipIcon("flagship", selectedShipId === "monad"));
  escortMarkers.forEach((marker, index) => {
    marker.setIcon(shipIcon("escort", selectedShipId === FORMATION[index].id));
  });
}

function updateFleetMarkers() {
  flagshipMarker.setLatLng([flagship.lat, flagship.lng]);
  escortMarkers.forEach((marker, index) => {
    const offset = FORMATION[index];
    marker.setLatLng([flagship.lat + offset.lat, flagship.lng + offset.lng]);
  });

  courseLine.setLatLngs(
    destination
      ? [
          [flagship.lat, flagship.lng],
          [destination.lat, destination.lng]
        ]
      : []
  );
  syncTrails();
}

function addLog(message) {
  const timestamp = new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
  logEntries.unshift({ timestamp, message });
  logEntries = logEntries.slice(0, LOG_LIMIT);
  captainsLog.innerHTML = logEntries
    .map((entry) => `<li><time>${entry.timestamp}</time>${entry.message}</li>`)
    .join("");
}

function updateShipInfo() {
  const selected = getSelectedShip();
  const status = currentStatus();
  const speed = destination && timeWarp > 0
    ? `${BASE_SPEED_KMH * timeWarp} km/h sim`
    : "0 km/h sim";

  shipInfoHeading.textContent = selected.name;
  shipPosition.textContent = formatPosition(selected.position);
  shipSpeed.textContent = speed;
  shipHeading.textContent = headingDegrees === null ? "--" : `${Math.round(headingDegrees)} deg`;
  shipStatus.textContent = status;
  shipDestination.textContent = destination ? formatPosition(destination) : "No course set";
}

function updateWarpControls() {
  warpValue.textContent = timeWarp === 0 ? "Paused" : `${timeWarp}x`;
  warpButtons.forEach((button) => {
    button.classList.toggle("active", Number(button.dataset.warp) === timeWarp);
  });
  pauseButton.textContent = timeWarp === 0 ? "Resume" : "Pause";
}

function updateStatus() {
  const status = currentStatus();
  currentPosition.textContent = formatPosition(flagship);
  destinationPosition.textContent = destination
    ? formatPosition(destination)
    : "No course set";
  speedValue.textContent =
    destination && timeWarp > 0 ? `${BASE_SPEED_KMH * timeWarp} km/h sim` : "0 km/h sim";

  if (destination) {
    const remaining = distanceKm(flagship, destination);
    distanceValue.textContent = timeWarp === 0
      ? `${remaining.toFixed(1)} km / paused`
      : `${remaining.toFixed(1)} km / ${formatEta(remaining)}`;
  } else {
    distanceValue.textContent = "--";
  }

  motionStatus.textContent = status;
  motionStatus.classList.toggle("underway", status === "Underway");
  motionStatus.classList.toggle("arrived", status === "Arrived");
  pauseButton.disabled = !destination && timeWarp !== 0;
  updateWarpControls();
  updateMarkerIcons();
  updateShipInfo();
}

function setDestination(position) {
  destination = { lat: position.lat, lng: position.lng };
  headingDegrees = bearingDegrees(flagship, destination);
  lastStatus = "Underway";
  if (timeWarp === 0) {
    timeWarp = lastMovingWarp;
  }
  addLog(`Destination set: ${formatPosition(destination)}.`);
  addLog("Fleet starts underway.");
  updateFleetMarkers();
  updateStatus();
}

function arrive() {
  flagship = { ...destination };
  destination = null;
  lastStatus = "Arrived";
  addLog(`MONAD arrived at ${formatPosition(flagship)}.`);
  updateFleetMarkers();
  updateStatus();
}

function advanceFleet(elapsedSeconds) {
  if (!destination || timeWarp === 0) {
    return;
  }

  const remaining = distanceKm(flagship, destination);
  const stepDistance = BASE_SPEED_KMH * timeWarp * (elapsedSeconds / 3600);
  if (stepDistance >= remaining) {
    arrive();
    return;
  }

  const ratio = stepDistance / remaining;
  flagship.lat += (destination.lat - flagship.lat) * ratio;
  flagship.lng += (destination.lng - flagship.lng) * ratio;
  headingDegrees = bearingDegrees(flagship, destination);
  updateFleetMarkers();
  updateStatus();
}

function animationFrame(timestamp) {
  if (previousFrame === undefined) {
    previousFrame = timestamp;
  }
  const elapsedSeconds = Math.min((timestamp - previousFrame) / 1000, 0.25);
  previousFrame = timestamp;
  advanceFleet(elapsedSeconds);
  window.requestAnimationFrame(animationFrame);
}

function setTimeWarp(nextWarp) {
  const previousWarp = timeWarp;
  timeWarp = nextWarp;
  if (nextWarp > 0) {
    lastMovingWarp = nextWarp;
  }
  if (nextWarp === 0 && previousWarp !== 0) {
    addLog("Simulation paused.");
  } else if (previousWarp === 0 && nextWarp > 0) {
    addLog(`Simulation resumed at ${nextWarp}x.`);
  } else if (previousWarp !== nextWarp) {
    addLog(`Time warp changed to ${nextWarp}x.`);
  }
  updateStatus();
}

function resetFleet() {
  flagship = { ...HOME };
  destination = null;
  timeWarp = 1;
  lastMovingWarp = 1;
  selectedShipId = "monad";
  previousFrame = undefined;
  lastStatus = "Holding";
  headingDegrees = null;
  createInitialTrails();
  addLog("Fleet reset to Strait of Hormuz station.");
  updateFleetMarkers();
  updateStatus();
  map.setView([HOME.lat, HOME.lng], 7);
}

function selectShip(id) {
  selectedShipId = id;
  updateStatus();
}

map.on("click", (event) => setDestination(event.latlng));
flagshipMarker.on("click", (event) => {
  L.DomEvent.stopPropagation(event);
  selectShip("monad");
});
escortMarkers.forEach((marker, index) => {
  marker.on("click", (event) => {
    L.DomEvent.stopPropagation(event);
    selectShip(FORMATION[index].id);
  });
});

pauseButton.addEventListener("click", () => {
  setTimeWarp(timeWarp === 0 ? lastMovingWarp : 0);
});

warpButtons.forEach((button) => {
  button.addEventListener("click", () => setTimeWarp(Number(button.dataset.warp)));
});

homeButton.addEventListener("click", () => {
  setDestination(HOME);
  map.panTo([HOME.lat, HOME.lng]);
});

resetButton.addEventListener("click", resetFleet);

createInitialTrails();
addLog("Fleet motion toy online. Captain's Log uses local browser time.");
updateFleetMarkers();
updateStatus();
window.requestAnimationFrame(animationFrame);
