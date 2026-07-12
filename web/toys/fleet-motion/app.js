const HOME = { lat: 20.5, lng: 63.2 };
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
const NPC_OPERATION_BOUNDS = {
  south: 19.5,
  north: 21.5,
  west: 62.0,
  east: 64.4
};
const THREAT_START = { lat: 20.64, lng: 63.52 };
const THREAT_SPEED_KMH = 240;
const THREAT_INTERCEPT_RADIUS_KM = 9;
const THREAT_BREACH_RADIUS_KM = 6;
const INTERNAL_FEATURES = {
  threatDrill: false,
  scenarioTools: false
};
const TRAIL_LIMIT = 180;
const TRAIL_REDRAW_MIN_POINTS = 2;
const LOG_LIMIT = 9;
const INTRO_DURATION_MS = 4800;
const FLEET_STATE_SCHEMA_VERSION = window.MonadFleetState.schemaVersion;
const FLEET_STATE_STORAGE_KEY = window.MonadFleetState.storageKey;
const FLEET_STATE_SAVE_INTERVAL_MS = 1200;
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
  arabian_sea_watch: {
    id: "arabian_sea_watch",
    label: "Arabian Sea Watch",
    variantName: "arabian_sea_watch",
    settings: {
      flagshipSpeedKmh: 180,
      escortSpeedScale: 1,
      formationSpread: 1
    },
    escortModeId: "loose",
    destination: { lat: 20.28, lng: 62.82 },
    waypoints: [],
    spawnThreat: false,
    notePrompt: "Open-water watch. Judge whether nearby traffic and escort spacing are readable."
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
    destination: { lat: 20.78, lng: 62.76 },
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
    destination: { lat: 20.18, lng: 63.78 },
    waypoints: [{ lat: 20.72, lng: 63.48 }],
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
  { id: "escort-alpha", name: "ESCORT ALPHA", lat: -0.07, lng: -0.09 },
  { id: "escort-bravo", name: "ESCORT BRAVO", lat: -0.015, lng: 0.1 },
  { id: "escort-charlie", name: "ESCORT CHARLIE", lat: 0.08, lng: 0.04 }
];
const NPC_CONTACTS = [
  {
    id: "traffic-dhow-01",
    name: "DHOW LANTERN",
    role: "civilian dhow",
    position: { lat: 20.58, lng: 63.29 },
    headingDegrees: 312,
    speedKmh: 32
  },
  {
    id: "traffic-tanker-02",
    name: "TANKER GULF STAR",
    role: "merchant tanker",
    position: { lat: 20.42, lng: 63.05 },
    headingDegrees: 72,
    speedKmh: 44
  },
  {
    id: "traffic-patrol-03",
    name: "PILOT BOAT AMBER",
    role: "harbor pilot",
    position: { lat: 20.55, lng: 63.08 },
    headingDegrees: 246,
    speedKmh: 38
  },
  {
    id: "traffic-coaster-04",
    name: "COASTER QESHM",
    role: "coastal freighter",
    position: { lat: 20.36, lng: 63.28 },
    headingDegrees: 286,
    speedKmh: 36
  }
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
    name: "Legacy Island Box",
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
map.setView([HOME.lat, HOME.lng], 7, { animate: false });

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

function contactIcon(selected = false, heading = 0) {
  const selectedClass = selected ? " selected" : "";
  return L.divIcon({
    className: "fleet-dot",
    html: `<span class="contact-dot${selectedClass}" style="--heading:${heading}deg"></span>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14]
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

const contactMarkers = NPC_CONTACTS.map((contact) =>
  L.marker([contact.position.lat, contact.position.lng], {
    icon: contactIcon(false, contact.headingDegrees),
    title: contact.name
  })
    .bindTooltip(contact.name, { permanent: true, direction: "bottom", offset: [0, 12], className: "contact-label" })
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
const trafficStatus = document.querySelector("#trafficStatus");
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
const resetToBaselineButton = document.querySelector("#resetToBaselineButton");
const resetButton = document.querySelector("#resetButton");
const liveModeNoteEl = document.querySelector("#liveModeNote");
const warpButtons = document.querySelectorAll(".warp-button");
const dataSourceValue = document.querySelector("#dataSourceValue");
const dataSourceBadge = document.querySelector("#dataSourceBadge");
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
const lastStateSaved = document.querySelector("#lastStateSaved");
const stateSchemaValue = document.querySelector("#stateSchemaValue");
const stateSavedValue = document.querySelector("#stateSavedValue");
const statePresetValue = document.querySelector("#statePresetValue");
const stateFlagshipValue = document.querySelector("#stateFlagshipValue");
const stateMotionValue = document.querySelector("#stateMotionValue");
const stateRouteValue = document.querySelector("#stateRouteValue");
const stateEscortValue = document.querySelector("#stateEscortValue");
const stateContactValue = document.querySelector("#stateContactValue");
const stateSelectionValue = document.querySelector("#stateSelectionValue");
const copyStateButton = document.querySelector("#copyStateButton");
const downloadStateButton = document.querySelector("#downloadStateButton");
const clearStateButton = document.querySelector("#clearStateButton");

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
let renderedContactHeadings = null;
let escortModeIndex = 1;
let logEntries = [];
let shipTrails = [];
let simulationClockSeconds = 0;
let escortStates = createEscortStates();
let contactStates = createContactStates();
// Live mode only: escortStates/contactStates hold every real scout/passive
// vessel FleetCore reports (see applyLiveSnapshot()), not just the fixed
// 3+4 local demo roster (FORMATION/NPC_CONTACTS) non-live mode uses. The
// original escortMarkers/contactMarkers/formationLinks arrays are sized
// for that fixed roster and stay untouched -- hidden once, on first live
// snapshot -- rather than reused, since indexing into them past their
// fixed length would silently show only the first 3/4 real vessels.
// liveVesselMarkers is a real dynamic marker pool keyed by each vessel's
// own FleetCore id, reconciled (created/updated/removed) on every
// snapshot by renderLiveVessels().
const liveVesselMarkers = new Map();
let liveRenderingInitialized = false;
let lastPersistedAt = null;
let lastPersistenceAttemptMs = 0;
let restoredFromPersistentState = false;
let persistenceSuspended = false;
let lastKnownSelectionId = selectedShipId;
// Live FleetCore mode: when a real fleetcore-serve is reachable, Fleet
// Motion stops running its own local physics (see the liveMode guard in
// advanceFleet()) and instead renders positions straight from the server's
// broadcast snapshots -- see connectFleetCoreLive()/applyLiveSnapshot()
// near the bottom of this file. Read-only by default, the same as any
// other FleetCore client (docs/architecture/fleetcore-api.md) -- command
// authority is only granted if a `?commandToken=` is present in the URL
// and the server accepts it (see liveCommandAuthority below). No token
// baked into this bundle, unlike toys/bridge-station-3.0/: this file is
// also served from the public deployment, where fleetcore-serve isn't
// reachable, but "isn't reachable" is a network fact, not a promise --
// a hardcoded token here would command the shared fleet for everyone the
// moment that stops being true. When no live server answers at all, this
// whole path times out once and Fleet Motion behaves exactly as it always
// has.
let liveMode = false;
let liveSocket = null;
let liveReconnectTimer = null;
let liveReconnectDelayMs = 1000;
let liveMapCentered = false;
// Mirrors the server's clock.state ("running"/"paused"), which time_scale
// alone can't express -- a paused world can still have a nonzero scale
// waiting to resume at. Only meaningful once liveMode is true.
let liveClockState = "running";
let liveCommandAuthority = false;
let liveFlagshipId = null;
const LIVE_CONNECT_TIMEOUT_MS = 2500;
const LIVE_KMH_PER_MPS = 3.6;

function createEscortStates() {
  return FORMATION.map((escort) => ({
    ...escort,
    position: { lat: HOME.lat + escort.lat, lng: HOME.lng + escort.lng },
    speedKmh: 0,
    headingDegrees: null,
    blocked: false
  }));
}

function createContactStates() {
  return NPC_CONTACTS.map((contact) => ({
    ...contact,
    position: clonePoint(contact.position),
    speedKmh: contact.speedKmh,
    headingDegrees: contact.headingDegrees,
    status: "Transiting",
    lastTurnSeconds: 0
  }));
}

function clonePoint(point) {
  return point ? { lat: Number(point.lat), lng: Number(point.lng) } : null;
}

function clonePoints(points) {
  return (points || []).map((point) => clonePoint(point)).filter(Boolean);
}

function createBaselineFleetState() {
  return {
    schemaVersion: FLEET_STATE_SCHEMA_VERSION,
    savedAt: null,
    activePresetId: "arabian_sea_watch",
    designSettings: { ...DESIGN_DEFAULTS },
    flagship: {
      position: { ...HOME },
      headingDegrees: null,
      speedKmh: 0,
      engineOrderKmh: BASE_SPEED_KMH
    },
    navigation: {
      destination: null,
      finalDestination: null,
      waypoints: [],
      routeQueue: [],
      waypointMode: false,
      selectedWaypointIndex: null,
      lastStatus: "Holding",
      lastNavigationMessage: "Clear"
    },
    time: {
      timeWarp: 1,
      lastMovingWarp: 1,
      simulationClockSeconds: 0
    },
    escorts: {
      modeIndex: 1,
      modeId: "loose",
      formation: FORMATION.map((escort) => ({ ...escort })),
      ships: createEscortStates().map((escort) => ({
        id: escort.id,
        name: escort.name,
        position: clonePoint(escort.position),
        speedKmh: escort.speedKmh,
        headingDegrees: escort.headingDegrees,
        blocked: escort.blocked
      }))
    },
    contacts: {
      mode: "passive",
      ships: createContactStates().map((contact) => ({
        id: contact.id,
        name: contact.name,
        role: contact.role,
        position: clonePoint(contact.position),
        speedKmh: contact.speedKmh,
        headingDegrees: contact.headingDegrees,
        status: contact.status
      }))
    },
    selection: {
      selectedShipId: "monad"
    }
  };
}

function createCanonicalFleetState() {
  const now = new Date().toISOString();
  return {
    schemaVersion: FLEET_STATE_SCHEMA_VERSION,
    savedAt: now,
    dataSource: liveMode ? "fleetcore-live" : "local-simulation",
    // liveCommandAuthority is false whenever not live and only ever
    // becomes true from a real "connected" message (see
    // connectFleetCoreLive()), so passing the var straight through is
    // already correct in both modes -- no liveMode ternary needed.
    liveCommandAuthority,
    activePresetId,
    designSettings: { ...designSettings },
    flagship: {
      position: clonePoint(flagship),
      headingDegrees,
      speedKmh: currentSpeedKmh,
      engineOrderKmh: currentFlagshipSpeedKmh()
    },
    navigation: {
      destination: clonePoint(destination),
      finalDestination: clonePoint(finalDestination),
      waypoints: clonePoints(waypoints),
      routeQueue: clonePoints(routeQueue),
      waypointMode,
      selectedWaypointIndex,
      lastStatus,
      lastNavigationMessage
    },
    time: {
      timeWarp,
      lastMovingWarp,
      simulationClockSeconds
    },
    escorts: {
      modeIndex: escortModeIndex,
      modeId: currentEscortMode().id,
      formation: FORMATION.map((escort) => ({ ...escort })),
      ships: escortStates.map((escort) => ({
        id: escort.id,
        name: escort.name,
        position: clonePoint(escort.position),
        speedKmh: escort.speedKmh,
        headingDegrees: escort.headingDegrees,
        blocked: escort.blocked
      }))
    },
    contacts: {
      mode: "passive",
      ships: contactStates.map((contact) => ({
        id: contact.id,
        name: contact.name,
        role: contact.role,
        position: clonePoint(contact.position),
        speedKmh: contact.speedKmh,
        headingDegrees: contact.headingDegrees,
        status: contact.status
      }))
    },
    selection: {
      selectedShipId
    }
  };
}

function normalizeFleetState(candidate) {
  if (!candidate || candidate.schemaVersion !== FLEET_STATE_SCHEMA_VERSION) {
    return null;
  }
  const baseline = createBaselineFleetState();
  return {
    ...baseline,
    ...candidate,
    designSettings: { ...baseline.designSettings, ...(candidate.designSettings || {}) },
    flagship: { ...baseline.flagship, ...(candidate.flagship || {}) },
    navigation: { ...baseline.navigation, ...(candidate.navigation || {}) },
    time: { ...baseline.time, ...(candidate.time || {}) },
    escorts: { ...baseline.escorts, ...(candidate.escorts || {}) },
    contacts: { ...baseline.contacts, ...(candidate.contacts || {}) },
    selection: { ...baseline.selection, ...(candidate.selection || {}) }
  };
}

function applyCanonicalFleetState(state) {
  const normalized = normalizeFleetState(state);
  if (!normalized) {
    return false;
  }

  activePresetId = normalized.activePresetId || "freeplay";
  if (INTERNAL_FEATURES.scenarioTools && SCENARIO_PRESETS[activePresetId]) {
    scenarioPresetSelect.value = activePresetId;
    variantNameInput.value = SCENARIO_PRESETS[activePresetId].variantName;
    suggestedChangeInput.placeholder = SCENARIO_PRESETS[activePresetId].notePrompt;
  }

  designSettings = { ...DESIGN_DEFAULTS, ...normalized.designSettings };
  flagship = clonePoint(normalized.flagship.position) || { ...HOME };
  headingDegrees = normalized.flagship.headingDegrees;
  currentSpeedKmh = Number(normalized.flagship.speedKmh) || 0;

  destination = clonePoint(normalized.navigation.destination);
  finalDestination = clonePoint(normalized.navigation.finalDestination);
  waypoints = clonePoints(normalized.navigation.waypoints);
  routeQueue = clonePoints(normalized.navigation.routeQueue);
  waypointMode = Boolean(normalized.navigation.waypointMode);
  selectedWaypointIndex = normalized.navigation.selectedWaypointIndex;
  lastStatus = normalized.navigation.lastStatus || "Holding";
  lastNavigationMessage = normalized.navigation.lastNavigationMessage || "Clear";

  timeWarp = Number(normalized.time.timeWarp) || 0;
  lastMovingWarp = Number(normalized.time.lastMovingWarp) || 1;
  simulationClockSeconds = Number(normalized.time.simulationClockSeconds) || 0;

  escortModeIndex = Number.isInteger(normalized.escorts.modeIndex)
    ? normalized.escorts.modeIndex
    : escortModeIndexFor(normalized.escorts.modeId);
  escortStates = FORMATION.map((escort, index) => {
    const saved = (normalized.escorts.ships || []).find((ship) => ship.id === escort.id) || normalized.escorts.ships?.[index];
    return {
      ...escort,
      position: clonePoint(saved?.position) || { lat: HOME.lat + escort.lat, lng: HOME.lng + escort.lng },
      speedKmh: Number(saved?.speedKmh) || 0,
      headingDegrees: saved?.headingDegrees ?? null,
      blocked: Boolean(saved?.blocked)
    };
  });
  contactStates = NPC_CONTACTS.map((contact, index) => {
    const saved = (normalized.contacts.ships || []).find((ship) => ship.id === contact.id) || normalized.contacts.ships?.[index];
    const savedPosition = clonePoint(saved?.position);
    const savedPositionIsUsable = savedPosition && contactCanOccupy(savedPosition);
    const position = savedPositionIsUsable ? savedPosition : clonePoint(contact.position);
    return {
      ...contact,
      position,
      speedKmh: Number(saved?.speedKmh) || contact.speedKmh,
      headingDegrees: saved?.headingDegrees ?? contact.headingDegrees,
      status: savedPositionIsUsable ? saved?.status || "Transiting" : "Transiting",
      lastTurnSeconds: 0
    };
  });

  selectedShipId = normalized.selection.selectedShipId || "monad";
  renderedHeading = null;
  renderedSelection = null;
  renderedEscortHeadings = null;
  renderedContactHeadings = null;
  syncDesignControls();
  redrawWaypoints();
  createInitialTrails();
  lastPersistedAt = normalized.savedAt || null;
  updateLastSavedIndicator();
  updateFleetMarkers();
  updateStatus();
  return true;
}

function updateLastSavedIndicator() {
  if (!lastStateSaved) {
    return;
  }
  if (!lastPersistedAt) {
    lastStateSaved.textContent = "Not saved yet";
    return;
  }
  const date = new Date(lastPersistedAt);
  lastStateSaved.textContent = Number.isNaN(date.getTime())
    ? "Saved"
    : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function persistFleetState(force = false) {
  if (persistenceSuspended && !force) {
    return;
  }
  if (force) {
    persistenceSuspended = false;
  }
  const nowMs = Date.now();
  if (!force && nowMs - lastPersistenceAttemptMs < FLEET_STATE_SAVE_INTERVAL_MS) {
    return;
  }
  lastPersistenceAttemptMs = nowMs;
  try {
    const state = createCanonicalFleetState();
    if (!window.MonadFleetState.write(state)) {
      throw new Error("Shared fleet state contract rejected this state");
    }
    lastPersistedAt = state.savedAt;
    lastKnownSelectionId = state.selection.selectedShipId;
    updateLastSavedIndicator();
    updateStateInspector();
  } catch (error) {
    console.warn("Fleet state persistence failed", error);
    if (lastStateSaved) {
      lastStateSaved.textContent = "Save failed";
    }
  }
}

function restoreFleetState() {
  try {
    const state = window.MonadFleetState.read();
    const restored = state ? applyCanonicalFleetState(state) : false;
    lastKnownSelectionId = selectedShipId;
    return restored;
  } catch (error) {
    console.warn("Fleet state restore failed", error);
    return false;
  }
}

// Fleet Motion is the sole writer of most of MonadFleetState, but Periscope has
// an additive write path into `selection.selectedShipId` (a contact selected
// directly in Periscope). This must run every frame, not on its own throttle:
// animationFrame() always calls this immediately before advanceFleet() ->
// updateStatus() -> persistFleetState(), so checking every frame guarantees
// selectedShipId is fresh at the moment of any write. An earlier version
// throttled this to once/second independently of persistFleetState()'s own
// ~1.2s write throttle, which left a window where Fleet Motion's periodic
// write could fire on stale local state and silently clobber a Periscope-
// originated selection back to its previous value before this ever noticed.
function syncExternalSelection() {
  const external = window.MonadFleetState.read();
  if (!external) {
    return;
  }
  const externalId = external.selection?.selectedShipId || "monad";
  if (externalId === lastKnownSelectionId || externalId === selectedShipId) {
    lastKnownSelectionId = externalId;
    return;
  }
  lastKnownSelectionId = externalId;
  selectedShipId = externalId;
  flashAt(getShipPosition(selectedShipId), "feedback-pulse selected");
  updateStatus();
}

function fleetCoreServerUrl() {
  const params = new URLSearchParams(window.location.search);
  if (params.get("fleetcoreServer")) return params.get("fleetcoreServer");
  // Under the public /monad/ path, port 4771 isn't reachable directly --
  // route through Caddy's /monad/fleetcore-ws/ reverse proxy instead (see
  // docs/deployment.md). Anywhere else (LAN root, local dev server),
  // fleetcore-serve is reachable directly on its own port.
  if (window.location.pathname.startsWith("/monad/")) {
    const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${scheme}//${window.location.host}/monad/fleetcore-ws/ws`;
  }
  return `ws://${window.location.hostname || "localhost"}:4771/ws`;
}

// Command authority is opt-in per docs/architecture/fleetcore-api.md: pass
// `?token=<token>` on the /ws connect URL to request it. No default and no
// baked-in value -- see the liveMode comment above for why. An operator
// (or Bridge, forwarding its own `?commandToken=`) supplies this via URL.
function liveConnectUrl() {
  const base = fleetCoreServerUrl();
  const params = new URLSearchParams(window.location.search);
  const token = params.get("commandToken");
  if (!token) return base;
  return `${base}${base.includes("?") ? "&" : "?"}token=${encodeURIComponent(token)}`;
}

// One connection attempt to a live FleetCore server. Fails closed and
// silently: if nothing answers within LIVE_CONNECT_TIMEOUT_MS, Fleet
// Motion just proceeds exactly as it always has (local simulation). This
// matters because Fleet Motion is deployed publicly, where fleetcore-serve
// isn't reachable -- a hung or slow-failing connection attempt must never
// delay or degrade the normal standalone experience there.
function connectFleetCoreLive() {
  let settled = false;
  const socket = new WebSocket(liveConnectUrl());
  const timeout = setTimeout(() => {
    if (settled) return;
    settled = true;
    socket.close();
  }, LIVE_CONNECT_TIMEOUT_MS);

  socket.addEventListener("open", () => {
    liveReconnectDelayMs = 1000;
  });

  socket.addEventListener("message", (event) => {
    let message;
    try {
      message = JSON.parse(event.data);
    } catch (error) {
      return;
    }
    if (message.type === "connected") {
      liveCommandAuthority = Boolean(message.command_authority);
      updateLiveWriteControlsAvailability();
      updateLiveModeNote();
      return;
    }
    if (message.type === "error") {
      addLog(`Command rejected — ${message.message}`);
      return;
    }
    if (message.type !== "snapshot") return;
    if (!settled) {
      settled = true;
      clearTimeout(timeout);
      enterLiveMode();
    }
    applyLiveSnapshot(message.snapshot);
  });

  socket.addEventListener("close", () => {
    if (!settled) {
      // Never got a snapshot inside the timeout window -- give up for good
      // rather than retrying forever against a host with nothing listening.
      settled = true;
      clearTimeout(timeout);
      return;
    }
    if (liveMode) {
      // Was live and got disconnected mid-session: keep trying rather than
      // silently falling back to local physics, which would read as a
      // confusing regression to anyone watching rather than a connection
      // hiccup. Command authority doesn't carry over an open socket, so
      // don't assume it survives the gap either -- the next "connected"
      // message re-grants it if the token still checks out.
      liveCommandAuthority = false;
      updateLiveWriteControlsAvailability();
      updateLiveModeNote();
      liveReconnectTimer = setTimeout(() => {
        liveReconnectDelayMs = Math.min(liveReconnectDelayMs * 1.6, 15000);
        connectFleetCoreLive();
      }, liveReconnectDelayMs);
    }
  });

  liveSocket = socket;
}

// These have no FleetCore command behind them at all, in any mode, with
// any authority: Suggest/Accept Detour is a client-only land-avoidance
// heuristic FleetCore's Command enum has no terrain concept for; Escort
// Mode is cosmetic client-side formation drift that live snapshots
// overwrite every tick regardless; Return to Station is a fixed local-demo
// waypoint with no shared-world meaning; Reset to Open Water instantly
// teleports local state, and FleetCore has no reset/teleport command --
// only set-route, which moves a vessel over real ticks, not instantly.
// Permanently disabled while live, not authority-gated, so the visitor
// isn't misled into thinking a token would unlock them.
function disableLiveOnlyControls() {
  [
    suggestDetourButton, acceptDetourButton, escortModeButton,
    homeButton, resetToBaselineButton
  ].forEach((button) => {
    if (button) button.disabled = true;
  });
}

// Everything here DOES have a real FleetCore command (set-route,
// pause-clock, resume-clock, set-time-scale) -- availability tracks
// liveCommandAuthority, not a permanent live-mode disable. undo/remove/
// clear-waypoint stay additionally gated by their own state checks in
// updateStatus() (nothing staged yet, etc.); this function only handles
// the authority half of that gate.
function updateLiveWriteControlsAvailability() {
  const blocked = liveMode && !liveCommandAuthority;
  [waypointButton, pauseButton, undoWaypointButton, removeWaypointButton, clearWaypointsButton, cancelRouteButton]
    .forEach((button) => {
      if (button) button.disabled = blocked;
    });
  warpButtons.forEach((button) => {
    button.disabled = blocked;
  });
  updateStatus();
}

function updateLiveModeNote() {
  if (!liveModeNoteEl) return;
  if (!liveMode) {
    liveModeNoteEl.hidden = true;
    return;
  }
  liveModeNoteEl.hidden = false;
  liveModeNoteEl.textContent = liveCommandAuthority
    ? "Live command authority granted: click the map to send the ship there now. For a multi-leg route, click Add Waypoint to arm, click the map once per point, then click Add Waypoint again to send the whole path as one command (Shift-click also stages points, if you'd rather not use the button). Cancel Route and Pause/Time Warp also send real FleetCore commands. Escort Mode, Suggest/Accept Detour, Return to Station, and Reset to Open Water have no FleetCore command yet and stay disabled."
    : "Live, read-only: no command token presented, so every control here only observes. Escort Mode, Suggest/Accept Detour, Return to Station, and Reset to Open Water would stay disabled even with one — FleetCore has no command for them yet.";
}

function enterLiveMode() {
  liveMode = true;
  disableLiveOnlyControls();
  updateLiveWriteControlsAvailability();
  updateLiveModeNote();
  if (dataSourceValue) dataSourceValue.textContent = "FleetCore Live";
  if (dataSourceBadge) dataSourceBadge.textContent = "Live Data";
  addLog(
    liveCommandAuthority
      ? "FleetCore server acquired. Command authority granted — Set Waypoint, Cancel Route, Pause, and Time Warp now command the real fleet."
      : "FleetCore server acquired. Rendering live world state (read-only)."
  );
}

function capitalizeStatus(status) {
  if (!status) return null;
  return status.charAt(0).toUpperCase() + status.slice(1);
}

// The one place live snapshots turn into Fleet Motion's own internal state
// shape. Deliberately does NOT go through applyCanonicalFleetState(): that
// function also resets trails (createInitialTrails()) and the current
// selection (selectedShipId) on every call, which is correct for a one-time
// restore-from-storage but would fight syncExternalSelection() and erase
// trail history every time a new snapshot arrives (about once a second).
// Updating position/heading/speed fields directly and calling the same
// updateFleetMarkers()/updateStatus() the local physics loop already uses
// keeps trails accumulating and the current selection untouched, and
// reuses Fleet Motion's existing persistFleetState() write path unchanged
// -- Periscope and Bridge inherit live data through the same
// MonadFleetState contract they already read, with no changes on their end.
// FleetCore's vessel ids never matched Fleet Motion's own local demo ids
// ("escort-alpha" vs "vessel.scout-alpha"). An earlier version of this
// function matched incoming vessels onto a fixed local roster by name
// keyword instead of array position (position broke for passive traffic:
// FleetCore's snapshot order is alphabetical by id, Fleet Motion's own
// contactStates order wasn't, so positional matching silently paired
// "DHOW LANTERN" with whatever vessel happened to be at that index -- e.g.
// the real Coaster Qeshm's position). Using each real vessel's own id
// directly (see escortStates/contactStates below) sidesteps matching
// altogether -- there's nothing to mismatch -- and also removes the fixed
// roster's 3+4 cap on how many vessels could ever be shown at once.
function applyLiveSnapshot(snapshot) {
  const vessels = snapshot.vessels || [];
  const flagshipVessel = vessels.find((vessel) => vessel.kind === "flagship");
  const scoutVessels = vessels.filter((vessel) => vessel.kind === "scout");
  const passiveVessels = vessels.filter((vessel) => vessel.kind === "passive-traffic");

  if (flagshipVessel) {
    flagship = clonePoint(flagshipVessel.position) || flagship;
    headingDegrees = flagshipVessel.course ?? headingDegrees;
    currentSpeedKmh = Number(flagshipVessel.speed_mps || 0) * LIVE_KMH_PER_MPS;
    lastStatus = capitalizeStatus(flagshipVessel.status) || lastStatus;
    liveFlagshipId = flagshipVessel.id || liveFlagshipId;
    // Server truth for the course line and the Destination/Cancel Route
    // readouts, replacing the local guesses those fields hold in
    // non-live mode. Empty route means "no active course" -- matches
    // world.rs's own set-route handling (empty route -> Holding).
    routeQueue = clonePoints(flagshipVessel.route);
    destination = routeQueue[0] || null;
    finalDestination = routeQueue.length ? routeQueue[routeQueue.length - 1] : null;
  }

  // escortStates/contactStates hold every real scout/passive vessel
  // FleetCore reports in live mode -- not matched against, or capped by,
  // the fixed 3+4 local demo roster (FORMATION/NPC_CONTACTS) non-live mode
  // uses. Earlier versions of this function matched incoming vessels onto
  // that fixed roster (by name keyword, to avoid a positional-order
  // mismatch bug -- see git history), which meant only 7 vessels could
  // ever be visible here regardless of how many actually existed in
  // FleetCore, and only if their callsigns happened to end in one of the
  // roster's own names (ALPHA, LANTERN, ...). Using each real vessel's own
  // id/position directly sidesteps the matching problem entirely (nothing
  // to mismatch) and removes the cap -- Periscope and Bridge inherit the
  // full real list for free through the same MonadFleetState contract,
  // with no changes needed on their end.
  escortStates = scoutVessels.map((vessel) => ({
    id: vessel.id,
    name: vessel.callsign || vessel.name,
    position: clonePoint(vessel.position),
    headingDegrees: vessel.course ?? null,
    speedKmh: Number(vessel.speed_mps || 0) * LIVE_KMH_PER_MPS,
    blocked: false
  }));

  contactStates = passiveVessels.map((vessel) => ({
    id: vessel.id,
    name: vessel.callsign || vessel.name,
    role: "passive traffic",
    position: clonePoint(vessel.position),
    headingDegrees: vessel.course ?? null,
    speedKmh: Number(vessel.speed_mps || 0) * LIVE_KMH_PER_MPS,
    status: capitalizeStatus(vessel.status) || "Transiting"
  }));

  simulationClockSeconds = Number(snapshot.tick) || simulationClockSeconds;
  liveClockState = snapshot.clock_state || liveClockState;
  const liveScale = Number(snapshot.time_scale) || lastMovingWarp || 1;
  lastMovingWarp = liveScale;
  // timeWarp is the UI's single "effective speed" number (0 = paused) in
  // both modes -- clock_state carries the pause bit here since, unlike
  // local sim, a live world can be paused at any nonzero time_scale.
  timeWarp = liveClockState === "paused" ? 0 : liveScale;
  lastNavigationMessage = "Live FleetCore feed";

  if (!liveMapCentered && flagshipVessel) {
    liveMapCentered = true;
    map.setView([flagshipVessel.position.lat, flagshipVessel.position.lng], 7);
  }

  updateFleetMarkers();
  updateStatus();
}

function clearPersistedFleetState() {
  localStorage.removeItem(FLEET_STATE_STORAGE_KEY);
  lastPersistedAt = null;
  updateLastSavedIndicator();
}


function formatSavedTimestamp(value) {
  if (!value) {
    return "Not saved";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Saved";
  }
  return date.toLocaleString([], {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
}

function stateJsonFromStorage() {
  return localStorage.getItem(FLEET_STATE_STORAGE_KEY) || JSON.stringify(createCanonicalFleetState(), null, 2);
}

function updateStateInspector() {
  if (!stateSchemaValue) {
    return;
  }
  const routeLegs = routeQueue.length;
  const waypointCount = waypoints.length;
  const mode = currentEscortMode();
  stateSchemaValue.textContent = `v${FLEET_STATE_SCHEMA_VERSION}`;
  stateSavedValue.textContent = persistenceSuspended ? "Cleared this session" : formatSavedTimestamp(lastPersistedAt);
  statePresetValue.textContent = SCENARIO_PRESETS[activePresetId]?.label || activePresetId || "Manual";
  stateFlagshipValue.textContent = `${formatPosition(flagship)} / ${headingDegrees === null ? "--" : `${Math.round(headingDegrees)} deg`}`;
  stateMotionValue.textContent = `${formatSpeed(currentSpeedKmh)} / ${timeWarp === 0 ? "paused" : `${timeWarp}x`}`;
  stateRouteValue.textContent = `${routeLegs} leg${routeLegs === 1 ? "" : "s"} / ${waypointCount} waypoint${waypointCount === 1 ? "" : "s"}`;
  stateEscortValue.textContent = `${mode.label} / ${escortStates.length} ships`;
  if (stateContactValue) {
    stateContactValue.textContent = `${contactStates.length} passive`;
  }
  stateSelectionValue.textContent = getSelectedShip().name;
}

function copyStateJson() {
  persistFleetState(true);
  const json = stateJsonFromStorage();
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(json).catch(() => {});
  }
  addLog("Persistent state JSON copied.");
  updateStateInspector();
}

function downloadStateJson() {
  persistFleetState(true);
  const json = stateJsonFromStorage();
  const blob = new Blob([json.endsWith("\n") ? json : `${json}\n`], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `fleet-motion-state-${safeFilename(activePresetId || "manual")}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  addLog("Persistent state JSON download prepared.");
  updateStateInspector();
}

function clearSavedStateFromControl() {
  if (!window.confirm("Clear the saved Fleet Motion state from this browser? Autosave will pause until a forced export or page reload.")) {
    return;
  }
  clearPersistedFleetState();
  persistenceSuspended = true;
  addLog("Persisted fleet state cleared for this browser session.");
  updateStateInspector();
}


function reloadPersistedFleetStateFromControl() {
  const restored = restoreFleetState();
  if (!restored) {
    window.alert("No saved fleet state is available yet.");
    addLog("No persisted fleet state available to reload.");
    updateStatus();
    return;
  }
  addLog("Fleet state reloaded from persistence store.");
  flashAt(flagship, "feedback-pulse reset");
  updateFleetMarkers();
  updateStatus();
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

function pointAtDistance(start, bearing, distance) {
  const earthRadiusKm = 6371;
  const angularDistance = distance / earthRadiusKm;
  const bearingRadians = toRadians(bearing);
  const startLat = toRadians(start.lat);
  const startLng = toRadians(start.lng);
  const endLat = Math.asin(
    Math.sin(startLat) * Math.cos(angularDistance) +
      Math.cos(startLat) * Math.sin(angularDistance) * Math.cos(bearingRadians)
  );
  const endLng = startLng + Math.atan2(
    Math.sin(bearingRadians) * Math.sin(angularDistance) * Math.cos(startLat),
    Math.cos(angularDistance) - Math.sin(startLat) * Math.sin(endLat)
  );
  return {
    lat: toDegrees(endLat),
    lng: ((toDegrees(endLng) + 540) % 360) - 180
  };
}

function pointInOperationBounds(point) {
  return (
    point.lat >= NPC_OPERATION_BOUNDS.south &&
    point.lat <= NPC_OPERATION_BOUNDS.north &&
    point.lng >= NPC_OPERATION_BOUNDS.west &&
    point.lng <= NPC_OPERATION_BOUNDS.east
  );
}

function contactCanOccupy(point) {
  return pointInOperationBounds(point) && !LAND_ZONES.some((zone) => pointInZone(point, zone));
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
  const contact = contactStates.find((ship) => ship.id === id);
  if (contact) {
    return { ...contact.position };
  }
  // escortStates[0] as a last-resort fallback assumes at least one escort
  // exists -- true by construction in local-sim mode (FORMATION always has
  // 3) and in practice in live mode (FleetCore's despawn-vessel refuses to
  // remove scouts), but not guaranteed by anything that would stop a
  // custom/edited seed file from shipping zero scouts. Fall back to the
  // flagship's own position rather than throwing on escortStates[0] being
  // undefined.
  const escort = escortStates.find((ship) => ship.id === id) || escortStates[0];
  return escort ? { ...escort.position } : { ...flagship };
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
  const contact = contactStates.find((ship) => ship.id === selectedShipId);
  if (contact) {
    return {
      id: contact.id,
      name: contact.name,
      kind: "contact",
      role: contact.role,
      position: getShipPosition(contact.id),
      speedKmh: contact.speedKmh,
      headingDegrees: contact.headingDegrees,
      status: contact.status,
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
  // trailLayers/trailColors are sized for the fixed 3-escort local roster
  // (FORMATION.length + 1). In live mode escortStates can hold many more
  // real scout vessels, so cap here rather than index out of bounds --
  // per-vessel trails for live mode's dynamic roster aren't attempted,
  // only the flagship's own trail (index 0, always synced above) matters
  // operationally there.
  escortStates.slice(0, trailLayers.length - 1).forEach((escort, index) => {
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
  const contactHeadings = contactStates
    .map((contact) => `${contact.id}:${Math.round(contact.headingDegrees)}`)
    .join("|");
  if (
    renderedHeading === heading &&
    renderedSelection === selectedShipId &&
    renderedEscortHeadings === escortHeadings &&
    renderedContactHeadings === contactHeadings
  ) {
    return;
  }
  renderedHeading = heading;
  renderedSelection = selectedShipId;
  renderedEscortHeadings = escortHeadings;
  renderedContactHeadings = contactHeadings;
  flagshipMarker.setIcon(shipIcon("flagship", selectedShipId === "monad", heading));
  escortMarkers.forEach((marker, index) => {
    const escort = escortStates[index];
    const escortHeading = Math.round(escort.headingDegrees === null ? heading : escort.headingDegrees);
    marker.setIcon(shipIcon("escort", selectedShipId === escort.id, escortHeading));
  });
  if (liveMode) {
    renderLiveVessels();
  } else {
    escortMarkers.forEach((marker, index) => {
      const escort = escortStates[index];
      marker.setIcon(shipIcon("escort", selectedShipId === escort.id, Math.round(escort.headingDegrees === null ? heading : escort.headingDegrees)));
    });
    contactMarkers.forEach((marker, index) => {
      const contact = contactStates[index];
      marker.setIcon(contactIcon(selectedShipId === contact.id, Math.round(contact.headingDegrees)));
    });
  }
}

// Live mode's dynamic counterpart to the escortMarkers/contactMarkers
// forEach loops above -- reconciles one real Leaflet marker per vessel id
// currently in escortStates/contactStates (which in live mode hold every
// real scout/passive vessel FleetCore reports, not a fixed 3+4 slot
// roster). Markers persist across calls (keyed in liveVesselMarkers by
// vessel id) so repeated snapshots update existing markers in place
// instead of flickering; a vessel id no longer present gets its marker
// removed. First call hides the original fixed-roster markers/links once,
// since indexing into those fixed-length arrays would only ever show the
// first 3/4 real vessels.
function renderLiveVessels() {
  if (!liveRenderingInitialized) {
    escortMarkers.forEach((marker) => map.removeLayer(marker));
    contactMarkers.forEach((marker) => map.removeLayer(marker));
    formationLinks.forEach((link) => map.removeLayer(link));
    liveRenderingInitialized = true;
  }

  const seen = new Set();
  const upsert = (entity, kind) => {
    seen.add(entity.id);
    // FleetCore's own Vessel struct makes position non-optional, so this
    // should never actually be null -- but a single bad entry throwing
    // here would abort the whole forEach mid-loop, silently freezing
    // every other live marker (including the removal pass below, which
    // never runs). Skipping just this one entity is strictly safer than
    // trusting the wire format to stay well-formed forever.
    if (!entity.position || !Number.isFinite(entity.position.lat) || !Number.isFinite(entity.position.lng)) {
      console.warn("Fleet Motion: skipping live vessel with invalid position", entity.id);
      return;
    }
    const heading = Math.round(entity.headingDegrees === null || entity.headingDegrees === undefined ? 0 : entity.headingDegrees);
    const selected = selectedShipId === entity.id;
    let entry = liveVesselMarkers.get(entity.id);
    if (!entry) {
      const marker = L.marker([entity.position.lat, entity.position.lng], {
        icon: kind === "escort" ? shipIcon("escort", selected, heading) : contactIcon(selected, heading),
        title: entity.name
      })
        .bindTooltip(entity.name, kind === "escort"
          ? { direction: "top", offset: [0, -14] }
          : { permanent: true, direction: "bottom", offset: [0, 12], className: "contact-label" })
        .addTo(map);
      marker.on("click", (event) => {
        L.DomEvent.stopPropagation(event);
        selectShip(entity.id);
      });
      liveVesselMarkers.set(entity.id, { marker });
    } else {
      entry.marker.setLatLng([entity.position.lat, entity.position.lng]);
      entry.marker.setIcon(kind === "escort" ? shipIcon("escort", selected, heading) : contactIcon(selected, heading));
      entry.marker.setTooltipContent(entity.name);
    }
  };

  escortStates.forEach((escort) => upsert(escort, "escort"));
  contactStates.forEach((contact) => upsert(contact, "contact"));

  for (const [id, entry] of liveVesselMarkers) {
    if (!seen.has(id)) {
      map.removeLayer(entry.marker);
      liveVesselMarkers.delete(id);
    }
  }
}

function updateFleetMarkers() {
  flagshipMarker.setLatLng([flagship.lat, flagship.lng]);
  if (liveMode) {
    renderLiveVessels();
  } else {
    escortMarkers.forEach((marker, index) => {
      const escort = escortStates[index];
      marker.setLatLng([escort.position.lat, escort.position.lng]);
      formationLinks[index].setLatLngs([
        [flagship.lat, flagship.lng],
        [escort.position.lat, escort.position.lng]
      ]);
    });
    contactMarkers.forEach((marker, index) => {
      const contact = contactStates[index];
      marker.setLatLng([contact.position.lat, contact.position.lng]);
    });
  }

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
    : selected.kind === "contact"
      ? selected.status
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
    : selected.kind === "contact"
      ? selected.role
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
  if (!INTERNAL_FEATURES.scenarioTools) {
    return;
  }
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

// Quarantine: scenario editor/evaluator support is intentionally out of the
// normal Fleet Motion loop. Keep it disabled until the navigation engine is
// mature enough to justify scenario-management UI again.
function buildScenarioArtifact() {
  if (!INTERNAL_FEATURES.scenarioTools) {
    return null;
  }
  const activeRoute = [
    ...(destination ? [{ ...destination }] : []),
    ...routeQueue.slice(destination ? 1 : 0)
  ];
  const artifact = {
    toy: "fleet-motion",
    schemaVersion: 1,
    exportedAt: new Date().toISOString(),
    scenario: {
      area: "Arabian Sea",
      presetId: activePresetId,
      presetLabel: SCENARIO_PRESETS[activePresetId]?.label || "Freeplay / Manual",
      variantName: variantNameInput?.value.trim() || activePresetId || "manual",
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
      feltGood: feltGoodInput?.value.trim() || "",
      feltWrong: feltWrongInput?.value.trim() || "",
      suggestedChange: suggestedChangeInput?.value.trim() || ""
    },
    constraints: [
      "Standalone browser toy",
      "Navigation loop first",
      "Scenario tools quarantined",
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
  if (!INTERNAL_FEATURES.scenarioTools) {
    return;
  }
  lastScenarioExport = `${JSON.stringify(buildScenarioArtifact(), null, 2)}\n`;
  if (scenarioExportOutput) {
    scenarioExportOutput.value = lastScenarioExport;
    scenarioExportOutput.focus();
    scenarioExportOutput.select();
  }
  if (downloadScenarioButton) {
    downloadScenarioButton.disabled = false;
  }
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(lastScenarioExport).catch(() => {});
  }
  addLog("Scenario JSON exported for designer handoff.");
}

function safeFilename(value) {
  return (value || "fleet-motion")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80) || "fleet-motion";
}

function downloadScenarioExport() {
  if (!INTERNAL_FEATURES.scenarioTools || !lastScenarioExport) {
    return;
  }
  const blob = new Blob([lastScenarioExport], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${safeFilename(variantNameInput?.value || activePresetId)}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  addLog("Scenario JSON download prepared.");
}

function loadPassiveOpeningRoute() {
  const preset = SCENARIO_PRESETS.arabian_sea_watch;
  activePresetId = preset.id;
  if (scenarioPresetSelect) scenarioPresetSelect.value = preset.id;
  designSettings = { ...preset.settings };
  escortModeIndex = escortModeIndexFor(preset.escortModeId);
  if (variantNameInput) variantNameInput.value = preset.variantName;
  if (suggestedChangeInput) suggestedChangeInput.placeholder = preset.notePrompt;
  syncDesignControls();
  waypoints = [];
  selectedWaypointIndex = null;
  finalDestination = { ...preset.destination };
  routeQueue = [finalDestination];
  destination = routeQueue[0];
  headingDegrees = bearingDegrees(flagship, destination);
  lastStatus = "Underway";
  lastNavigationMessage = "Clear";
  addLog("Opening route loaded: Arabian Sea Watch.");
}

function completeIntro() {
  document.body.classList.remove("is-opening");
  if (openingOverlay) {
    openingOverlay.classList.add("complete");
  }
}

function startOpeningSequence({ loadOpeningRoute = true } = {}) {
  if (loadOpeningRoute) {
    loadPassiveOpeningRoute();
  }
  updateFleetMarkers();
  updateStatus();
  const focusPoint = loadOpeningRoute ? HOME : flagship;
  window.setTimeout(() => {
    map.flyTo([focusPoint.lat, focusPoint.lng], 7, {
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
  if (scenarioPresetSelect) scenarioPresetSelect.value = preset.id;

  if (!resetFleet({ requireConfirmation: true })) {
    return;
  }
  designSettings = { ...preset.settings };
  escortModeIndex = escortModeIndexFor(preset.escortModeId);
  syncDesignControls();

  if (variantNameInput) variantNameInput.value = preset.variantName;
  feltGoodInput.value = "";
  feltWrongInput.value = "";
  suggestedChangeInput.value = "";
  if (suggestedChangeInput) suggestedChangeInput.placeholder = preset.notePrompt;
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
  persistFleetState(true);
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
  if (trafficStatus) {
    trafficStatus.textContent = `${contactStates.length} passive contact${contactStates.length === 1 ? "" : "s"}`;
  }
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
    ? (liveMode ? "Click map to add waypoints; click Add Waypoint again to send" : "Click map to place one waypoint")
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
  // Live mode gates these on command authority (set once by
  // updateLiveWriteControlsAvailability, which calls back into this
  // function) on top of the same state checks non-live mode already used
  // -- a live visitor without a token sees the same disabled state as
  // before; one with a token sees exactly local mode's own logic.
  const liveWriteBlocked = liveMode && !liveCommandAuthority;
  pauseButton.disabled = liveMode ? liveWriteBlocked : (!destination && timeWarp !== 0);
  waypointButton.classList.toggle("active", waypointMode);
  suggestDetourButton.hidden = !pendingDetour && !suggestedDetour;
  acceptDetourButton.hidden = !suggestedDetour;
  suggestDetourButton.disabled = !pendingDetour || Boolean(suggestedDetour);
  acceptDetourButton.disabled = !suggestedDetour;
  undoWaypointButton.disabled = liveWriteBlocked || !waypoints.length;
  removeWaypointButton.disabled = liveWriteBlocked || selectedWaypointIndex === null || !waypoints[selectedWaypointIndex];
  clearWaypointsButton.disabled = liveWriteBlocked || (!waypoints.length && !routeQueue.length && !destination);
  cancelRouteButton.disabled = liveWriteBlocked || (!destination && !routeQueue.length);
  escortModeButton.textContent = `Escort: ${mode.label}`;
  updateWarpControls();
  updateMarkerIcons();
  updateShipInfo();
  persistFleetState();
  updateStateInspector();
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
  // The LAND_ZONES hazard check is a local-simulation-only heuristic --
  // FleetCore has no terrain model, so a real vessel_id isn't actually
  // blocked by these boxes. Rejecting a live waypoint against a rule the
  // server doesn't enforce would just be a client-side lie about what's
  // possible; skip it live and let the staged route go to the server as
  // clicked, same as toys/bridge-station-3.0/ already does.
  const navigationCheck = liveMode ? { clear: true, reason: "Clear" } : checkNavigation(start, waypoint);
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
  // Live mode keeps waypointMode armed across clicks so the button is a
  // press-to-start/press-to-send toggle (see waypointButton's own click
  // handler) -- one click per waypoint, no Shift needed, so this works on
  // touch. Local-sim mode keeps its original one-shot-per-press behavior.
  if (oneShotMode && !liveMode) {
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

function turnPassiveContact(contact) {
  contact.headingDegrees = (contact.headingDegrees + 105 + Math.abs(Math.sin(simulationClockSeconds + contact.id.length)) * 80) % 360;
  contact.status = "Course adjusted";
  contact.lastTurnSeconds = simulationClockSeconds;
}

function advancePassiveContact(contact, elapsedSeconds) {
  const stepDistance = contact.speedKmh * timeWarp * (elapsedSeconds / 3600);
  if (stepDistance <= 0) {
    return;
  }

  const nextPosition = pointAtDistance(contact.position, contact.headingDegrees, stepDistance);
  if (!contactCanOccupy(nextPosition)) {
    turnPassiveContact(contact);
    return;
  }

  contact.position = nextPosition;
  contact.status = simulationClockSeconds - contact.lastTurnSeconds < 18
    ? "Settling on new course"
    : "Transiting";
}

function advanceFleet(elapsedSeconds) {
  if (liveMode || timeWarp === 0) {
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
  contactStates.forEach((contact) => advancePassiveContact(contact, elapsedSeconds));
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
  syncExternalSelection();
  advanceFleet(elapsedSeconds);
  window.requestAnimationFrame(animationFrame);
}

function setTimeWarp(nextWarp) {
  if (liveMode) {
    sendLiveTimeWarp(nextWarp);
    return;
  }
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

function resetFleet({ requireConfirmation = true } = {}) {
  if (requireConfirmation && !window.confirm("Reset Fleet Motion to the documented Arabian Sea watch baseline? This clears the persisted voyage.")) {
    return false;
  }
  flagship = { ...HOME };
  clearRoutePlan();
  timeWarp = 1;
  lastMovingWarp = 1;
  currentSpeedKmh = 0;
  simulationClockSeconds = 0;
  escortStates = createEscortStates();
  contactStates = createContactStates();
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
  renderedContactHeadings = null;
  createInitialTrails();
  addLog("Fleet reset to Arabian Sea watch station.");
  flashAt(flagship, "feedback-pulse reset");
  updateFleetMarkers();
  updateStatus();
  map.setView([HOME.lat, HOME.lng], 7);
  persistFleetState(true);
  return true;
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
  if (liveMode) {
    sendLiveCancelRoute();
    return;
  }
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
  if (liveMode) {
    if (waypointMode || event.originalEvent.shiftKey) {
      addWaypoint(event.latlng);
      return;
    }
    sendLiveRoute(event.latlng);
    return;
  }
  if (waypointMode || event.originalEvent.shiftKey) {
    addWaypoint(event.latlng);
    return;
  }
  setDestination(event.latlng);
});

// The one write path into live mode's navigation. Mirrors local mode's
// setDestination() gesture exactly (staged waypoints via addWaypoint(),
// finalized on a plain click) but sends the whole staged route -- FleetCore's
// set-route takes a real Vec<Position>, not just one point
// (fleetcore/src/command.rs) -- as one Command over the same WebSocket the
// snapshots arrive on, instead of running local route physics. The next
// broadcast snapshot is what actually moves MONAD; local waypoint markers
// are cleared immediately since they were only ever a staging UI, not the
// live truth. waypointButton/pauseButton/warp are only enabled when
// liveCommandAuthority is true (updateLiveWriteControlsAvailability), so
// reaching here means authority was granted.
function sendLiveRoute(latlng) {
  if (!liveCommandAuthority || !liveFlagshipId || !liveSocket || liveSocket.readyState !== WebSocket.OPEN) {
    return;
  }
  const finalPoint = { lat: latlng.lat, lng: latlng.lng };
  const route = [...waypoints, finalPoint];
  liveSocket.send(JSON.stringify({ type: "set-route", vessel_id: liveFlagshipId, route }));
  waypointMode = false;
  waypoints = [];
  selectedWaypointIndex = null;
  redrawWaypoints();
  flashAt(finalPoint);
  addLog(`Route command sent — ${route.length} leg${route.length === 1 ? "" : "s"}. Awaiting live world response.`);
  updateStatus();
}

// Finalizes waypointButton's armed multi-click staging (see addWaypoint's
// liveMode branch): every staged point becomes the route, with no extra
// "final click" point needed since the last click already staged one.
function sendStagedLiveRoute() {
  if (!liveCommandAuthority || !liveFlagshipId || !liveSocket || liveSocket.readyState !== WebSocket.OPEN) {
    return;
  }
  if (!waypoints.length) return;
  const route = waypoints.map((point) => ({ lat: point.lat, lng: point.lng }));
  liveSocket.send(JSON.stringify({ type: "set-route", vessel_id: liveFlagshipId, route }));
  waypointMode = false;
  waypoints = [];
  selectedWaypointIndex = null;
  redrawWaypoints();
  flashAt(route[route.length - 1]);
  addLog(`Route command sent — ${route.length} leg${route.length === 1 ? "" : "s"}. Awaiting live world response.`);
  updateStatus();
}

// Real cancel: sends an empty route, which world.rs's set-route handler
// treats as "clear route, go to Holding" -- not a local-only reset like
// clearRoutePlan() (which only clears the staged, not-yet-sent waypoints
// list and needs no command at all).
function sendLiveCancelRoute() {
  if (!liveCommandAuthority || !liveFlagshipId || !liveSocket || liveSocket.readyState !== WebSocket.OPEN) {
    return;
  }
  liveSocket.send(JSON.stringify({ type: "set-route", vessel_id: liveFlagshipId, route: [] }));
  waypointMode = false;
  waypoints = [];
  selectedWaypointIndex = null;
  redrawWaypoints();
  addLog("Cancel Route command sent — awaiting live world response.");
  updateStatus();
}

function sendLiveTimeWarp(nextWarp) {
  if (!liveCommandAuthority || !liveSocket || liveSocket.readyState !== WebSocket.OPEN) {
    return;
  }
  if (nextWarp === 0) {
    liveSocket.send(JSON.stringify({ type: "pause-clock" }));
    addLog("Pause command sent.");
    return;
  }
  // set-time-scale doesn't itself resume a paused clock (world.rs keeps
  // the two orthogonal), so a paused world needs both commands to actually
  // start moving again at the requested speed.
  if (liveClockState === "paused") {
    liveSocket.send(JSON.stringify({ type: "resume-clock" }));
  }
  liveSocket.send(JSON.stringify({ type: "set-time-scale", scale: nextWarp }));
  addLog(`Time-scale command sent — ${nextWarp}x. This affects every connected visitor's clock, not just this view.`);
}
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
contactMarkers.forEach((marker, index) => {
  marker.on("click", (event) => {
    L.DomEvent.stopPropagation(event);
    selectShip(NPC_CONTACTS[index].id);
  });
});

pauseButton.addEventListener("click", () => {
  setTimeWarp(timeWarp === 0 ? lastMovingWarp : 0);
});

waypointButton.addEventListener("click", () => {
  if (liveMode) {
    waypointMode = !waypointMode;
    if (waypointMode) {
      addLog("Waypoint placement armed — click the map to add points, click Add Waypoint again to send.");
    } else if (waypoints.length) {
      sendStagedLiveRoute();
    } else {
      addLog("Waypoint placement canceled — no points staged.");
    }
    updateStatus();
    return;
  }
  waypointMode = true;
  addLog("Waypoint placement armed for next map click.");
  updateStatus();
});

suggestDetourButton.addEventListener("click", buildSuggestedDetour);

acceptDetourButton.addEventListener("click", acceptSuggestedDetour);

escortModeButton.addEventListener("click", cycleEscortMode);

if (INTERNAL_FEATURES.scenarioTools && applyPresetButton) {
  applyPresetButton.addEventListener("click", () => {
    applyScenarioPreset(scenarioPresetSelect.value);
  });
}

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

if (INTERNAL_FEATURES.scenarioTools) {
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
}

copyStateButton?.addEventListener("click", copyStateJson);

downloadStateButton?.addEventListener("click", downloadStateJson);

clearStateButton?.addEventListener("click", clearSavedStateFromControl);

homeButton.addEventListener("click", () => {
  waypointMode = false;
  setDestination(HOME);
  map.panTo([HOME.lat, HOME.lng]);
});

// resetFleet() already builds exactly this tableau (flagship at HOME,
// escorts in formation, contacts scattered) -- it just had no visible
// entry point before now, only reachable through the quarantined scenario-
// preset UI (INTERNAL_FEATURES.scenarioTools). This exposes it directly,
// without touching that quarantine.
resetToBaselineButton.addEventListener("click", () => {
  resetFleet({ requireConfirmation: true });
});

resetButton.addEventListener("click", reloadPersistedFleetStateFromControl);

skipIntroButton.addEventListener("click", completeIntro);

createInitialTrails();
syncDesignControls();
updateStateInspector();
addLog("Fleet motion toy online. Captain's Log uses local browser time.");
restoredFromPersistentState = restoreFleetState();
if (restoredFromPersistentState) {
  addLog("Persisted fleet state restored.");
  startOpeningSequence({ loadOpeningRoute: false });
} else {
  addLog("No persisted fleet state found; opening baseline route loaded.");
  startOpeningSequence({ loadOpeningRoute: true });
}
window.requestAnimationFrame(animationFrame);
// Live is the default now (Admiral's call, 2026-07-11): every page load
// attempts a FleetCore connection, not just ?live=1 ones. Local simulation
// still starts immediately above and keeps running uninterrupted unless/
// until a snapshot actually arrives -- if fleetcore-serve is unreachable
// or the public Caddy/rock64 proxy isn't finished yet, this fails closed
// exactly as before (silently, after LIVE_CONNECT_TIMEOUT_MS), just no
// longer gated behind a query param. Accepted tradeoff: a failed
// connection attempt logs a browser-native console error that no
// application code can suppress -- previously the reason this was opt-in
// only. ?fleetcoreServer= still overrides the server URL if needed.
connectFleetCoreLive();
