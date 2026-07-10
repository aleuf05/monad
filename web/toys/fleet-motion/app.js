const HOME = { lat: 26.56, lng: 56.25 };
const BASE_SPEED_KMH = 180;
const ARRIVAL_RADIUS_KM = 0.08;
const SLOWDOWN_DISTANCE_KM = 12;
const SPEED_RESPONSE_SECONDS = 0.9;
const HEADING_RESPONSE_SECONDS = 0.75;
const ESCORT_SPEED_MULTIPLIER = 1.18;
const ESCORT_SLOT_RADIUS_KM = 0.12;
const ESCORT_DRIFT_LAT = 0.035;
const ESCORT_DRIFT_LNG = 0.045;
const ESCORT_SLOT_RESPONSE_SECONDS = 0.7;
const THREAT_START = { lat: 26.42, lng: 57.18 };
const THREAT_SPEED_KMH = 240;
const THREAT_INTERCEPT_RADIUS_KM = 9;
const THREAT_BREACH_RADIUS_KM = 6;
const INTERNAL_FEATURES = {
  threatDrill: false
};
const TRAIL_LIMIT = 180;
const TRAIL_REDRAW_MIN_POINTS = 2;
const LOG_LIMIT = 9;
const INTRO_DURATION_MS = 4800;
const DESIGN_DEFAULTS = {
  flagshipSpeedKmh: BASE_SPEED_KMH,
  escortSpeedScale: 1,
  formationSpread: 1
};
const SCENARIO_PRESETS = {
  freeplay: {
    id: "freeplay",
    label: "Freeplay / Manual",
    variantName: "freeplay_manual",
    settings: { ...DESIGN_DEFAULTS },
    escortModeId: "loose",
    destination: null,
    waypoints: [],
    spawnThreat: false,
    notePrompt: "Manual sandbox. Tune parameters, click a destination, and record what changed."
  },
  hormuz_transit: {
    id: "hormuz_transit",
    label: "Hormuz Transit",
    variantName: "hormuz_transit",
    settings: {
      flagshipSpeedKmh: 180,
      escortSpeedScale: 1,
      formationSpread: 1
    },
    escortModeId: "loose",
    destination: { lat: 26.25, lng: 55.35 },
    waypoints: [],
    spawnThreat: false,
    notePrompt: "Baseline crossing. Judge whether the route and escort spacing are readable."
  },
  escort_screen_drill: {
    id: "escort_screen_drill",
    label: "Patrol Weave Review",
    variantName: "patrol_weave_review",
    settings: {
      flagshipSpeedKmh: 160,
      escortSpeedScale: 1.3,
      formationSpread: 1.25
    },
    escortModeId: "patrol",
    destination: { lat: 26.62, lng: 55.05 },
    waypoints: [],
    spawnThreat: false,
    notePrompt: "Patrol weave review. Judge whether escorts read as independent but coherent."
  },
  waypoint_threading: {
    id: "waypoint_threading",
    label: "Waypoint Threading",
    variantName: "waypoint_threading",
    settings: {
      flagshipSpeedKmh: 140,
      escortSpeedScale: 1.05,
      formationSpread: 0.75
    },
    escortModeId: "tight",
    destination: { lat: 26.35, lng: 57.25 },
    waypoints: [{ lat: 26.62, lng: 56.85 }],
    spawnThreat: false,
    notePrompt: "Waypoint route. Judge whether manual routing feels understandable and recoverable."
  }
};
const ESCORT_MODES = [
  {
    id: "tight",
    label: "Tight Screen",
    driftScale: 0.45,
    slotRadiusKm: 0.08,
    speedMultiplier: 1.05
  },
  {
    id: "loose",
    label: "Loose Screen",
    driftScale: 1,
    slotRadiusKm: 0.12,
    speedMultiplier: 1.18
  },
  {
    id: "patrol",
    label: "Patrol Weave",
    driftScale: 1.75,
    slotRadiusKm: 0.18,
    speedMultiplier: 1.3
  }
];
const FORMATION = [
  { id: "escort-alpha", name: "ESCORT ALPHA", lat: -0.22, lng: -0.32 },
  { id: "escort-bravo", name: "ESCORT BRAVO", lat: -0.02, lng: 0.38 },
  { id: "escort-charlie", name: "ESCORT CHARLIE", lat: 0.18, lng: 0.16 }
];
const LAND_ZONES = [
  {
    name: "Iranian Coast",
    south: 26.9,
    north: 27.75,
    west: 54.8,
    east: 57.4
  },
  {
    name: "Qeshm Island",
    south: 26.62,
    north: 26.98,
    west: 55.55,
    east: 56.25
  },
  {
    name: "Hormuz Island",
    south: 27.02,
    north: 27.16,
    west: 56.36,
    east: 56.55
  },
  {
    name: "Musandam Peninsula",
    south: 25.45,
    north: 26.35,
    west: 56.0,
    east: 56.7
  },
  {
    name: "UAE Coast",
    south: 24.65,
    north: 25.85,
    west: 54.1,
    east: 56.3
  }
];

const map = L.map("map", {
  center: [HOME.lat, HOME.lng],
  zoom: 7,
  minZoom: 3,
  worldCopyJump: true
});
map.setView([26.42, 55.7], 6, { animate: false });

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap contributors"
}).addTo(map);

function shipIcon(kind, selected = false, heading = 0) {
  const size = kind === "flagship" ? 32 : 24;
  const selectedClass = selected ? " selected" : "";
  return L.divIcon({
    className: "fleet-dot",
    html: `<span class="ship-dot ${kind}${selectedClass}" style="--heading:${heading}deg"></span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2]
  });
}

function waypointIcon(index, suggested = false, selected = false) {
  const suggestedClass = suggested ? " suggested" : "";
  const selectedClass = selected ? " selected" : "";
  return L.divIcon({
    className: "fleet-dot",
    html: `<span class="waypoint-dot${suggestedClass}${selectedClass}">${index + 1}</span>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10]
  });
}

function threatIcon() {
  return L.divIcon({
    className: "fleet-dot",
    html: '<span class="threat-dot"></span>',
    iconSize: [26, 26],
    iconAnchor: [13, 13]
  });
}

const courseLine = L.polyline([], {
  color: "#0d8192",
  weight: 3,
  opacity: 0.9,
  dashArray: "10 8"
}).addTo(map);

const blockedLine = L.polyline([], {
  color: "#ff8f73",
  weight: 3,
  opacity: 0.9,
  dashArray: "4 6"
}).addTo(map);

const detourPreviewLine = L.polyline([], {
  color: "#e8b95d",
  weight: 3,
  opacity: 0.92,
  dashArray: "2 7",
  className: "detour-preview"
}).addTo(map);

const threatLine = L.polyline([], {
  color: "#ff4f5f",
  weight: 2,
  opacity: 0.82,
  dashArray: "5 7",
  className: "threat-line"
}).addTo(map);

const formationLinks = FORMATION.map(() =>
  L.polyline([], {
    color: "#25d9e8",
    weight: 1,
    opacity: 0.46,
    dashArray: "3 9",
    className: "formation-link"
  }).addTo(map)
);

const landZoneLayers = LAND_ZONES.map((zone) => {
  const layer = L.rectangle(
    [
      [zone.south, zone.west],
      [zone.north, zone.east]
    ],
    {
      className: "land-zone",
      color: "#ff8f73",
      fillColor: "#ff8f73",
      fillOpacity: 0.14,
      opacity: 0.68,
      weight: 1
    }
  );
  layer
    .bindTooltip(zone.name, { direction: "center", sticky: true })
    .addTo(map);
  return { zone, layer };
});

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

const trailColors = ["#e8b95d", ...FORMATION.map(() => "#25d9e8")];
const trailLayers = [
  L.layerGroup().addTo(map),
  ...FORMATION.map(() => L.layerGroup().addTo(map))
];

const currentPosition = document.querySelector("#currentPosition");
const destinationPosition = document.querySelector("#destinationPosition");
const distanceValue = document.querySelector("#distanceValue");
const motionStatus = document.querySelector("#motionStatus");
const speedValue = document.querySelector("#speedValue");
const warpValue = document.querySelector("#warpValue");
const navigationStatus = document.querySelector("#navigationStatus");
const routeStatus = document.querySelector("#routeStatus");
const escortModeStatus = document.querySelector("#escortModeStatus");
const pauseButton = document.querySelector("#pauseButton");
const waypointButton = document.querySelector("#waypointButton");
const suggestDetourButton = document.querySelector("#suggestDetourButton");
const acceptDetourButton = document.querySelector("#acceptDetourButton");
const escortModeButton = document.querySelector("#escortModeButton");
const undoWaypointButton = document.querySelector("#undoWaypointButton");
const removeWaypointButton = document.querySelector("#removeWaypointButton");
const clearWaypointsButton = document.querySelector("#clearWaypointsButton");
const cancelRouteButton = document.querySelector("#cancelRouteButton");
const homeButton = document.querySelector("#homeButton");
const resetButton = document.querySelector("#resetButton");
const warpButtons = document.querySelectorAll(".warp-button");
const scenarioPresetSelect = document.querySelector("#scenarioPresetSelect");
const applyPresetButton = document.querySelector("#applyPresetButton");
const flagshipSpeedControl = document.querySelector("#flagshipSpeedControl");
const flagshipSpeedOutput = document.querySelector("#flagshipSpeedOutput");
const escortSpeedControl = document.querySelector("#escortSpeedControl");
const escortSpeedOutput = document.querySelector("#escortSpeedOutput");
const formationSpreadControl = document.querySelector("#formationSpreadControl");
const formationSpreadOutput = document.querySelector("#formationSpreadOutput");
const variantNameInput = document.querySelector("#variantNameInput");
const feltGoodInput = document.querySelector("#feltGoodInput");
const feltWrongInput = document.querySelector("#feltWrongInput");
const suggestedChangeInput = document.querySelector("#suggestedChangeInput");
const exportScenarioButton = document.querySelector("#exportScenarioButton");
const downloadScenarioButton = document.querySelector("#downloadScenarioButton");
const scenarioExportOutput = document.querySelector("#scenarioExportOutput");
const shipInfoHeading = document.querySelector("#shipInfoHeading");
const shipPosition = document.querySelector("#shipPosition");
const shipSpeed = document.querySelector("#shipSpeed");
const shipHeading = document.querySelector("#shipHeading");
const shipStatus = document.querySelector("#shipStatus");
const shipDestination = document.querySelector("#shipDestination");
const captainsLog = document.querySelector("#captainsLog");
const openingOverlay = document.querySelector("#openingOverlay");
const skipIntroButton = document.querySelector("#skipIntroButton");

let flagship = { ...HOME };
let destination = null;
let finalDestination = null;
let waypoints = [];
let routeQueue = [];
let waypointMarkers = [];
let waypointMode = false;
let selectedWaypointIndex = null;
let pendingDetour = null;
let suggestedDetour = null;
let timeWarp = 1;
let lastMovingWarp = 1;
let currentSpeedKmh = 0;
let designSettings = { ...DESIGN_DEFAULTS };
let lastScenarioExport = "";
let activePresetId = "freeplay";
let threat = null;
let threatMarker = null;
let score = {
  neutralized: 0,
  breaches: 0
};
let selectedShipId = "monad";
let previousFrame;
let lastStatus = "Holding";
let lastNavigationMessage = "Clear";
let headingDegrees = null;
let renderedHeading = null;
let renderedSelection = null;
let renderedEscortHeadings = null;
let escortModeIndex = 1;
let logEntries = [];
let shipTrails = [];
let simulationClockSeconds = 0;
let escortStates = createEscortStates();

function createEscortStates() {
  return FORMATION.map((escort) => ({
    ...escort,
    position: { lat: HOME.lat + escort.lat, lng: HOME.lng + escort.lng },
    speedKmh: 0,
    headingDegrees: null,
    blocked: false
  }));
}

function createInitialTrails() {
  if (typeof trailLayers !== "undefined") {
    trailLayers.forEach((layer) => layer.clearLayers());
  }
  shipTrails = [
    [[HOME.lat, HOME.lng]],
    ...escortStates.map((escort) => [[escort.position.lat, escort.position.lng]])
  ];
}

function toRadians(degrees) {
  return degrees * (Math.PI / 180);
}

function toDegrees(radians) {
  return radians * (180 / Math.PI);
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function smoothstep(value) {
  const t = clamp(value, 0, 1);
  return t * t * (3 - 2 * t);
}

function smoothingAlpha(elapsedSeconds, responseSeconds) {
  return 1 - Math.exp(-elapsedSeconds / responseSeconds);
}

function angleDeltaDegrees(current, target) {
  return ((target - current + 540) % 360) - 180;
}

function easeHeading(current, target, elapsedSeconds) {
  if (current === null) {
    return target;
  }
  const alpha = smoothingAlpha(elapsedSeconds, HEADING_RESPONSE_SECONDS);
  return (current + angleDeltaDegrees(current, target) * alpha + 360) % 360;
}

function currentEscortMode() {
  return ESCORT_MODES[escortModeIndex];
}

function escortModeIndexFor(id) {
  const index = ESCORT_MODES.findIndex((mode) => mode.id === id);
  return index === -1 ? escortModeIndex : index;
}

function currentFlagshipSpeedKmh() {
  return designSettings.flagshipSpeedKmh;
}

function currentEscortSpeedMultiplier() {
  return designSettings.escortSpeedScale;
}

function currentFormationSpread() {
  return designSettings.formationSpread;
}

function escortSlot(escort, index) {
  const mode = currentEscortMode();
  const spread = currentFormationSpread();
  const phase = simulationClockSeconds * 0.18 + index * 2.15;
  return {
    lat: flagship.lat + escort.lat * spread + Math.sin(phase) * ESCORT_DRIFT_LAT * mode.driftScale * spread,
    lng: flagship.lng + escort.lng * spread + Math.cos(phase * 0.8) * ESCORT_DRIFT_LNG * mode.driftScale * spread
  };
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

function pointInZone(point, zone) {
  return (
    point.lat >= zone.south &&
    point.lat <= zone.north &&
    point.lng >= zone.west &&
    point.lng <= zone.east
  );
}

function orientation(a, b, c) {
  const value = (b.y - a.y) * (c.x - b.x) - (b.x - a.x) * (c.y - b.y);
  if (Math.abs(value) < 0.0000001) {
    return 0;
  }
  return value > 0 ? 1 : 2;
}

function onSegment(a, b, c) {
  return (
    b.x <= Math.max(a.x, c.x) &&
    b.x >= Math.min(a.x, c.x) &&
    b.y <= Math.max(a.y, c.y) &&
    b.y >= Math.min(a.y, c.y)
  );
}

function segmentsIntersect(firstStart, firstEnd, secondStart, secondEnd) {
  const o1 = orientation(firstStart, firstEnd, secondStart);
  const o2 = orientation(firstStart, firstEnd, secondEnd);
  const o3 = orientation(secondStart, secondEnd, firstStart);
  const o4 = orientation(secondStart, secondEnd, firstEnd);

  if (o1 !== o2 && o3 !== o4) {
    return true;
  }
  if (o1 === 0 && onSegment(firstStart, secondStart, firstEnd)) {
    return true;
  }
  if (o2 === 0 && onSegment(firstStart, secondEnd, firstEnd)) {
    return true;
  }
  if (o3 === 0 && onSegment(secondStart, firstStart, secondEnd)) {
    return true;
  }
  return o4 === 0 && onSegment(secondStart, firstEnd, secondEnd);
}

function routeIntersectsZone(start, end, zone) {
  if (pointInZone(start, zone) || pointInZone(end, zone)) {
    return true;
  }

  const routeStart = { x: start.lng, y: start.lat };
  const routeEnd = { x: end.lng, y: end.lat };
  const corners = [
    { x: zone.west, y: zone.south },
    { x: zone.east, y: zone.south },
    { x: zone.east, y: zone.north },
    { x: zone.west, y: zone.north }
  ];

  return corners.some((corner, index) =>
    segmentsIntersect(routeStart, routeEnd, corner, corners[(index + 1) % corners.length])
  );
}

function checkNavigation(start, end) {
  const destinationZone = LAND_ZONES.find((zone) => pointInZone(end, zone));
  if (destinationZone) {
    return {
      clear: false,
      reason: `Destination inside ${destinationZone.name}.`,
      kind: "destination",
      zone: destinationZone
    };
  }

  const routeZone = LAND_ZONES.find((zone) => routeIntersectsZone(start, end, zone));
  if (routeZone) {
    return {
      clear: false,
      reason: `Route crosses ${routeZone.name}.`,
      kind: "route",
      zone: routeZone
    };
  }

  return {
    clear: true,
    reason: "Clear"
  };
}

function findEscortSlot(escort, index) {
  const base = escortSlot(escort, index);
  const candidateOffsets = [
    [0, 0],
    [0.14, 0],
    [-0.14, 0],
    [0, 0.18],
    [0, -0.18],
    [0.16, 0.16],
    [0.16, -0.16],
    [-0.16, 0.16],
    [-0.16, -0.16]
  ];

  for (const [latOffset, lngOffset] of candidateOffsets) {
    const candidate = {
      lat: base.lat + latOffset,
      lng: base.lng + lngOffset
    };
    if (checkNavigation(escort.position, candidate).clear) {
      return candidate;
    }
  }

  return null;
}

function checkRoute(points) {
  for (let index = 0; index < points.length - 1; index += 1) {
    const check = checkNavigation(points[index], points[index + 1]);
    if (!check.clear) {
      return {
        clear: false,
        reason: `Leg ${index + 1}: ${check.reason}`,
        kind: check.kind,
        zone: check.zone,
        start: points[index],
        end: points[index + 1]
      };
    }
  }

  return {
    clear: true,
    reason: "Clear"
  };
}

function routeDistance(points) {
  let total = 0;
  for (let index = 0; index < points.length - 1; index += 1) {
    total += distanceKm(points[index], points[index + 1]);
  }
  return total;
}

function detourCandidatesForZone(zone) {
  const margin = 0.24;
  const north = zone.north + margin;
  const south = zone.south - margin;
  const west = zone.west - margin;
  const east = zone.east + margin;
  const northwest = { lat: north, lng: west };
  const northeast = { lat: north, lng: east };
  const southeast = { lat: south, lng: east };
  const southwest = { lat: south, lng: west };

  return [
    [northwest, northeast],
    [southwest, southeast],
    [northeast, southeast],
    [northwest, southwest],
    [northwest],
    [northeast],
    [southeast],
    [southwest]
  ];
}

function suggestDetour(start, target, zone) {
  const viableRoutes = detourCandidatesForZone(zone)
    .map((candidateWaypoints) => {
      const route = [start, ...candidateWaypoints, target];
      return {
        waypoints: candidateWaypoints,
        distance: routeDistance(route),
        check: checkRoute(route)
      };
    })
    .filter((candidate) => candidate.check.clear)
    .sort((first, second) => first.distance - second.distance);

  return viableRoutes[0] || null;
}

function formatPosition(position) {
  return `${position.lat.toFixed(4)}, ${position.lng.toFixed(4)}`;
}

function formatEta(distance) {
  const effectiveSpeed = currentFlagshipSpeedKmh() * Math.max(timeWarp, 1);
  const totalMinutes = Math.ceil((distance / effectiveSpeed) * 60);
  if (totalMinutes < 1) {
    return "<1 min";
  }
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return hours ? `${hours}h ${minutes}m` : `${minutes}m`;
}

function formatSpeed(speed) {
  return `${Math.round(speed)} km/h sim`;
}

function threatLabel() {
  if (!threat) {
    return "No contact";
  }
  const range = distanceKm(threat.position, flagship);
  return `${threat.name}: ${range.toFixed(1)} km closing`;
}

function currentStatus() {
  if (destination && timeWarp > 0) {
    return "Underway";
  }
  if (lastStatus === "Blocked") {
    return "Blocked";
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
  const escort = escortStates.find((ship) => ship.id === id) || escortStates[0];
  return { ...escort.position };
}

function getSelectedShip() {
  if (selectedShipId === "monad") {
    return {
      id: "monad",
      name: "MONAD",
      kind: "flagship",
      position: getShipPosition("monad"),
      speedKmh: currentSpeedKmh,
      headingDegrees,
      blocked: false
    };
  }
  const escort = escortStates.find((ship) => ship.id === selectedShipId) || escortStates[0];
  return {
    id: escort.id,
    name: escort.name,
    kind: "escort",
    position: getShipPosition(escort.id),
    speedKmh: escort.speedKmh,
    headingDegrees: escort.headingDegrees,
    blocked: escort.blocked
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
    return true;
  }
  return false;
}

function flashAt(position, className = "feedback-pulse") {
  const marker = L.circleMarker([position.lat, position.lng], {
    radius: 7,
    color: "#ffffff",
    fillColor: "#25d9e8",
    fillOpacity: 0.65,
    opacity: 0.95,
    weight: 2,
    className
  }).addTo(map);
  window.setTimeout(() => marker.remove(), 950);
}

function emphasizeZone(zone) {
  if (!zone) {
    return;
  }
  const match = landZoneLayers.find((entry) => entry.zone.name === zone.name);
  if (!match) {
    return;
  }
  match.layer.setStyle({
    fillOpacity: 0.34,
    opacity: 1,
    weight: 3
  });
  window.setTimeout(() => {
    match.layer.setStyle({
      fillOpacity: 0.14,
      opacity: 0.68,
      weight: 1
    });
  }, 1200);
}

function buildCoursePath() {
  if (!routeQueue.length) {
    return [];
  }

  const path = [];
  const points = [flagship, ...routeQueue];
  for (let index = 0; index < points.length - 1; index += 1) {
    const start = points[index];
    const end = points[index + 1];
    if (index > 0) {
      path.push([start.lat, start.lng]);
      continue;
    }

    const distance = distanceKm(start, end);
    const desired = bearingDegrees(start, end);
    const current = headingDegrees === null ? desired : headingDegrees;
    const delta = angleDeltaDegrees(current, desired);
    const curveStrength = clamp(Math.abs(delta) / 160, 0, 0.22);
    if (distance < 2 || curveStrength < 0.02) {
      path.push([start.lat, start.lng]);
      continue;
    }

    const midpoint = {
      lat: (start.lat + end.lat) / 2,
      lng: (start.lng + end.lng) / 2
    };
    const side = delta >= 0 ? 1 : -1;
    const offset = curveStrength * 0.18;
    const control = {
      lat: midpoint.lat + side * offset,
      lng: midpoint.lng - side * offset
    };
    for (let step = 0; step <= 8; step += 1) {
      const t = step / 8;
      const inverse = 1 - t;
      path.push([
        inverse * inverse * start.lat + 2 * inverse * t * control.lat + t * t * end.lat,
        inverse * inverse * start.lng + 2 * inverse * t * control.lng + t * t * end.lng
      ]);
    }
  }
  path.push(...points.slice(2).map((point) => [point.lat, point.lng]));
  return path;
}

function renderTrail(index) {
  const points = shipTrails[index];
  const layer = trailLayers[index];
  layer.clearLayers();

  if (points.length < TRAIL_REDRAW_MIN_POINTS) {
    return;
  }

  const color = trailColors[index];
  const maxSegment = points.length - 1;
  for (let pointIndex = 1; pointIndex < points.length; pointIndex += 1) {
    const age = pointIndex / maxSegment;
    const opacity = 0.08 + age * 0.68;
    const weight = index === 0
      ? 1.2 + age * 3.4
      : 0.9 + age * 2.4;

    L.polyline([points[pointIndex - 1], points[pointIndex]], {
      ...trailStyle,
      color,
      opacity,
      weight,
      lineCap: "round",
      lineJoin: "round"
    }).addTo(layer);
  }
}

function syncTrails() {
  const changed = [addTrailPoint(0, flagship)];
  escortStates.forEach((escort, index) => {
    changed[index + 1] = addTrailPoint(index + 1, escort.position);
  });
  changed.forEach((shouldRender, index) => {
    if (shouldRender) {
      renderTrail(index);
    }
  });
}

function updateMarkerIcons() {
  const heading = headingDegrees === null ? 0 : Math.round(headingDegrees);
  const escortHeadings = escortStates
    .map((escort) => Math.round(escort.headingDegrees === null ? heading : escort.headingDegrees))
    .join("|");
  if (
    renderedHeading === heading &&
    renderedSelection === selectedShipId &&
    renderedEscortHeadings === escortHeadings
  ) {
    return;
  }
  renderedHeading = heading;
  renderedSelection = selectedShipId;
  renderedEscortHeadings = escortHeadings;
  flagshipMarker.setIcon(shipIcon("flagship", selectedShipId === "monad", heading));
  escortMarkers.forEach((marker, index) => {
    const escort = escortStates[index];
    const escortHeading = Math.round(escort.headingDegrees === null ? heading : escort.headingDegrees);
    marker.setIcon(shipIcon("escort", selectedShipId === escort.id, escortHeading));
  });
}

function updateFleetMarkers() {
  flagshipMarker.setLatLng([flagship.lat, flagship.lng]);
  escortMarkers.forEach((marker, index) => {
    const escort = escortStates[index];
    marker.setLatLng([escort.position.lat, escort.position.lng]);
    formationLinks[index].setLatLngs([
      [flagship.lat, flagship.lng],
      [escort.position.lat, escort.position.lng]
    ]);
  });

  courseLine.setLatLngs(
    buildCoursePath()
  );
  updateThreatLayer();
  syncTrails();
}

function updateThreatLayer() {
  if (!threat) {
    if (threatMarker) {
      threatMarker.remove();
      threatMarker = null;
    }
    threatLine.setLatLngs([]);
    return;
  }

  if (!threatMarker) {
    threatMarker = L.marker([threat.position.lat, threat.position.lng], {
      icon: threatIcon(),
      title: threat.name
    })
      .bindTooltip(threat.name, { direction: "top", offset: [0, -14] })
      .addTo(map);
  }

  threatMarker.setLatLng([threat.position.lat, threat.position.lng]);
  threatLine.setLatLngs([
    [threat.position.lat, threat.position.lng],
    [flagship.lat, flagship.lng]
  ]);
}

function redrawWaypoints() {
  waypointMarkers.forEach((marker) => marker.remove());
  waypointMarkers = waypoints.map((waypoint, index) => {
    const marker = L.marker([waypoint.lat, waypoint.lng], {
      icon: waypointIcon(index, Boolean(suggestedDetour), selectedWaypointIndex === index),
      title: `Waypoint ${index + 1}`
    })
      .bindTooltip(`Waypoint ${index + 1}`, { direction: "top", offset: [0, -12] })
      .addTo(map);

    marker.on("click", (event) => {
      L.DomEvent.stopPropagation(event);
      selectWaypoint(index);
    });

    return marker;
  });
}

function showBlockedRoute(target, start = flagship, zone = null) {
  blockedLine.setLatLngs([
    [start.lat, start.lng],
    [target.lat, target.lng]
  ]);
  flashAt(target, "feedback-pulse rejected");
  emphasizeZone(zone);
}

function clearBlockedRoute() {
  blockedLine.setLatLngs([]);
}

function clearSuggestedDetour() {
  suggestedDetour = null;
  pendingDetour = null;
  detourPreviewLine.setLatLngs([]);
}

function clearRoutePlan() {
  destination = null;
  finalDestination = null;
  routeQueue = [];
  currentSpeedKmh = 0;
  waypoints = [];
  selectedWaypointIndex = null;
  clearSuggestedDetour();
  redrawWaypoints();
  clearBlockedRoute();
}

function previewSuggestedDetour() {
  if (!suggestedDetour) {
    detourPreviewLine.setLatLngs([]);
    return;
  }

  detourPreviewLine.setLatLngs([
    [flagship.lat, flagship.lng],
    ...suggestedDetour.waypoints.map((point) => [point.lat, point.lng]),
    [suggestedDetour.target.lat, suggestedDetour.target.lng]
  ]);
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
    .map((entry, index) => `<li class="${index === 0 ? "latest" : ""}"><time>${entry.timestamp}</time>${entry.message}</li>`)
    .join("");
}

function updateShipInfo() {
  const selected = getSelectedShip();
  const mode = currentEscortMode();
  const status = selected.id === "monad"
    ? currentStatus()
    : selected.blocked
      ? "Holding"
      : selected.speedKmh > 1
        ? "Underway"
        : "Holding";

  shipInfoHeading.textContent = selected.name;
  shipPosition.textContent = formatPosition(selected.position);
  shipSpeed.textContent = formatSpeed(selected.speedKmh);
  shipHeading.textContent = selected.headingDegrees === null ? "--" : `${Math.round(selected.headingDegrees)} deg`;
  shipStatus.textContent = status;
  shipDestination.textContent = selected.id === "monad"
    ? finalDestination
      ? formatPosition(finalDestination)
      : "No course set"
    : `${mode.label} slot`;
}

function updateWarpControls() {
  warpValue.textContent = timeWarp === 0 ? "Paused" : `${timeWarp}x`;
  warpButtons.forEach((button) => {
    button.classList.toggle("active", Number(button.dataset.warp) === timeWarp);
  });
  pauseButton.textContent = timeWarp === 0 ? "Resume" : "Pause";
}

function syncDesignControls() {
  flagshipSpeedControl.value = String(designSettings.flagshipSpeedKmh);
  escortSpeedControl.value = designSettings.escortSpeedScale.toFixed(2);
  formationSpreadControl.value = designSettings.formationSpread.toFixed(2);
  flagshipSpeedOutput.textContent = `${Math.round(designSettings.flagshipSpeedKmh)} km/h`;
  escortSpeedOutput.textContent = `${designSettings.escortSpeedScale.toFixed(2)}x`;
  formationSpreadOutput.textContent = `${designSettings.formationSpread.toFixed(2)}x`;
}

function setDesignSetting(key, value, shouldLog = false) {
  designSettings = {
    ...designSettings,
    [key]: value
  };
  syncDesignControls();
  if (shouldLog) {
    addLog(`Design parameter changed: ${key} = ${Number(value).toFixed(key === "flagshipSpeedKmh" ? 0 : 2)}.`);
  }
  updateStatus();
}

function resetThreatDrill(shouldLog = true) {
  threat = null;
  score = {
    neutralized: 0,
    breaches: 0
  };
  if (shouldLog) {
    addLog("Threat drill reset.");
  }
  updateFleetMarkers();
  updateStatus();
}

function roundedPosition(position) {
  if (!position) {
    return null;
  }
  return {
    lat: Number(position.lat.toFixed(5)),
    lng: Number(position.lng.toFixed(5))
  };
}

function scenarioPoints(points) {
  return points.map((point) => roundedPosition(point));
}

function buildScenarioArtifact() {
  const activeRoute = [
    ...(destination ? [{ ...destination }] : []),
    ...routeQueue.slice(destination ? 1 : 0)
  ];
  const artifact = {
    toy: "fleet-motion",
    schemaVersion: 1,
    exportedAt: new Date().toISOString(),
    scenario: {
      area: "Strait of Hormuz",
      presetId: activePresetId,
      presetLabel: SCENARIO_PRESETS[activePresetId]?.label || "Freeplay / Manual",
      variantName: variantNameInput.value.trim() || "untitled_variant",
      status: currentStatus()
    },
    parameters: {
      flagshipSpeedKmh: designSettings.flagshipSpeedKmh,
      escortSpeedScale: Number(designSettings.escortSpeedScale.toFixed(2)),
      formationSpread: Number(designSettings.formationSpread.toFixed(2)),
      escortMode: currentEscortMode().id,
      timeWarp
    },
    fleet: {
      flagship: {
        name: "MONAD",
        position: roundedPosition(flagship),
        speedKmh: Math.round(currentSpeedKmh),
        headingDegrees: headingDegrees === null ? null : Math.round(headingDegrees)
      },
      escorts: escortStates.map((escort) => ({
        id: escort.id,
        name: escort.name,
        position: roundedPosition(escort.position),
        speedKmh: Math.round(escort.speedKmh),
        headingDegrees: escort.headingDegrees === null ? null : Math.round(escort.headingDegrees),
        blocked: escort.blocked
      }))
    },
    route: {
      finalDestination: roundedPosition(finalDestination),
      stagedWaypoints: scenarioPoints(waypoints),
      activeLegs: scenarioPoints(activeRoute),
      navigationStatus: lastNavigationMessage
    },
    designerNotes: {
      feltGood: feltGoodInput.value.trim(),
      feltWrong: feltWrongInput.value.trim(),
      suggestedChange: suggestedChangeInput.value.trim()
    },
    constraints: [
      "Standalone browser toy",
      "No backend or persistence",
      "Not connected to Bridge, doctrine, Qdrant, agents, or deployment automation",
      "Not for real navigation"
    ]
  };
  if (INTERNAL_FEATURES.threatDrill) {
    artifact.parameters.threatSpeedKmh = THREAT_SPEED_KMH;
    artifact.parameters.threatInterceptRadiusKm = THREAT_INTERCEPT_RADIUS_KM;
    artifact.parameters.threatBreachRadiusKm = THREAT_BREACH_RADIUS_KM;
    artifact.threat = threat
      ? {
          name: threat.name,
          position: roundedPosition(threat.position),
          target: "MONAD",
          rangeToFlagshipKm: Number(distanceKm(threat.position, flagship).toFixed(2))
        }
      : null;
    artifact.score = { ...score };
  }
  return artifact;
}

function exportScenario() {
  lastScenarioExport = `${JSON.stringify(buildScenarioArtifact(), null, 2)}\n`;
  scenarioExportOutput.value = lastScenarioExport;
  downloadScenarioButton.disabled = false;
  scenarioExportOutput.focus();
  scenarioExportOutput.select();
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(lastScenarioExport).catch(() => {});
  }
  addLog("Scenario JSON exported for designer handoff.");
}

function safeFilename(value) {
  return (value || "fleet-motion-scenario")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80) || "fleet-motion-scenario";
}

function downloadScenarioExport() {
  if (!lastScenarioExport) {
    return;
  }
  const blob = new Blob([lastScenarioExport], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${safeFilename(variantNameInput.value)}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  addLog("Scenario JSON download prepared.");
}

function loadPassiveOpeningRoute() {
  const preset = SCENARIO_PRESETS.hormuz_transit;
  activePresetId = preset.id;
  scenarioPresetSelect.value = preset.id;
  designSettings = { ...preset.settings };
  escortModeIndex = escortModeIndexFor(preset.escortModeId);
  variantNameInput.value = preset.variantName;
  suggestedChangeInput.placeholder = preset.notePrompt;
  syncDesignControls();
  waypoints = [];
  selectedWaypointIndex = null;
  finalDestination = { ...preset.destination };
  routeQueue = [finalDestination];
  destination = routeQueue[0];
  headingDegrees = bearingDegrees(flagship, destination);
  lastStatus = "Underway";
  lastNavigationMessage = "Clear";
  addLog("Opening route loaded: Hormuz Transit.");
}

function completeIntro() {
  document.body.classList.remove("is-opening");
  if (openingOverlay) {
    openingOverlay.classList.add("complete");
  }
}

function startOpeningSequence() {
  loadPassiveOpeningRoute();
  updateFleetMarkers();
  updateStatus();
  window.setTimeout(() => {
    map.flyTo([HOME.lat, HOME.lng], 7, {
      animate: true,
      duration: 3.2,
      easeLinearity: 0.28
    });
  }, 450);
  window.setTimeout(completeIntro, INTRO_DURATION_MS);
}

function applyScenarioPreset(presetId) {
  const preset = SCENARIO_PRESETS[presetId] || SCENARIO_PRESETS.freeplay;
  activePresetId = preset.id;
  scenarioPresetSelect.value = preset.id;

  resetFleet();
  designSettings = { ...preset.settings };
  escortModeIndex = escortModeIndexFor(preset.escortModeId);
  syncDesignControls();

  variantNameInput.value = preset.variantName;
  feltGoodInput.value = "";
  feltWrongInput.value = "";
  suggestedChangeInput.value = "";
  suggestedChangeInput.placeholder = preset.notePrompt;
  lastScenarioExport = "";
  scenarioExportOutput.value = "";
  downloadScenarioButton.disabled = true;

  waypoints = preset.waypoints.map((point) => ({ ...point }));
  redrawWaypoints();
  if (preset.destination) {
    setDestination(preset.destination);
  } else {
    updateFleetMarkers();
    updateStatus();
  }

  if (preset.spawnThreat) {
    spawnThreat();
  }

  addLog(`Scenario preset loaded: ${preset.label}.`);
}

function spawnThreat() {
  if (!INTERNAL_FEATURES.threatDrill) {
    return;
  }
  threat = {
    id: "threat-1",
    name: "HOSTILE CONTACT",
    position: { ...THREAT_START },
    headingDegrees: bearingDegrees(THREAT_START, flagship),
    speedKmh: THREAT_SPEED_KMH
  };
  addLog("Hostile contact spawned southeast of the fleet.");
  updateFleetMarkers();
  updateStatus();
}

function clearThreat(message = "Threat contact cleared.") {
  threat = null;
  addLog(message);
  updateFleetMarkers();
  updateStatus();
}

function neutralizeThreat(escort) {
  score.neutralized += 1;
  clearThreat(`${escort.name} neutralized hostile contact.`);
}

function breachThreat() {
  score.breaches += 1;
  clearThreat("Hostile contact breached MONAD screen.");
}

function advanceThreat(elapsedSeconds) {
  if (!INTERNAL_FEATURES.threatDrill || !threat) {
    return;
  }

  const closestEscort = escortStates
    .map((escort) => ({
      escort,
      range: distanceKm(threat.position, escort.position)
    }))
    .sort((first, second) => first.range - second.range)[0];

  if (closestEscort && closestEscort.range <= THREAT_INTERCEPT_RADIUS_KM) {
    neutralizeThreat(closestEscort.escort);
    return;
  }

  const rangeToFlagship = distanceKm(threat.position, flagship);
  if (rangeToFlagship <= THREAT_BREACH_RADIUS_KM) {
    breachThreat();
    return;
  }

  threat.headingDegrees = bearingDegrees(threat.position, flagship);
  const stepDistance = THREAT_SPEED_KMH * timeWarp * (elapsedSeconds / 3600);
  const ratio = Math.min(stepDistance / rangeToFlagship, 1);
  threat.position.lat += (flagship.lat - threat.position.lat) * ratio;
  threat.position.lng += (flagship.lng - threat.position.lng) * ratio;
}

function updateStatus() {
  const status = currentStatus();
  const mode = currentEscortMode();
  currentPosition.textContent = formatPosition(flagship);
  destinationPosition.textContent = destination
    ? formatPosition(finalDestination || destination)
    : "No course set";
  speedValue.textContent = formatSpeed(currentSpeedKmh);
  escortModeStatus.textContent = mode.label;
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
  motionStatus.classList.toggle("blocked", status === "Blocked");
  navigationStatus.textContent = lastNavigationMessage;
  routeStatus.textContent = waypointMode
    ? "Click map to place one waypoint"
    : suggestedDetour
      ? `Detour suggested: ${suggestedDetour.waypoints.length} waypoint${suggestedDetour.waypoints.length === 1 ? "" : "s"}`
      : pendingDetour
        ? "Route blocked; detour available"
        : status === "Blocked"
          ? "Manual waypoint required"
        : selectedWaypointIndex !== null && waypoints[selectedWaypointIndex]
          ? `Waypoint ${selectedWaypointIndex + 1} selected for editing`
        : routeQueue.length
      ? `${routeQueue.length} active leg${routeQueue.length === 1 ? "" : "s"}`
      : waypoints.length
        ? `${waypoints.length} waypoint${waypoints.length === 1 ? "" : "s"} staged; click destination`
        : "Direct course";
  pauseButton.disabled = !destination && timeWarp !== 0;
  waypointButton.classList.toggle("active", waypointMode);
  suggestDetourButton.hidden = !pendingDetour && !suggestedDetour;
  acceptDetourButton.hidden = !suggestedDetour;
  suggestDetourButton.disabled = !pendingDetour || Boolean(suggestedDetour);
  acceptDetourButton.disabled = !suggestedDetour;
  undoWaypointButton.disabled = !waypoints.length;
  removeWaypointButton.disabled = selectedWaypointIndex === null || !waypoints[selectedWaypointIndex];
  clearWaypointsButton.disabled = !waypoints.length && !routeQueue.length && !destination;
  cancelRouteButton.disabled = !destination && !routeQueue.length;
  escortModeButton.textContent = `Escort: ${mode.label}`;
  updateWarpControls();
  updateMarkerIcons();
  updateShipInfo();
}

function setDestination(position) {
  const nextDestination = { lat: position.lat, lng: position.lng };
  const plannedRoute = [flagship, ...waypoints, nextDestination];
  const navigationCheck = checkRoute(plannedRoute);

  if (!navigationCheck.clear) {
    destination = null;
    finalDestination = null;
    routeQueue = [];
    suggestedDetour = null;
    detourPreviewLine.setLatLngs([]);
    pendingDetour = navigationCheck.kind === "route" && navigationCheck.zone
      ? {
          start: { ...flagship },
          target: nextDestination,
          zone: navigationCheck.zone,
          reason: navigationCheck.reason
        }
      : null;
    lastStatus = "Blocked";
    lastNavigationMessage = pendingDetour
      ? `${navigationCheck.reason} Detour available.`
      : navigationCheck.reason;
    showBlockedRoute(navigationCheck.end || nextDestination, navigationCheck.start || flagship, navigationCheck.zone);
    addLog(`Navigation blocked: ${navigationCheck.reason}`);
    updateFleetMarkers();
    updateStatus();
    return;
  }

  clearBlockedRoute();
  clearSuggestedDetour();
  selectedWaypointIndex = null;
  finalDestination = nextDestination;
  routeQueue = [...waypoints, finalDestination];
  destination = routeQueue[0];
  if (headingDegrees === null) {
    headingDegrees = bearingDegrees(flagship, destination);
  }
  lastStatus = "Underway";
  lastNavigationMessage = waypoints.length
    ? `Clear via ${waypoints.length} waypoint${waypoints.length === 1 ? "" : "s"}.`
    : "Clear";
  if (timeWarp === 0) {
    timeWarp = lastMovingWarp;
  }
  addLog(`Destination set: ${formatPosition(finalDestination)}.`);
  addLog("Fleet starts underway.");
  updateFleetMarkers();
  updateStatus();
}

function addWaypoint(position) {
  const waypoint = { lat: position.lat, lng: position.lng };
  const start = waypoints.length ? waypoints[waypoints.length - 1] : flagship;
  const navigationCheck = checkNavigation(start, waypoint);
  const oneShotMode = waypointMode;

  if (!navigationCheck.clear) {
    waypointMode = false;
    lastStatus = "Blocked";
    lastNavigationMessage = `Waypoint rejected: ${navigationCheck.reason}`;
    showBlockedRoute(waypoint, start, navigationCheck.zone);
    addLog(`Waypoint rejected: ${navigationCheck.reason}`);
    updateStatus();
    return;
  }

  destination = null;
  finalDestination = null;
  routeQueue = [];
  waypoints.push(waypoint);
  selectedWaypointIndex = waypoints.length - 1;
  clearSuggestedDetour();
  if (oneShotMode) {
    waypointMode = false;
  }
  redrawWaypoints();
  flashAt(waypoint);
  clearBlockedRoute();
  lastStatus = "Holding";
  lastNavigationMessage = `Waypoint ${waypoints.length} staged. Click destination to start.`;
  addLog(`Waypoint ${waypoints.length} staged at ${formatPosition(waypoint)}.`);
  updateFleetMarkers();
  updateStatus();
}

function buildSuggestedDetour() {
  if (!pendingDetour) {
    return;
  }

  const suggestion = suggestDetour(pendingDetour.start, pendingDetour.target, pendingDetour.zone);
  if (!suggestion) {
    const zoneName = pendingDetour.zone.name;
    pendingDetour = null;
    lastNavigationMessage = "No simple detour found. Manual waypoint required.";
    addLog(`No simple detour found around ${zoneName}.`);
    updateStatus();
    return;
  }

  suggestedDetour = {
    target: pendingDetour.target,
    waypoints: suggestion.waypoints,
    zone: pendingDetour.zone,
    distance: suggestion.distance
  };
  waypoints = suggestion.waypoints.map((point) => ({ ...point }));
  selectedWaypointIndex = null;
  finalDestination = suggestedDetour.target;
  routeQueue = [];
  destination = null;
  waypointMode = false;
  lastStatus = "Holding";
  lastNavigationMessage = `Suggested detour around ${pendingDetour.zone.name}.`;
  redrawWaypoints();
  previewSuggestedDetour();
  addLog(`Suggested detour around ${pendingDetour.zone.name}.`);
  updateFleetMarkers();
  updateStatus();
}

function acceptSuggestedDetour() {
  if (!suggestedDetour) {
    return;
  }

  clearBlockedRoute();
  detourPreviewLine.setLatLngs([]);
  finalDestination = { ...suggestedDetour.target };
  routeQueue = [...waypoints.map((point) => ({ ...point })), finalDestination];
  destination = routeQueue[0];
  suggestedDetour = null;
  pendingDetour = null;
  redrawWaypoints();
  if (headingDegrees === null) {
    headingDegrees = bearingDegrees(flagship, destination);
  }
  lastStatus = "Underway";
  lastNavigationMessage = `Clear via ${waypoints.length} suggested waypoint${waypoints.length === 1 ? "" : "s"}.`;
  if (timeWarp === 0) {
    timeWarp = lastMovingWarp;
  }
  addLog("Suggested detour accepted. Fleet starts underway.");
  updateFleetMarkers();
  updateStatus();
}

function arrive() {
  flagship = { ...destination };
  routeQueue.shift();

  if (routeQueue.length) {
    destination = routeQueue[0];
    lastStatus = "Underway";
    lastNavigationMessage = "Clear";
    addLog(`MONAD reached route leg. Next leg: ${formatPosition(destination)}.`);
    updateFleetMarkers();
    updateStatus();
    return;
  }

  destination = null;
  finalDestination = null;
  currentSpeedKmh = 0;
  lastStatus = "Arrived";
  lastNavigationMessage = "Clear";
  waypoints = [];
  selectedWaypointIndex = null;
  redrawWaypoints();
  clearBlockedRoute();
  addLog(`MONAD arrived at ${formatPosition(flagship)}.`);
  updateFleetMarkers();
  updateStatus();
}

function advanceEscort(escort, index, elapsedSeconds) {
  const mode = currentEscortMode();
  const target = findEscortSlot(escort, index);
  if (!target) {
    escort.blocked = true;
    escort.speedKmh += (0 - escort.speedKmh) * smoothingAlpha(elapsedSeconds, ESCORT_SLOT_RESPONSE_SECONDS);
    return;
  }

  const remaining = distanceKm(escort.position, target);
  if (remaining <= mode.slotRadiusKm) {
    escort.blocked = false;
    escort.speedKmh += (0 - escort.speedKmh) * smoothingAlpha(elapsedSeconds, ESCORT_SLOT_RESPONSE_SECONDS);
    return;
  }

  const targetSpeed = currentFlagshipSpeedKmh() * timeWarp * mode.speedMultiplier * currentEscortSpeedMultiplier();
  const speedAlpha = smoothingAlpha(elapsedSeconds, ESCORT_SLOT_RESPONSE_SECONDS);
  escort.speedKmh += (targetSpeed - escort.speedKmh) * speedAlpha;
  escort.headingDegrees = easeHeading(escort.headingDegrees, bearingDegrees(escort.position, target), elapsedSeconds);

  const stepDistance = escort.speedKmh * (elapsedSeconds / 3600);
  if (stepDistance >= remaining) {
    escort.position = { ...target };
    escort.speedKmh = 0;
    escort.blocked = false;
    return;
  }

  const ratio = stepDistance / remaining;
  escort.position.lat += (target.lat - escort.position.lat) * ratio;
  escort.position.lng += (target.lng - escort.position.lng) * ratio;
  escort.blocked = false;
}

function advanceFleet(elapsedSeconds) {
  if (timeWarp === 0) {
    return;
  }

  simulationClockSeconds += elapsedSeconds * timeWarp;

  if (destination) {
    const remaining = distanceKm(flagship, destination);
    if (remaining <= ARRIVAL_RADIUS_KM) {
      arrive();
    } else {
      const cruiseSpeed = currentFlagshipSpeedKmh() * timeWarp;
      const slowdown = smoothstep(remaining / SLOWDOWN_DISTANCE_KM);
      const targetSpeed = cruiseSpeed * clamp(slowdown, 0.08, 1);
      const speedAlpha = smoothingAlpha(elapsedSeconds, SPEED_RESPONSE_SECONDS);
      currentSpeedKmh += (targetSpeed - currentSpeedKmh) * speedAlpha;

      const desiredHeading = bearingDegrees(flagship, destination);
      headingDegrees = easeHeading(headingDegrees, desiredHeading, elapsedSeconds);

      const stepDistance = currentSpeedKmh * (elapsedSeconds / 3600);
      if (stepDistance >= remaining) {
        arrive();
      } else {
        const ratio = stepDistance / remaining;
        flagship.lat += (destination.lat - flagship.lat) * ratio;
        flagship.lng += (destination.lng - flagship.lng) * ratio;
      }
    }
  } else {
    currentSpeedKmh += (0 - currentSpeedKmh) * smoothingAlpha(elapsedSeconds, SPEED_RESPONSE_SECONDS);
  }

  escortStates.forEach((escort, index) => advanceEscort(escort, index, elapsedSeconds));
  advanceThreat(elapsedSeconds);
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
  } else {
    currentSpeedKmh = 0;
    escortStates.forEach((escort) => {
      escort.speedKmh = 0;
    });
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
  clearRoutePlan();
  timeWarp = 1;
  lastMovingWarp = 1;
  currentSpeedKmh = 0;
  simulationClockSeconds = 0;
  escortStates = createEscortStates();
  threat = null;
  score = {
    neutralized: 0,
    breaches: 0
  };
  selectedShipId = "monad";
  previousFrame = undefined;
  lastStatus = "Holding";
  lastNavigationMessage = "Clear";
  headingDegrees = null;
  renderedHeading = null;
  renderedSelection = null;
  renderedEscortHeadings = null;
  createInitialTrails();
  addLog("Fleet reset to Strait of Hormuz station.");
  flashAt(flagship, "feedback-pulse reset");
  updateFleetMarkers();
  updateStatus();
  map.setView([HOME.lat, HOME.lng], 7);
}

function selectShip(id) {
  selectedShipId = id;
  flashAt(getShipPosition(id), "feedback-pulse selected");
  updateStatus();
}

function cycleEscortMode() {
  escortModeIndex = (escortModeIndex + 1) % ESCORT_MODES.length;
  escortModeButton.classList.add("attention");
  window.setTimeout(() => escortModeButton.classList.remove("attention"), 700);
  addLog(`Escort mode changed to ${currentEscortMode().label}.`);
  updateStatus();
}

function validateEditedWaypoints(actionMessage) {
  destination = null;
  finalDestination = null;
  routeQueue = [];
  currentSpeedKmh = 0;
  clearSuggestedDetour();

  if (!waypoints.length) {
    selectedWaypointIndex = null;
    clearBlockedRoute();
    lastStatus = "Holding";
    lastNavigationMessage = `${actionMessage} No waypoints staged.`;
    return true;
  }

  const navigationCheck = checkRoute([flagship, ...waypoints]);
  if (!navigationCheck.clear) {
    lastStatus = "Blocked";
    lastNavigationMessage = `${actionMessage} Edited route blocked: ${navigationCheck.reason}`;
    showBlockedRoute(navigationCheck.end || waypoints[waypoints.length - 1], navigationCheck.start || flagship, navigationCheck.zone);
    return false;
  }

  clearBlockedRoute();
  lastStatus = "Holding";
  lastNavigationMessage = `${actionMessage} ${waypoints.length} waypoint${waypoints.length === 1 ? "" : "s"} staged. Click destination to start.`;
  return true;
}

function selectWaypoint(index) {
  if (!waypoints[index]) {
    return;
  }
  selectedWaypointIndex = index;
  lastNavigationMessage = `Waypoint ${index + 1} selected for editing.`;
  redrawWaypoints();
  updateStatus();
}

function undoLastWaypoint() {
  if (!waypoints.length) {
    return;
  }
  const removedIndex = waypoints.length - 1;
  const removed = waypoints.pop();
  if (selectedWaypointIndex === removedIndex) {
    selectedWaypointIndex = null;
  } else if (selectedWaypointIndex !== null && selectedWaypointIndex > removedIndex) {
    selectedWaypointIndex -= 1;
  }
  validateEditedWaypoints(`Waypoint ${removedIndex + 1} removed.`);
  addLog(`Waypoint ${removedIndex + 1} undone at ${formatPosition(removed)}.`);
  redrawWaypoints();
  updateFleetMarkers();
  updateStatus();
}

function removeSelectedWaypoint() {
  if (selectedWaypointIndex === null || !waypoints[selectedWaypointIndex]) {
    return;
  }
  const removedIndex = selectedWaypointIndex;
  const [removed] = waypoints.splice(removedIndex, 1);
  selectedWaypointIndex = waypoints[removedIndex] ? removedIndex : null;
  validateEditedWaypoints(`Waypoint ${removedIndex + 1} removed.`);
  addLog(`Selected waypoint removed at ${formatPosition(removed)}.`);
  redrawWaypoints();
  updateFleetMarkers();
  updateStatus();
}

function cancelActiveRoute() {
  if (!destination && !routeQueue.length) {
    return;
  }
  destination = null;
  finalDestination = null;
  routeQueue = [];
  currentSpeedKmh = 0;
  waypointMode = false;
  selectedWaypointIndex = null;
  clearSuggestedDetour();
  clearBlockedRoute();
  lastStatus = "Holding";
  lastNavigationMessage = "Route canceled; current position retained.";
  flashAt(flagship, "feedback-pulse canceled");
  addLog(`Route canceled at ${formatPosition(flagship)}.`);
  redrawWaypoints();
  updateFleetMarkers();
  updateStatus();
}

map.on("click", (event) => {
  if (waypointMode || event.originalEvent.shiftKey) {
    addWaypoint(event.latlng);
    return;
  }
  setDestination(event.latlng);
});
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

waypointButton.addEventListener("click", () => {
  waypointMode = true;
  addLog("Waypoint placement armed for next map click.");
  updateStatus();
});

suggestDetourButton.addEventListener("click", buildSuggestedDetour);

acceptDetourButton.addEventListener("click", acceptSuggestedDetour);

escortModeButton.addEventListener("click", cycleEscortMode);

applyPresetButton.addEventListener("click", () => {
  applyScenarioPreset(scenarioPresetSelect.value);
});

undoWaypointButton.addEventListener("click", undoLastWaypoint);

removeWaypointButton.addEventListener("click", removeSelectedWaypoint);

cancelRouteButton.addEventListener("click", cancelActiveRoute);

clearWaypointsButton.addEventListener("click", () => {
  clearRoutePlan();
  waypointMode = false;
  selectedWaypointIndex = null;
  lastStatus = "Holding";
  lastNavigationMessage = "Route plan cleared.";
  addLog("Route plan cleared.");
  updateFleetMarkers();
  updateStatus();
});

warpButtons.forEach((button) => {
  button.addEventListener("click", () => setTimeWarp(Number(button.dataset.warp)));
});

flagshipSpeedControl.addEventListener("input", () => {
  setDesignSetting("flagshipSpeedKmh", Number(flagshipSpeedControl.value));
});
flagshipSpeedControl.addEventListener("change", () => {
  setDesignSetting("flagshipSpeedKmh", Number(flagshipSpeedControl.value), true);
});

escortSpeedControl.addEventListener("input", () => {
  setDesignSetting("escortSpeedScale", Number(escortSpeedControl.value));
});
escortSpeedControl.addEventListener("change", () => {
  setDesignSetting("escortSpeedScale", Number(escortSpeedControl.value), true);
});

formationSpreadControl.addEventListener("input", () => {
  setDesignSetting("formationSpread", Number(formationSpreadControl.value));
});
formationSpreadControl.addEventListener("change", () => {
  setDesignSetting("formationSpread", Number(formationSpreadControl.value), true);
});

exportScenarioButton.addEventListener("click", exportScenario);

downloadScenarioButton.addEventListener("click", downloadScenarioExport);

homeButton.addEventListener("click", () => {
  waypointMode = false;
  setDestination(HOME);
  map.panTo([HOME.lat, HOME.lng]);
});

resetButton.addEventListener("click", resetFleet);

skipIntroButton.addEventListener("click", completeIntro);

createInitialTrails();
syncDesignControls();
addLog("Fleet motion toy online. Captain's Log uses local browser time.");
startOpeningSequence();
window.requestAnimationFrame(animationFrame);
