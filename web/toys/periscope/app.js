const TAU = Math.PI * 2;
const FIELD_OF_VIEW = 54;
const MAX_RANGE = 14;
const HORIZON_RATIO = 0.45;
const OPTICS_TIERS = {
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
const ASSET_PATHS = {
  sea: "assets/backgrounds/sea-horizon-mk2.png",
  scout: "assets/sprites/scout-alpha.png",
  vessels: {
    scout: "assets/sprites/vessel-scout.svg",
    tanker: "assets/sprites/vessel-tanker.svg",
    dhow: "assets/sprites/vessel-dhow.svg",
    pilot: "assets/sprites/vessel-pilot.svg",
    coaster: "assets/sprites/vessel-coaster.svg",
  },
};

const VESSEL_RENDER_PROFILES = {
  scout: {
    label: "Scout",
    sprite: "scout",
    size: 0.95,
    waterline: 0.76,
    haze: 0.88,
  },
  tanker: {
    label: "Tanker",
    sprite: "tanker",
    size: 1.78,
    waterline: 0.7,
    haze: 0.72,
  },
  dhow: {
    label: "Dhow",
    sprite: "dhow",
    size: 0.72,
    waterline: 0.72,
    haze: 1,
  },
  pilot: {
    label: "Pilot Boat",
    sprite: "pilot",
    size: 0.66,
    waterline: 0.74,
    haze: 1,
  },
  coaster: {
    label: "Coaster",
    sprite: "coaster",
    size: 1.14,
    waterline: 0.72,
    haze: 0.88,
  },
  fallback: {
    label: "Vessel",
    sprite: "scout",
    size: 0.92,
    waterline: 0.74,
    haze: 0.92,
  },
};

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
const dataSourceReadout = document.querySelector("#dataSourceReadout");
const bearingBand = document.querySelector("#bearingBand");
const contactStrip = document.querySelector("#contactStrip");
const detailsButton = document.querySelector("#detailsButton");
const fieldNote = document.querySelector("#fieldNote");
const magnificationReadout = document.querySelector("#magnificationReadout");
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
  contactSourceKey: "",
  acquiredSourceKey: "",
  dataSource: null,
  opticsMode: "wide",
  acquisitionCue: {
    contactId: null,
    startedAt: 0,
    label: "",
  },
};

const assets = {
  sea: loadImage(ASSET_PATHS.sea),
  scout: loadImage(ASSET_PATHS.scout),
  vessels: Object.fromEntries(Object.entries(ASSET_PATHS.vessels).map(([key, path]) => [key, loadImage(path)])),
};

function loadImage(src) {
  const image = new Image();
  const asset = { image, ready: false, failed: false };
  image.onload = () => {
    asset.ready = true;
  };
  image.onerror = () => {
    asset.failed = true;
  };
  image.src = src;
  return asset;
}

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

function currentOptics() {
  return OPTICS_TIERS[state.opticsMode] || OPTICS_TIERS.wide;
}

function vesselProfile(contact) {
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
  return vessels.map((vessel) => vesselState(vessel, elapsedSeconds));
}

function sharedContacts() {
  const sharedState = window.MonadFleetState?.read?.();
  const contacts = sharedState && window.MonadFleetState?.toScoutContacts
    ? window.MonadFleetState.toScoutContacts(sharedState)
    : [];
  if (!contacts.length) {
    state.dataSource = null;
    return null;
  }
  state.dataSource = sharedState.dataSource || "local-simulation";
  return contacts;
}

function currentContacts(elapsedSeconds) {
  return sharedContacts() || localContacts(elapsedSeconds);
}

function autoAcquireSharedContact(contacts) {
  const shared = contacts.filter((contact) => contact.source);
  if (!shared.length) return;
  // Fleet Motion's selected ship (if it's one of these contacts) always wins over
  // the nearest-range fallback, and re-aims live whenever that selection changes.
  const selected = shared.find((contact) => contact.selected);
  const preferred = selected || shared.slice().sort((first, second) => first.range - second.range)[0];
  const acquireKey = selected ? `selected:${selected.id}` : `nearest:${shared.map((contact) => contact.id).join("|")}`;
  if (state.acquiredSourceKey === acquireKey) return;
  state.acquiredSourceKey = acquireKey;
  state.bearing = normalizeDegrees(preferred.bearing);
  state.targetBearing = state.bearing;
  state.velocity = 0;
  selectVessel(preferred);
}

function projectContact(contact) {
  const optics = currentOptics();
  const profile = vesselProfile(contact);
  const relative = shortestDelta(state.bearing, contact.bearing);
  const visible = Math.abs(relative) <= optics.fov / 2;
  const rangeRatio = clamp(contact.range / MAX_RANGE, 0, 1);
  const proximity = 1 - rangeRatio;
  const horizonY = HORIZON_RATIO + 0.035;
  const waterlineY = clamp(horizonY + proximity * 0.19, horizonY, 0.71);
  const baseScale = 0.42 + proximity * 0.52;
  return {
    ...contact,
    profile,
    relative,
    visible,
    x: 0.5 + relative / optics.fov,
    y: waterlineY,
    rangeRatio,
    scale: baseScale * profile.size * optics.spriteBoost,
    optics,
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

function renderProceduralOcean(now) {
  const w = canvas.width;
  const h = canvas.height;
  const horizon = h * HORIZON_RATIO;
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

function renderSeaPlate(now) {
  const w = canvas.width;
  const h = canvas.height;
  const optics = currentOptics();
  if (!assets.sea.ready) {
    renderProceduralOcean(now);
    return;
  }

  const image = assets.sea.image;
  const sourceRatio = image.width / image.height;
  let drawHeight = h * optics.backgroundZoom;
  let drawWidth = h * sourceRatio;
  if (drawWidth < w) {
    drawWidth = w;
    drawHeight = w / sourceRatio;
  }
  drawWidth *= optics.backgroundZoom;
  drawHeight *= optics.backgroundZoom;

  const horizonCorrection = h * (0.025 + (optics.magnification - 1) * 0.002);
  const drawY = (h - drawHeight) * 0.5 + horizonCorrection;
  const pan = normalizeDegrees(state.bearing) / 360;
  const period = drawWidth;
  const drift = (now * 0.0022 / optics.backgroundZoom) % period;
  let drawX = -((pan * period + drift) % period);

  ctx.save();
  ctx.filter = `contrast(${(1.04 + optics.magnification * 0.004).toFixed(3)}) saturate(0.9) brightness(${(0.87 - optics.magnification * 0.008).toFixed(3)})`;
  while (drawX < w) {
    ctx.drawImage(image, drawX, drawY, drawWidth, drawHeight);
    drawX += period;
  }
  ctx.restore();
}

function renderAtmosphere(now) {
  const w = canvas.width;
  const h = canvas.height;
  const optics = currentOptics();
  const horizon = h * HORIZON_RATIO;

  const haze = ctx.createLinearGradient(0, horizon - h * 0.08, 0, horizon + h * 0.17);
  haze.addColorStop(0, "rgba(205, 222, 218, 0.02)");
  haze.addColorStop(0.45, "rgba(220, 225, 213, 0.22)");
  haze.addColorStop(1, "rgba(20, 42, 48, 0)");
  ctx.fillStyle = haze;
  ctx.fillRect(0, horizon - h * 0.1, w, h * 0.3);

  ctx.fillStyle = "rgba(240, 219, 173, 0.18)";
  ctx.fillRect(0, horizon - 1, w, Math.max(1, h * 0.002));

  const glare = ctx.createRadialGradient(w * 0.62, h * 0.2, 0, w * 0.62, h * 0.2, w * 0.48);
  glare.addColorStop(0, `rgba(255, 241, 198, ${(0.08 + optics.magnification * 0.006).toFixed(3)})`);
  glare.addColorStop(1, "rgba(255, 241, 198, 0)");
  ctx.fillStyle = glare;
  ctx.fillRect(0, 0, w, h);

  const shimmerHeight = h * 0.16;
  ctx.save();
  ctx.globalAlpha = clamp(0.16 + optics.magnification * 0.014, 0.16, 0.3);
  ctx.strokeStyle = "rgba(232, 240, 237, 0.2)";
  ctx.lineWidth = Math.max(1, w * 0.001);
  for (let i = 0; i < 9; i += 1) {
    const y = horizon + h * 0.025 + i * shimmerHeight * 0.08;
    const phase = now * 0.0015 + i * 0.72;
    ctx.beginPath();
    for (let x = -20; x <= w + 20; x += 24) {
      const wave = Math.sin(x * 0.026 + phase) * h * 0.0025;
      if (x === -20) ctx.moveTo(x, y + wave);
      else ctx.lineTo(x, y + wave);
    }
    ctx.stroke();
  }
  ctx.restore();

  const grainStep = Math.max(7, Math.floor(w / 110));
  ctx.fillStyle = "rgba(255, 255, 255, 0.025)";
  for (let y = 0; y < h; y += grainStep) {
    for (let x = (y / grainStep) % 2; x < w; x += grainStep * 2) {
      const jitter = Math.sin(x * 19.19 + y * 7.31 + now * 0.001) * 0.5 + 0.5;
      if (jitter > 0.72) ctx.fillRect(x, y, 1, 1);
    }
  }
}

function renderBridgeOptics() {
  const w = canvas.width;
  const h = canvas.height;
  const optics = currentOptics();
  const cx = w / 2;
  const cy = h / 2;
  const radius = w * 0.485;

  ctx.strokeStyle = "rgba(229, 242, 238, 0.18)";
  ctx.lineWidth = w * 0.002;
  const horizontalTicks = Math.round(2 * optics.reticleDensity);
  for (let i = -horizontalTicks; i <= horizontalTicks; i += 1) {
    const y = cy + i * h * 0.092 / optics.reticleDensity;
    ctx.beginPath();
    ctx.moveTo(cx - radius * 0.5, y);
    ctx.lineTo(cx + radius * 0.5, y);
    ctx.stroke();
  }

  ctx.strokeStyle = "rgba(229, 242, 238, 0.22)";
  ctx.beginPath();
  ctx.moveTo(cx, cy - radius * 0.48);
  ctx.lineTo(cx, cy + radius * 0.48);
  ctx.moveTo(cx - radius * 0.08, cy);
  ctx.lineTo(cx + radius * 0.08, cy);
  ctx.stroke();

  ctx.strokeStyle = "rgba(216, 180, 106, 0.42)";
  ctx.lineWidth = w * 0.003;
  ctx.beginPath();
  ctx.arc(cx, cy, radius * 0.76, Math.PI * 1.15, Math.PI * 1.85);
  ctx.stroke();

  for (let i = -4; i <= 4; i += 1) {
    const angle = -Math.PI / 2 + i * 0.105 / optics.reticleDensity;
    const inner = radius * 0.72;
    const outer = radius * (i === 0 ? 0.84 : 0.79);
    ctx.beginPath();
    ctx.moveTo(cx + Math.cos(angle) * inner, cy + Math.sin(angle) * inner);
    ctx.lineTo(cx + Math.cos(angle) * outer, cy + Math.sin(angle) * outer);
    ctx.stroke();
  }

  ctx.fillStyle = "rgba(226, 240, 236, 0.68)";
  ctx.font = `${Math.max(10, w * 0.012)}px Segoe UI, sans-serif`;
  ctx.fillText(`${optics.magnification}x / ${optics.fov} deg FOV`, w * 0.075, h * 0.89);
}

function renderWake(contact, x, y, spriteWidth) {
  const w = canvas.width;
  const h = canvas.height;
  const wakeWidth = spriteWidth * 1.18;
  const wakeHeight = Math.max(5, h * 0.012 * contact.scale);

  ctx.save();
  ctx.translate(x - spriteWidth * 0.05, y + wakeHeight * 0.55);
  ctx.strokeStyle = "rgba(225, 236, 228, 0.33)";
  ctx.lineWidth = Math.max(1, w * 0.0015);
  ctx.beginPath();
  ctx.moveTo(-wakeWidth * 0.48, 0);
  ctx.bezierCurveTo(-wakeWidth * 0.22, -wakeHeight, wakeWidth * 0.16, -wakeHeight * 0.8, wakeWidth * 0.52, 0);
  ctx.stroke();
  ctx.strokeStyle = "rgba(148, 188, 185, 0.18)";
  ctx.beginPath();
  ctx.moveTo(-wakeWidth * 0.42, wakeHeight * 0.7);
  ctx.bezierCurveTo(-wakeWidth * 0.08, wakeHeight * 0.05, wakeWidth * 0.24, wakeHeight * 0.12, wakeWidth * 0.42, wakeHeight * 0.74);
  ctx.stroke();
  ctx.restore();
}

function renderContactContrastPocket(contact, x, y, spriteWidth, spriteHeight) {
  const w = canvas.width;
  const rangeRatio = clamp(contact.range / MAX_RANGE, 0, 1);
  const pocketWidth = spriteWidth * (1.2 + rangeRatio * 0.48);
  const pocketHeight = spriteHeight * (0.64 + rangeRatio * 0.26);
  const centerY = y - spriteHeight * 0.32;
  const gradient = ctx.createRadialGradient(x, centerY, 0, x, centerY, pocketWidth * 0.58);

  gradient.addColorStop(0, `rgba(3, 8, 10, ${(0.24 + rangeRatio * 0.2).toFixed(3)})`);
  gradient.addColorStop(0.62, `rgba(6, 18, 20, ${(0.16 + rangeRatio * 0.11).toFixed(3)})`);
  gradient.addColorStop(1, "rgba(6, 18, 20, 0)");

  ctx.save();
  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.ellipse(x, centerY, pocketWidth * 0.5, pocketHeight * 0.5, 0, 0, TAU);
  ctx.fill();

  ctx.strokeStyle = `rgba(232, 240, 237, ${(0.13 + rangeRatio * 0.12).toFixed(3)})`;
  ctx.lineWidth = Math.max(1, w * 0.0012);
  ctx.beginPath();
  ctx.moveTo(x - pocketWidth * 0.44, y + spriteHeight * 0.02);
  ctx.lineTo(x + pocketWidth * 0.44, y + spriteHeight * 0.02);
  ctx.stroke();
  ctx.restore();
}

function renderFallbackContactGlyph(contact, x, y, spriteWidth) {
  const w = canvas.width;
  const hull = spriteWidth * 0.18;
  const mast = spriteWidth * 0.2;

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
  ctx.restore();
}

function renderContactLabel(contact, x, y, spriteHeight) {
  const w = canvas.width;
  const mastTop = y - spriteHeight * 0.68;
  ctx.fillStyle = "rgba(4, 9, 11, 0.7)";
  ctx.strokeStyle = "rgba(226, 240, 236, 0.25)";
  const labelWidth = Math.max(w * 0.19, 130);
  const labelHeight = 58;
  const labelX = clamp(16, x - labelWidth * 0.5, w - labelWidth - 24);
  const labelY = clamp(58, mastTop - labelHeight - 16, canvas.height - labelHeight - 28);
  ctx.fillRect(labelX, labelY, labelWidth, labelHeight);
  ctx.strokeRect(labelX, labelY, labelWidth, labelHeight);

  ctx.fillStyle = contact.color;
  ctx.font = `${Math.max(11, w * 0.014)}px Segoe UI, sans-serif`;
  ctx.fillText(contact.callsign, labelX + 10, labelY + 18);
  ctx.fillStyle = "rgba(232, 240, 237, 0.9)";
  ctx.font = `${Math.max(10, w * 0.012)}px Segoe UI, sans-serif`;
  ctx.fillText(`${contact.profile?.label || "Vessel"} / ${formatBearing(contact.bearing)}`, labelX + 10, labelY + 35);
  ctx.fillText(`Range ${contact.range.toFixed(1)} nm`, labelX + 10, labelY + 50);
}

function renderAcquisitionCue(contact, x, y, spriteWidth, spriteHeight, now) {
  const cue = state.acquisitionCue;
  const isSelected = state.selectedId === contact.id;
  const elapsed = cue.contactId === contact.id ? now - cue.startedAt : Number.POSITIVE_INFINITY;
  const pulseActive = elapsed >= 0 && elapsed < 1600;
  if (!isSelected && !pulseActive) return;

  const w = canvas.width;
  const pulse = pulseActive ? 1 - elapsed / 1600 : 0;
  const lift = spriteHeight * 0.42;
  const ringRadius = Math.max(spriteWidth * (0.34 + pulse * 0.18), w * 0.035);

  ctx.save();
  ctx.translate(x, y - lift);
  ctx.strokeStyle = pulseActive
    ? `rgba(216, 180, 106, ${(0.18 + pulse * 0.5).toFixed(3)})`
    : "rgba(138, 215, 193, 0.26)";
  ctx.lineWidth = Math.max(1.5, w * 0.0025);
  ctx.setLineDash([Math.max(5, w * 0.01), Math.max(4, w * 0.008)]);
  ctx.beginPath();
  ctx.arc(0, 0, ringRadius, 0, TAU);
  ctx.stroke();
  ctx.setLineDash([]);

  ctx.strokeStyle = "rgba(226, 240, 236, 0.34)";
  ctx.lineWidth = Math.max(1, w * 0.0016);
  ctx.beginPath();
  ctx.moveTo(-ringRadius * 1.28, 0);
  ctx.lineTo(-ringRadius * 0.72, 0);
  ctx.moveTo(ringRadius * 0.72, 0);
  ctx.lineTo(ringRadius * 1.28, 0);
  ctx.moveTo(0, -ringRadius * 1.15);
  ctx.lineTo(0, -ringRadius * 0.66);
  ctx.moveTo(0, ringRadius * 0.66);
  ctx.lineTo(0, ringRadius * 1.15);
  ctx.stroke();
  ctx.restore();
}

function renderContact(contact, now) {
  if (!contact.visible) return;
  const w = canvas.width;
  const h = canvas.height;
  const optics = currentOptics();
  const profile = contact.profile || vesselProfile(contact);
  const vesselAsset = assets.vessels[profile.sprite] || assets.scout;
  const x = contact.x * w;
  const bobSeed = Number.isFinite(contact.baseBearing) ? contact.baseBearing : contact.bearing;
  const bob = Math.sin(now * 0.003 + bobSeed) * h * 0.004 * contact.scale / optics.backgroundZoom;
  const y = contact.y * h + bob;
  const spriteWidth = w * 0.24 * contact.scale;
  const assetRatio = vesselAsset?.ready && vesselAsset.image.height
    ? vesselAsset.image.width / vesselAsset.image.height
    : 2;
  const spriteHeight = spriteWidth / clamp(assetRatio, 1.7, 2.35);
  if (![x, y, spriteWidth, spriteHeight].every(Number.isFinite)) return;

  ctx.save();
  renderWake(contact, x, y, spriteWidth);
  renderContactContrastPocket(contact, x, y, spriteWidth, spriteHeight);
  if (vesselAsset?.ready) {
    const rangeRatio = clamp(contact.range / MAX_RANGE, 0, 1);
    const drawX = x - spriteWidth * 0.5;
    const drawY = y - spriteHeight * profile.waterline;
    ctx.save();
    ctx.globalAlpha = clamp(0.54 + rangeRatio * 0.16, 0.54, 0.72) * profile.haze;
    ctx.filter = "brightness(0) blur(0.35px)";
    ctx.drawImage(
      vesselAsset.image,
      drawX + Math.max(1, w * 0.002),
      drawY + Math.max(1, h * 0.002),
      spriteWidth,
      spriteHeight
    );
    ctx.restore();

    ctx.globalAlpha = clamp(1.03 - rangeRatio * 0.12, 0.82, 0.98) * profile.haze;
    ctx.filter = `blur(${(rangeRatio * 0.32 / optics.backgroundZoom).toFixed(2)}px) contrast(${(1.04 + optics.magnification * 0.008).toFixed(2)}) saturate(0.94) brightness(${(0.92 + contact.scale * 0.14).toFixed(2)})`;
    ctx.drawImage(
      vesselAsset.image,
      drawX,
      drawY,
      spriteWidth,
      spriteHeight
    );
    if (rangeRatio > 0.62) {
      ctx.globalAlpha = (rangeRatio - 0.62) * 0.45;
      ctx.filter = "none";
      ctx.fillStyle = "rgba(214, 226, 221, 0.42)";
      ctx.fillRect(drawX, drawY, spriteWidth, spriteHeight * 0.38);
    }
  } else {
    renderFallbackContactGlyph(contact, x, y, spriteWidth);
  }
  ctx.restore();

  renderAcquisitionCue(contact, x, y, spriteWidth, spriteHeight, now);
  renderContactLabel(contact, x, y, spriteHeight);
}

function updateBearingBand() {
  const marks = [];
  const optics = currentOptics();
  const half = Math.ceil(optics.fov / 2 / 5) * 5;
  const step = optics.fov <= 16 ? 5 : 10;
  for (let offset = -half; offset <= half; offset += step) {
    marks.push(`<span>${formatBearing(state.bearing + offset)}</span>`);
  }
  bearingBand.innerHTML = marks.join("");
}

function updateOpticsControls() {
  const optics = currentOptics();
  if (magnificationReadout) {
    magnificationReadout.textContent = optics.label;
  }
  magnificationButtons.forEach((button) => {
    const active = button.dataset.magnification === optics.id;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
}

function triggerAcquisitionCue(contact, label = "Contact acquired") {
  if (!contact) return;
  state.acquisitionCue = {
    contactId: contact.id,
    startedAt: performance.now(),
    label: `${label}: ${contact.callsign}`,
  };
}

function focusContactForOptics() {
  const contacts = currentContacts(performance.now() / 1000);
  const projected = contacts.map(projectContact);
  const selected = projected.find((contact) => contact.id === state.selectedId);
  const visible = projected
    .filter((contact) => contact.visible)
    .sort((first, second) => Math.abs(first.relative) - Math.abs(second.relative))[0];
  const nearest = selected || visible || projected
    .sort((first, second) => Math.abs(first.relative) - Math.abs(second.relative))[0];
  if (!nearest) return;
  state.targetBearing = normalizeDegrees(nearest.bearing);
  state.velocity = 0;
  triggerAcquisitionCue(nearest, "Optics centered");
}

function setOpticsMode(mode) {
  if (!OPTICS_TIERS[mode] || state.opticsMode === mode) return;
  state.opticsMode = mode;
  focusContactForOptics();
  updateOpticsControls();
}

function updateContactStrip(contacts) {
  const sourceKey = contacts.map((contact) => contact.id).join("|");
  if (!state.contactButtonsReady || state.contactSourceKey !== sourceKey) {
    contactStrip.innerHTML = contacts.map((contact) => `<button class="contact-card" type="button" data-vessel-id="${contact.id}">
      <strong>${contact.callsign}</strong>
      <span>Standing by</span>
    </button>`).join("");
    state.contactButtonsReady = true;
    state.contactSourceKey = sourceKey;
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

function selectVessel(contact, { propagate = false } = {}) {
  if (!contact) return;
  const changed = state.selectedId !== contact.id;
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
  if (changed) {
    triggerAcquisitionCue(contact);
  }
  if (propagate) propagateSelection(contact);
}

// Additive write path into MonadFleetState.selection: a contact picked directly
// in Periscope (rather than acquired from Fleet Motion) only matters cross-
// instrument if it round-trips back into shared state. Only fires for contacts
// sourced from shared state (`contact.source` is set) — Periscope's own local
// demo vessels have no matching id in Fleet Motion's state to select.
function propagateSelection(contact) {
  if (!contact.source) return;
  const sharedState = window.MonadFleetState?.read?.();
  if (!sharedState || sharedState.selection?.selectedShipId === contact.id) return;
  window.MonadFleetState.write({
    ...sharedState,
    selection: { ...sharedState.selection, selectedShipId: contact.id }
  });
}

function updateSelectedPanel(contacts) {
  if (!state.selectedId) return;
  const contact = contacts.find((item) => item.id === state.selectedId);
  if (contact) {
    selectVessel(contact);
  }
}

function updateFieldNote() {
  if (!fieldNote) return;
  const cue = state.acquisitionCue;
  const cueAge = performance.now() - cue.startedAt;
  if (cue.contactId && cueAge >= 0 && cueAge < 2400) {
    fieldNote.textContent = cue.label;
    fieldNote.classList.add("is-acquiring");
    return;
  }
  const selected = state.visibleContacts.find((contact) => contact.id === state.selectedId);
  if (selected) {
    fieldNote.textContent = `Tracking ${selected.callsign}`;
  } else {
    fieldNote.textContent = "Drag to rotate bearing";
  }
  fieldNote.classList.toggle("is-acquiring", Boolean(selected));
}

// Mirrors Fleet Motion's own Data Source indicator: Periscope has always
// composited whatever Fleet Motion writes to MonadFleetState (live or not)
// with zero code changes, but had no way to tell a viewer which one it's
// currently looking at. state.dataSource is set as a side effect of
// sharedContacts() (null when there's no shared state to read at all, in
// which case Periscope falls back to its own local demo contacts).
function updateDataSourceIndicator() {
  if (!dataSourceReadout) return;
  if (state.dataSource === "fleetcore-live") {
    dataSourceReadout.textContent = "FleetCore Live";
    dataSourceReadout.classList.add("is-live");
  } else if (state.dataSource) {
    dataSourceReadout.textContent = "Fleet Motion (Local Sim)";
    dataSourceReadout.classList.remove("is-live");
  } else {
    dataSourceReadout.textContent = "Local Demo";
    dataSourceReadout.classList.remove("is-live");
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

  renderSeaPlate(now);
  renderAtmosphere(now);
  renderBridgeOptics();
  const sourceContacts = currentContacts(now / 1000);
  autoAcquireSharedContact(sourceContacts);
  const contacts = sourceContacts.map(projectContact);
  state.visibleContacts = contacts.filter((contact) => contact.visible);
  contacts.forEach((contact) => renderContact(contact, now));

  bearingReadout.textContent = formatBearing(state.bearing);
  updateBearingBand();
  updateContactStrip(contacts);
  updateDetailsButton();
  updateSelectedPanel(contacts);
  updateFieldNote();
  updateDataSourceIndicator();

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
  if (contact) selectVessel(contact, { propagate: true });
});

detailsButton.addEventListener("click", () => {
  const contact = state.visibleContacts.find((item) => item.id === detailsButton.dataset.vesselId);
  selectVessel(contact, { propagate: true });
});

magnificationButtons.forEach((button) => {
  button.addEventListener("click", () => setOpticsMode(button.dataset.magnification));
});

contactStrip.addEventListener("click", (event) => {
  const button = event.target.closest("[data-vessel-id]");
  if (!button) return;
  const contact = currentContacts(performance.now() / 1000)
    .map(projectContact)
    .find((item) => item.id === button.dataset.vesselId);
  selectVessel(contact, { propagate: true });
});

window.addEventListener("resize", resizeCanvas);
resizeCanvas();
updateOpticsControls();
requestAnimationFrame(render);
