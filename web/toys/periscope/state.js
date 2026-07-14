// Periscope state/decision layer -- bearing, contact sourcing, selection,
// and interpolation. No rendering here; see scene.js for the three.js layer
// and app.js for DOM wiring. Ported from the pre-Mk-IV Canvas 2D app.js with
// the render-only pieces (screen-space projection) removed.

export const TAU = Math.PI * 2;
export const MAX_RANGE = 14;
export const HORIZON_RATIO = 0.45;

export const OPTICS_TIERS = {
  wide: {
    id: "wide",
    label: "1x wide watch",
    magnification: 1,
    fov: 54,
    spriteBoost: 1,
    backgroundZoom: 1,
    reticleDensity: 1,
  },
  standard: {
    id: "standard",
    label: "4x observation",
    magnification: 4,
    fov: 28,
    spriteBoost: 1.35,
    backgroundZoom: 1.13,
    reticleDensity: 1.25,
  },
  close: {
    id: "close",
    label: "10x inspection",
    magnification: 10,
    fov: 14,
    spriteBoost: 1.72,
    backgroundZoom: 1.28,
    reticleDensity: 1.55,
  },
};

export const ASSET_PATHS = {
  sea: "assets/backgrounds/sea-horizon-mk2.png",
  scout: "assets/sprites/scout-alpha.png",
  vessels: {
    scout: "assets/sprites/vessel-scout-photo.png",
    tanker: "assets/sprites/vessel-tanker-photo.png",
    dhow: "assets/sprites/vessel-dhow-photo.png",
    pilot: "assets/sprites/vessel-pilot-photo.png",
    coaster: "assets/sprites/vessel-coaster-photo.png",
  },
};

export const VESSEL_RENDER_PROFILES = {
  scout: { label: "Scout", sprite: "scout", size: 0.95, waterline: 0.76, haze: 0.88, wake: 0.86, contrast: 1.02 },
  tanker: { label: "Tanker", sprite: "tanker", size: 1.78, waterline: 0.7, haze: 0.84, wake: 1.42, contrast: 0.96 },
  dhow: { label: "Dhow", sprite: "dhow", size: 0.72, waterline: 0.72, haze: 1, wake: 0.52, contrast: 1.08 },
  pilot: { label: "Pilot Boat", sprite: "pilot", size: 0.66, waterline: 0.74, haze: 1, wake: 0.72, contrast: 1.12 },
  coaster: { label: "Coaster", sprite: "coaster", size: 1.14, waterline: 0.72, haze: 0.94, wake: 1.04, contrast: 1 },
  fallback: { label: "Vessel", sprite: "scout", size: 0.92, waterline: 0.74, haze: 0.92, wake: 0.82, contrast: 1 },
};

const DEMO_VESSELS = [
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

// A shared contact's raw bearing/range only changes when Fleet Motion (or
// FleetCore-live) writes a fresh sample -- roughly once a second, not once a
// frame. With no smoothing, a contact visibly steps between writes instead
// of gliding. This caches the last two raw samples per contact id and lerps
// between them over the *observed* gap between updates (falling back to
// Fleet Motion's known ~1.2s write throttle until two real samples land),
// rather than assuming a specific update rate.
const DEFAULT_UPDATE_INTERVAL_MS = 1200;
const interpolationCache = new Map();

function interpolateSharedContacts(rawContacts, now) {
  const seenIds = new Set();
  const result = rawContacts.map((raw) => {
    seenIds.add(raw.id);
    let entry = interpolationCache.get(raw.id);
    if (!entry) {
      entry = {
        rawBearing: raw.bearing,
        rawRange: raw.range,
        fromBearing: raw.bearing,
        toBearing: raw.bearing,
        fromRange: raw.range,
        toRange: raw.range,
        updatedAt: now,
        interval: DEFAULT_UPDATE_INTERVAL_MS,
      };
      interpolationCache.set(raw.id, entry);
    } else if (raw.bearing !== entry.rawBearing || raw.range !== entry.rawRange) {
      const observed = now - entry.updatedAt;
      entry.interval = clamp(observed, 400, 4000);
      entry.fromBearing = entry.toBearing;
      entry.fromRange = entry.toRange;
      entry.toBearing = raw.bearing;
      entry.toRange = raw.range;
      entry.rawBearing = raw.bearing;
      entry.rawRange = raw.range;
      entry.updatedAt = now;
    }
    const t = clamp((now - entry.updatedAt) / entry.interval, 0, 1);
    const bearing = normalizeDegrees(entry.fromBearing + shortestDelta(entry.fromBearing, entry.toBearing) * t);
    const range = entry.fromRange + (entry.toRange - entry.fromRange) * t;
    return { ...raw, bearing, range };
  });
  for (const id of interpolationCache.keys()) {
    if (!seenIds.has(id)) interpolationCache.delete(id);
  }
  return result;
}

export function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

export function normalizeDegrees(value) {
  return ((value % 360) + 360) % 360;
}

export function shortestDelta(from, to) {
  let delta = normalizeDegrees(to) - normalizeDegrees(from);
  if (delta > 180) delta -= 360;
  if (delta < -180) delta += 360;
  return delta;
}

export function formatBearing(value) {
  return `${String(Math.round(normalizeDegrees(value))).padStart(3, "0")}°`;
}

export function currentOptics(periscope) {
  return OPTICS_TIERS[periscope.opticsMode] || OPTICS_TIERS.wide;
}

export function vesselProfile(contact) {
  const text = `${contact.class || ""} ${contact.mission || ""} ${contact.callsign || ""}`.toLowerCase();
  if (text.includes("tanker")) return VESSEL_RENDER_PROFILES.tanker;
  if (text.includes("dhow")) return VESSEL_RENDER_PROFILES.dhow;
  if (text.includes("pilot")) return VESSEL_RENDER_PROFILES.pilot;
  if (text.includes("coaster") || text.includes("freighter")) return VESSEL_RENDER_PROFILES.coaster;
  if (text.includes("scout") || text.includes("escort")) return VESSEL_RENDER_PROFILES.scout;
  return VESSEL_RENDER_PROFILES.fallback;
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

function localContacts(elapsedSeconds) {
  return DEMO_VESSELS.map((vessel) => vesselState(vessel, elapsedSeconds));
}

function sharedContacts(periscope) {
  const sharedState = window.MonadFleetState?.read?.();
  const contacts = sharedState && window.MonadFleetState?.toScoutContacts
    ? window.MonadFleetState.toScoutContacts(sharedState)
    : [];
  if (!contacts.length) {
    periscope.dataSource = null;
    return null;
  }
  periscope.dataSource = sharedState.dataSource || "local-simulation";
  return contacts;
}

export function currentContacts(periscope, elapsedSeconds, now) {
  const shared = sharedContacts(periscope);
  if (shared) return interpolateSharedContacts(shared, now);
  return localContacts(elapsedSeconds);
}

export function projectContact(periscope, contact) {
  const optics = currentOptics(periscope);
  const profile = vesselProfile(contact);
  const relative = shortestDelta(periscope.bearing, contact.bearing);
  const visible = Math.abs(relative) <= optics.fov / 2;
  const rangeRatio = clamp(contact.range / MAX_RANGE, 0, 1);
  return { ...contact, profile, relative, visible, rangeRatio, optics };
}

export function createPeriscopeState() {
  return {
    bearing: 0,
    targetBearing: 0,
    velocity: 0,
    dragging: false,
    lastX: 0,
    lastTime: 0,
    selectedId: null,
    visibleContacts: [],
    dataSource: null,
    opticsMode: "wide",
    acquisitionCue: { contactId: null, startedAt: 0, label: "" },
  };
}

export function triggerAcquisitionCue(periscope, contact, label = "Contact acquired") {
  if (!contact) return;
  periscope.acquisitionCue = {
    contactId: contact.id,
    startedAt: performance.now(),
    label: `${label}: ${contact.callsign}`,
  };
}

// Additive write path into MonadFleetState.selection: a contact picked
// directly in Periscope (rather than acquired from Fleet Motion) only
// matters cross-instrument if it round-trips back into shared state. Only
// fires for contacts sourced from shared state (`contact.source` is set) --
// Periscope's own local demo vessels have no matching id in Fleet Motion's
// state to select.
export function propagateSelection(contact) {
  if (!contact.source) return;
  const sharedState = window.MonadFleetState?.read?.();
  if (!sharedState || sharedState.selection?.selectedShipId === contact.id) return;
  window.MonadFleetState.write({
    ...sharedState,
    selection: { ...sharedState.selection, selectedShipId: contact.id },
  });
}

export function selectVessel(periscope, contact, { propagate = false } = {}) {
  if (!contact) return;
  const changed = periscope.selectedId !== contact.id;
  periscope.selectedId = contact.id;
  if (changed) triggerAcquisitionCue(periscope, contact);
  if (propagate) propagateSelection(contact);
}

// Fleet Motion's own selected ship (if it's one of these contacts) always
// wins over the nearest-range fallback, and re-aims live whenever that
// selection changes.
export function autoAcquireSharedContact(periscope, contacts) {
  const shared = contacts.filter((contact) => contact.source);
  if (!shared.length) return;
  const selected = shared.find((contact) => contact.selected);
  const preferred = selected || shared.slice().sort((first, second) => first.range - second.range)[0];
  const acquireKey = selected ? `selected:${selected.id}` : `nearest:${shared.map((contact) => contact.id).join("|")}`;
  if (periscope.acquiredSourceKey === acquireKey) return;
  periscope.acquiredSourceKey = acquireKey;
  // Only set targetBearing, not bearing itself -- the per-frame smoothing in
  // app.js's tick() is what turns the scope toward it, same as a manual drag
  // release. Setting both here would jump-cut the whole view in one frame
  // instead of swinging to it.
  periscope.targetBearing = normalizeDegrees(preferred.bearing);
  periscope.velocity = 0;
  selectVessel(periscope, preferred);
}

export function tickBearing(periscope) {
  if (!periscope.dragging) {
    periscope.targetBearing = normalizeDegrees(periscope.targetBearing + periscope.velocity);
    periscope.velocity *= 0.94;
    if (Math.abs(periscope.velocity) < 0.003) periscope.velocity = 0;
  }
  periscope.bearing = normalizeDegrees(
    periscope.bearing + shortestDelta(periscope.bearing, periscope.targetBearing) * 0.13
  );
}

export function focusContactForOptics(periscope, contacts) {
  const projected = contacts.map((contact) => projectContact(periscope, contact));
  const selected = projected.find((contact) => contact.id === periscope.selectedId);
  const visible = projected
    .filter((contact) => contact.visible)
    .sort((first, second) => Math.abs(first.relative) - Math.abs(second.relative))[0];
  const nearest = selected || visible || projected
    .slice()
    .sort((first, second) => Math.abs(first.relative) - Math.abs(second.relative))[0];
  if (!nearest) return;
  periscope.targetBearing = normalizeDegrees(nearest.bearing);
  periscope.velocity = 0;
  triggerAcquisitionCue(periscope, nearest, "Optics centered");
}
