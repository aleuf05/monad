// Ambience bridge instrument: transmissions spoken aloud via the browser's
// SpeechSynthesis API where available, over a synthesized static bed and
// squelch pops built with Web Audio. Fully FleetCore-connected, on
// purpose: no scripted fallback. connectFleetCoreLive() runs on load and
// keeps retrying with backoff until fleetcore-serve's snapshots start
// arriving; only then does it enter live mode and start speaking, driven
// by real state changes (a vessel's status transition, a
// RecordWatchEvent message) -- never a random timer. While disconnected,
// the console stays visibly "Offline -- reconnecting", never silent
// scripted chatter standing in for real data. ?fleetcoreServer= overrides
// the server URL if needed.
const CHANNEL_LABELS = {
  "fleet-comms": "Fleet Comms",
  weather: "Weather",
  traffic: "Traffic"
};

const SQUELCH_DURATION_S = 0.12;
const STATION_LABELS = {
  bridge: "Bridge",
  engineering: "Engineering",
  traffic: "Traffic",
  weather: "Weather"
};
const TRANSMISSION_PROFILES = {
  watch: {
    sourceAuthority: "human",
    urgency: 0.98,
    relevance: 0.96,
    authority: 1.0,
    expiresAfterMs: 30000,
    interruptible: true
  },
  status: {
    sourceAuthority: "fleetcore",
    urgency: 0.74,
    relevance: 0.76,
    authority: 0.86,
    expiresAfterMs: 12000,
    interruptible: true
  },
  // Fuel reports cite fleetcore's own tracked fuel_fraction (see
  // fleetcore/src/vessel.rs) -- never an invented number. Scored above
  // routine status chatter but below an explicit human watch note:
  // real, but a lower-urgency observation until it actually crosses a
  // threshold worth interrupting for.
  fuel: {
    sourceAuthority: "fleetcore",
    urgency: 0.8,
    relevance: 0.82,
    authority: 0.9,
    expiresAfterMs: 15000,
    interruptible: true
  }
};

// Operational Severity thresholds (fuel_fraction, 0-1) -- the only real
// numeric signal FleetCore tracks today that maps to "how serious are
// things" (no alarm/degraded concept exists elsewhere; verified this
// session). See docs/engineering-orders/radio-console-v1-and-fleetcore-
// model-upgrade.md.
const FUEL_SEVERITY_THRESHOLDS = { critical: 0.15, elevated: 0.3 };

function fuelSeverity(fraction) {
  if (typeof fraction !== "number") return "unknown";
  if (fraction <= FUEL_SEVERITY_THRESHOLDS.critical) return "critical";
  if (fraction <= FUEL_SEVERITY_THRESHOLDS.elevated) return "elevated";
  return "routine";
}

// --- Three independent control signals (packet §4 -- not a god scalar) ---
// Fleet-wide Operational Severity: worst per-vessel fuel severity across
// the fleet. Thin (fuel is the only real severity signal that exists
// today), but real -- never a fabricated "alarm" concept.
const SEVERITY_RANK = { unknown: 0, routine: 1, elevated: 2, critical: 3 };

function deriveOperationalSeverity(vessels) {
  let worst = "routine";
  (vessels || []).forEach((vessel) => {
    const severity = fuelSeverity(vessel.fuel_fraction);
    if (SEVERITY_RANK[severity] > SEVERITY_RANK[worst]) worst = severity;
  });
  return worst;
}

// Traffic Load: how much is actually requesting airtime right now, not
// how serious it is (that's severity) and not how restricted the channel
// is supposed to be (that's command discipline, operator-set below).
function deriveTrafficLoad(pendingCount) {
  if (pendingCount === 0) return "none";
  if (pendingCount <= 2) return "low";
  if (pendingCount <= 5) return "moderate";
  return "high";
}

// Command Discipline is NOT derived -- it's the operator-set mode from
// the #commandDisciplineSelect control, read directly where needed.

// --- Radio state (packet §1: silence must be discoverable) ---
// One of these is always true; which one explains *why* the console is
// quiet or not, so silence never reads as broken.
function deriveRadioState({ connected, powered, suppressed, pendingRequestCount, trafficLoad, commandDiscipline }) {
  if (!connected) return "FLEETCORE_DISCONNECTED";
  if (!powered) return "PAUSED";
  if (commandDiscipline === "radio_silence") return "TRAFFIC_SUPPRESSED";
  if (suppressed) return "TRAFFIC_SUPPRESSED";
  if (pendingRequestCount > 0) return "PREPARING_REPORT";
  if (commandDiscipline === "quiet_watch") return "QUIET_WATCH";
  if (trafficLoad === "none") return "NO_ELIGIBLE_TRAFFIC";
  return "LIVE_READ_ONLY";
}

const RADIO_STATE_LABELS = {
  QUIET_WATCH: "QUIET WATCH",
  NO_ELIGIBLE_TRAFFIC: "NO ELIGIBLE TRAFFIC",
  TRAFFIC_SUPPRESSED: "TRAFFIC SUPPRESSED",
  PREPARING_REPORT: "PREPARING REPORT",
  FLEETCORE_DISCONNECTED: "DEGRADED · FLEETCORE DISCONNECTED",
  SCHEDULER_FAILURE: "DEGRADED · SCHEDULER FAILURE",
  PAUSED: "PAUSED",
  LIVE_READ_ONLY: "LIVE READ-ONLY"
};

function buildStatusLine(factors) {
  const parts = [RADIO_STATE_LABELS[deriveRadioState(factors)] || "UNKNOWN"];
  if (factors.connected) {
    parts.push(`${factors.activeStationCount} STATIONS ACTIVE`);
    parts.push(
      factors.pendingRequestCount > 0
        ? `${factors.pendingRequestCount} PENDING ${factors.pendingRequestCount === 1 ? "EXCHANGE" : "EXCHANGES"}`
        : "NO PENDING TRAFFIC"
    );
    if (factors.trafficLoad !== "none") parts.push(`TRAFFIC ${factors.trafficLoad.toUpperCase()}`);
    if (factors.severity !== "routine") parts.push(`SEVERITY ${factors.severity.toUpperCase()}`);
  }
  return parts.join(" · ");
}

function updateRadioStateIndicator() {
  if (!radioStateEl) return;
  const pendingRequestCount = liveQueue.filter((entry) => entry.threadState === "pending").length;
  const discipline = commandDisciplineSelect ? commandDisciplineSelect.value : "normal";
  // Reflects the same hard rule livePump() actually enforces -- true only
  // when radio_silence is active AND something non-human is actually
  // sitting suppressed in the queue, not just whenever the mode is set.
  const suppressed =
    discipline === "radio_silence" && liveQueue.some((entry) => entry.sourceAuthority !== "human");
  const factors = {
    connected: liveMode,
    powered: state.powered,
    suppressed,
    pendingRequestCount,
    trafficLoad: deriveTrafficLoad(liveQueue.length),
    severity: deriveOperationalSeverity(lastSnapshotVessels),
    commandDiscipline: discipline,
    activeStationCount: stationChips.length
  };
  radioStateEl.textContent = buildStatusLine(factors);
}

const powerButton = document.querySelector("#powerButton");
const powerStatusEl = document.querySelector("#powerStatus");
const channelCountEl = document.querySelector("#channelCount");
const dataSourceEl = document.querySelector("#dataSourceValue");
const radioStateEl = document.querySelector("#radioStateValue");
const commandDisciplineSelect = document.querySelector("#commandDisciplineSelect");
const channelChips = Array.from(document.querySelectorAll(".channel-chip[data-channel]"));
const stationChips = Array.from(document.querySelectorAll(".channel-chip[data-station]"));
const volumeSlider = document.querySelector("#volumeSlider");
const muteButton = document.querySelector("#muteButton");
const transcriptLogEl = document.querySelector("#transcriptLog");
const speakingIndicatorEl = document.querySelector("#speakingIndicator");
const signalCanvas = document.querySelector("#signalMeter");
const signalCtx = signalCanvas.getContext("2d");

const state = {
  powered: false,
  muted: false,
  activeChannels: new Set(["fleet-comms", "weather", "traffic"]),
  selectedStation: "bridge",
  speaking: false,
  voiceForSpeaker: new Map(),
  animationFrame: null,
  meterLevels: new Array(24).fill(0.08),
  currentTransmission: null,
  currentTransmissionScore: -Infinity,
  threadLedger: [],
  nextThreadId: 1
};

let audioContext = null;
let masterGain = null;
let staticGain = null;
let noiseBuffer = null;

let liveMode = false;
let liveSocket = null;
let liveReconnectTimer = null;
let liveReconnectDelayMs = 1000;
let livePumpTimer = null;
let speechTimeoutTimer = null;
let lastVesselStatus = null; // Map<vesselId, status>, null until the first live snapshot seeds it
let lastSnapshotVessels = []; // most recent snapshot's vessels, for on-demand severity derivation
let lastWatchEventCount = 0;
let lastFuelSeverity = null; // Map<vesselId, "routine"|"elevated"|"critical">, null until seeded
const liveQueue = [];
const LIVE_CONNECT_TIMEOUT_MS = 2500;
const LIVE_PUMP_INTERVAL_MS = 700;
const VESSEL_CHANNEL = { flagship: "fleet-comms", scout: "fleet-comms", "passive-traffic": "traffic" };
const STATUS_LINES = {
  underway: "underway, course {course}, speed {speed} knots.",
  transiting: "transiting, maintaining course and speed.",
  holding: "holding station.",
  paused: "standing by, clock paused.",
  arrived: "arrived on station."
};

function updateChannelCount() {
  const count = state.activeChannels.size;
  channelCountEl.textContent = count === 0 ? "No channels" : `${count} channel${count === 1 ? "" : "s"}`;
}

function updateStationScope() {
  stationChips.forEach((chip) => {
    chip.classList.toggle("is-active", chip.dataset.station === state.selectedStation);
  });
}

function hashString(value) {
  let hash = 0;
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash * 31 + value.charCodeAt(i)) >>> 0;
  }
  return hash;
}

function pickVoiceFor(speaker) {
  if (state.voiceForSpeaker.has(speaker)) return state.voiceForSpeaker.get(speaker);
  const voices = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
  const voice = voices.length ? voices[hashString(speaker) % voices.length] : null;
  state.voiceForSpeaker.set(speaker, voice);
  return voice;
}

function buildNoiseBuffer(context) {
  const buffer = context.createBuffer(1, context.sampleRate * 2, context.sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < data.length; i += 1) {
    data[i] = Math.random() * 2 - 1;
  }
  return buffer;
}

function initAudio() {
  if (audioContext) return;
  const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextCtor) return;
  audioContext = new AudioContextCtor();
  noiseBuffer = buildNoiseBuffer(audioContext);

  masterGain = audioContext.createGain();
  masterGain.gain.value = volumeToLinear();
  masterGain.connect(audioContext.destination);

  staticGain = audioContext.createGain();
  staticGain.gain.value = 0; // squelch closed until the first transmission opens it
  staticGain.connect(masterGain);

  const staticSource = audioContext.createBufferSource();
  staticSource.buffer = noiseBuffer;
  staticSource.loop = true;
  const staticFilter = audioContext.createBiquadFilter();
  staticFilter.type = "bandpass";
  staticFilter.frequency.value = 1500;
  staticFilter.Q.value = 0.7;
  staticSource.connect(staticFilter);
  staticFilter.connect(staticGain);
  staticSource.start();
}

function volumeToLinear() {
  return Number(volumeSlider.value) / 100;
}

function applyVolume() {
  const linear = state.muted ? 0 : volumeToLinear();
  if (masterGain) {
    masterGain.gain.linearRampToValueAtTime(linear, audioContext.currentTime + 0.1);
  }
}

function playSquelch() {
  if (!audioContext) return;
  const source = audioContext.createBufferSource();
  source.buffer = noiseBuffer;
  const filter = audioContext.createBiquadFilter();
  filter.type = "highpass";
  filter.frequency.value = 2200;
  const envelope = audioContext.createGain();
  const now = audioContext.currentTime;
  envelope.gain.setValueAtTime(0, now);
  envelope.gain.linearRampToValueAtTime(0.35, now + 0.015);
  envelope.gain.exponentialRampToValueAtTime(0.001, now + SQUELCH_DURATION_S);
  source.connect(filter);
  filter.connect(envelope);
  envelope.connect(masterGain);
  source.start(now);
  source.stop(now + SQUELCH_DURATION_S + 0.02);
}

function duckStatic(down) {
  if (!staticGain) return;
  const now = audioContext.currentTime;
  staticGain.gain.cancelScheduledValues(now);
  // Squelch closed (no transmission) is silent, not a constant hiss --
  // static is only audible, ducked under the voice, while a transmission
  // is actually on the air.
  staticGain.gain.linearRampToValueAtTime(down ? 0.012 : 0, now + (down ? 0.15 : 0.4));
}

function setSpeaking(speaking) {
  const wasSpeaking = state.speaking;
  state.speaking = speaking;
  speakingIndicatorEl.textContent = speaking ? "Transmitting…" : "Standing by…";
  speakingIndicatorEl.classList.toggle("is-speaking", speaking);
  duckStatic(speaking);
  // Squelch pop belongs to the channel closing (PTT release, static
  // snapping back up), not to a transmission starting -- it was firing on
  // the wrong edge before this fix.
  if (wasSpeaking && !speaking) {
    playSquelch();
  }
}

function appendTranscript(entry) {
  const empty = transcriptLogEl.querySelector(".empty-note");
  if (empty) empty.remove();

  const item = document.createElement("li");
  item.classList.add("is-new");
  const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  item.innerHTML =
    `<span class="channel-tag">${CHANNEL_LABELS[entry.channel]}</span>` +
    `<span class="channel-tag">${stationLabelFor(entry.station)}</span>` +
    `<span class="channel-tag">${entry.threadState || "transit"}</span>` +
    `<span class="speaker">${entry.speaker}</span>${entry.text}` +
    `<span class="timestamp">${time}</span>`;
  entry.transcriptNode = item;
  transcriptLogEl.appendChild(item);
  transcriptLogEl.scrollTop = transcriptLogEl.scrollHeight;

  window.setTimeout(() => item.classList.remove("is-new"), 4000);

  while (transcriptLogEl.children.length > 60) {
    transcriptLogEl.removeChild(transcriptLogEl.firstChild);
  }
}

function estimatedSpeakingMs(text) {
  return Math.min(8000, Math.max(1500, text.length * 90));
}

function transmissionProfileFor(entry) {
  return TRANSMISSION_PROFILES[entry.kind] || TRANSMISSION_PROFILES.status;
}

function stationLabelFor(station) {
  return STATION_LABELS[station] || station;
}

function stationForEntry(entry) {
  if (entry.kind === "fuel") return "engineering";
  if (entry.kind === "watch") return "bridge";
  if (entry.channel === "traffic") return "traffic";
  if (entry.channel === "weather") return "weather";
  return "bridge";
}

function normalizeQueuedEntry(entry) {
  const profile = transmissionProfileFor(entry);
  return {
    ...entry,
    kind: entry.kind || "status",
    sourceAuthority: entry.sourceAuthority || profile.sourceAuthority,
    urgency: entry.urgency ?? profile.urgency,
    relevance: entry.relevance ?? profile.relevance,
    authority: entry.authority ?? profile.authority,
    expiresAfterMs: entry.expiresAfterMs ?? profile.expiresAfterMs,
    interruptible: entry.interruptible ?? profile.interruptible,
    queuedAt: entry.queuedAt ?? Date.now(),
    score: entry.score ?? null,
    station: entry.station || stationForEntry(entry)
  };
}

function scoreTransmission(entry, now = Date.now()) {
  const ageMs = Math.max(0, now - entry.queuedAt);
  const freshness = Math.max(0, 1 - ageMs / entry.expiresAfterMs);
  const interruptBonus = entry.interruptible ? 0.05 : 0;
  return (
    entry.authority * 1000 +
    entry.urgency * 100 +
    entry.relevance * 50 +
    freshness * 40 +
    interruptBonus
  );
}

function clearSpeechTimeout() {
  if (speechTimeoutTimer !== null) {
    window.clearTimeout(speechTimeoutTimer);
    speechTimeoutTimer = null;
  }
}

function clearCurrentTransmission() {
  state.currentTransmission = null;
  state.currentTransmissionScore = -Infinity;
}

function recordThreadState(entry, nextState) {
  entry.threadState = nextState;
  entry.threadUpdatedAt = Date.now();
  state.threadLedger.push({
    threadId: entry.threadId,
    speaker: entry.speaker,
    channel: entry.channel,
    station: entry.station,
    state: nextState,
    at: entry.threadUpdatedAt
  });
  while (state.threadLedger.length > 50) {
    state.threadLedger.shift();
  }
}

function completeTransmission(entry, nextState = "completed") {
  clearSpeechTimeout();
  clearCurrentTransmission();
  recordThreadState(entry, nextState);
  if (entry.transcriptNode) {
    const tags = entry.transcriptNode.querySelectorAll(".channel-tag");
    if (tags[2]) tags[2].textContent = nextState;
  }
  setSpeaking(false);
  window.setTimeout(livePump, 0);
}

function interruptCurrentTransmission() {
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
  clearSpeechTimeout();
  clearCurrentTransmission();
  setSpeaking(false);
}

function speak(entry) {
  // No SpeechSynthesis at all, muted, or no voices installed (common on
  // minimal Linux desktops and headless/sandboxed environments) all fall
  // back to the same timed visual cue -- a silent console that never shows
  // "Transmitting..." reads as broken, not quiet.
  const voices = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
  if (!window.speechSynthesis || state.muted || !voices.length) {
    setSpeaking(true);
    clearSpeechTimeout();
    speechTimeoutTimer = window.setTimeout(() => {
      speechTimeoutTimer = null;
      completeTransmission(entry);
    }, estimatedSpeakingMs(entry.text));
    return;
  }
  const utterance = new SpeechSynthesisUtterance(entry.text);
  const voice = pickVoiceFor(entry.speaker);
  if (voice) utterance.voice = voice;
  utterance.volume = volumeToLinear();
  utterance.rate = 1.05;
  utterance.pitch = 0.95;
  utterance.onstart = () => setSpeaking(true);
  utterance.onend = () => {
    completeTransmission(entry);
  };
  utterance.onerror = () => {
    completeTransmission(entry, "completed");
  };
  // Safety net: if onstart/onend never fire at all (observed in some
  // sandboxed environments even when getVoices() reports voices), don't
  // leave the indicator stuck on "Transmitting..." forever.
  clearSpeechTimeout();
  speechTimeoutTimer = window.setTimeout(() => {
    speechTimeoutTimer = null;
    completeTransmission(entry);
  }, estimatedSpeakingMs(entry.text) + 2000);
  window.speechSynthesis.speak(utterance);
}

function transmitEntry(entry) {
  state.currentTransmission = entry;
  state.currentTransmissionScore = entry.score ?? scoreTransmission(entry);
  recordThreadState(entry, "acked");
  appendTranscript(entry);
  speak(entry);
}

// --- Live mode: event-driven transmissions from a real fleetcore-serve ---
//
// watch_events only ever contains what a human explicitly recorded via a
// RecordWatchEvent command -- in normal running it's usually empty, so
// building "event-driven" purely on that field would mean the radio
// almost never speaks. The actual continuous stream of real events is
// vessel status transitions between snapshots (underway -> arrived, a new
// contact appearing, etc.), diffed client-side the same way Fleet Motion's
// applyLiveSnapshot() already renders positions from consecutive
// snapshots. Both sources feed the same queue; RecordWatchEvent messages
// (an actual human watch note) are queued first since they're rarer and
// more deliberate than a routine status flip.

function fleetCoreServerUrl() {
  const params = new URLSearchParams(window.location.search);
  if (params.get("fleetcoreServer")) return params.get("fleetcoreServer");
  // Anywhere reached over https (the public domain), port 4771 isn't
  // reachable directly and ws:// would be blocked as mixed content anyway --
  // always route through Caddy's /fleetcore-ws/ reverse proxy instead (see
  // docs/deployment.md). Anywhere else (local dev server), fleetcore-serve
  // is reachable directly on its own port.
  if (window.location.protocol === "https:") {
    return `wss://${window.location.host}/fleetcore-ws/ws`;
  }
  return `ws://${window.location.hostname || "localhost"}:4771/ws`;
}

function speedKnots(speedMps) {
  return (Number(speedMps || 0) * 1.94384).toFixed(0);
}

function statusLineFor(vessel) {
  const template = STATUS_LINES[vessel.status];
  if (!template) return null;
  return template
    .replace("{course}", `${Math.round(Number(vessel.course || 0))}`)
    .replace("{speed}", speedKnots(vessel.speed_mps));
}

function queueLiveEntry(entry) {
  const queued = normalizeQueuedEntry(entry);
  queued.threadId = queued.threadId || state.nextThreadId++;
  recordThreadState(queued, "pending");
  liveQueue.push(queued);
  window.setTimeout(livePump, 0);
}

function stationCanObserve(entry, station) {
  if (station === "bridge") return true;
  return entry.station === station;
}

function speakerNameFor(vessel) {
  // MONAD refers to itself as "Monad Actual" in dialogue, everyone else
  // by their title-case name.
  if (vessel.kind === "flagship") return "Monad Actual";
  return vessel.name || vessel.callsign || vessel.id;
}

function diffVesselStates(vessels) {
  const seeding = lastVesselStatus === null;
  if (seeding) lastVesselStatus = new Map();
  vessels.forEach((vessel) => {
    const previous = lastVesselStatus.get(vessel.id);
    lastVesselStatus.set(vessel.id, vessel.status);
    if (seeding || previous === vessel.status) return;
    const line = statusLineFor(vessel);
    if (!line) return;
    const channel = VESSEL_CHANNEL[vessel.kind] || "fleet-comms";
    const name = speakerNameFor(vessel);
    queueLiveEntry({
      kind: "status",
      channel,
      speaker: name,
      text: `${name}, ${line}`,
      station: channel === "traffic" ? "traffic" : "bridge"
    });
  });
}

// Reports only on a severity *transition* (routine -> elevated -> critical,
// or back), not every tick fuel_fraction ticks down -- same anti-spam
// discipline as diffVesselStates. Cites the real fuel_fraction value from
// the snapshot; never invents a number.
function diffFuelLevels(vessels) {
  const seeding = lastFuelSeverity === null;
  if (seeding) lastFuelSeverity = new Map();
  vessels.forEach((vessel) => {
    if (typeof vessel.fuel_fraction !== "number") return;
    const severity = fuelSeverity(vessel.fuel_fraction);
    const previous = lastFuelSeverity.get(vessel.id);
    lastFuelSeverity.set(vessel.id, severity);
    if (seeding || previous === severity || severity === "routine") return;
    const percent = Math.round(vessel.fuel_fraction * 100);
    const name = speakerNameFor(vessel);
    const recommendation = severity === "critical" ? "recommend holding" : "monitoring consumption";
    queueLiveEntry({
      kind: "fuel",
      channel: "fleet-comms",
      speaker: "Engineering",
      text: `Engineering reports ${name} at ${percent} percent fuel margin, ${recommendation}.`,
      station: "engineering"
    });
  });
}

function diffWatchEvents(watchEvents) {
  const events = watchEvents || [];
  if (events.length <= lastWatchEventCount) {
    lastWatchEventCount = events.length;
    return;
  }
  events.slice(lastWatchEventCount).forEach((event) => {
    queueLiveEntry({
      kind: "watch",
      channel: "fleet-comms",
      speaker: "Watch Officer",
      text: event.message,
      station: "bridge"
    });
  });
  lastWatchEventCount = events.length;
}

function applyLiveSnapshot(snapshot) {
  lastSnapshotVessels = snapshot.vessels || [];
  diffWatchEvents(snapshot.watch_events);
  diffVesselStates(snapshot.vessels || []);
  diffFuelLevels(snapshot.vessels || []);
  updateRadioStateIndicator();
}

function livePump() {
  updateRadioStateIndicator();
  if (!state.powered || !liveQueue.length) return;

  const now = Date.now();
  for (let i = liveQueue.length - 1; i >= 0; i -= 1) {
    const entry = liveQueue[i];
    if (now - entry.queuedAt > entry.expiresAfterMs) {
      recordThreadState(entry, entry.kind === "watch" ? "escalated" : "timeout");
      liveQueue.splice(i, 1);
    }
  }

  // Hard rule (packet §4): radio_silence is not just a status label -- it
  // actually suppresses everything except human-command-class traffic,
  // regardless of score. Discipline shapes the channel; this one rule
  // isn't shaped, it's absolute.
  const discipline = commandDisciplineSelect ? commandDisciplineSelect.value : "normal";
  const silenced = discipline === "radio_silence";

  let next = null;
  for (const entry of liveQueue) {
    if (!state.activeChannels.has(entry.channel)) continue;
    if (!stationCanObserve(entry, state.selectedStation)) continue;
    if (silenced && entry.sourceAuthority !== "human") continue;
    entry.score = scoreTransmission(entry, now);
    if (!next || entry.score > next.score || (entry.score === next.score && entry.queuedAt < next.queuedAt)) {
      next = entry;
    }
  }
  if (!next) {
    liveQueue.length = 0; // Nothing filtered-in queued is worth holding onto once channels change.
    return;
  }

  if (state.speaking) {
    const currentScore = state.currentTransmissionScore;
    if (!next.interruptible || next.score <= currentScore) {
      return;
    }
    interruptCurrentTransmission();
  }

  liveQueue.splice(liveQueue.indexOf(next), 1);
  transmitEntry(next);
}

function setOfflineState(label) {
  liveMode = false;
  window.clearInterval(livePumpTimer);
  if (dataSourceEl) {
    dataSourceEl.textContent = label;
    dataSourceEl.classList.remove("is-on");
  }
  updateRadioStateIndicator();
}

function scheduleReconnect() {
  window.clearTimeout(liveReconnectTimer);
  liveReconnectTimer = setTimeout(() => {
    liveReconnectDelayMs = Math.min(liveReconnectDelayMs * 1.6, 15000);
    connectFleetCoreLive();
  }, liveReconnectDelayMs);
}

function enterLiveMode() {
  liveMode = true;
  if (dataSourceEl) {
    dataSourceEl.textContent = "FleetCore Live";
    dataSourceEl.classList.add("is-on");
  }
  livePumpTimer = window.setInterval(livePump, LIVE_PUMP_INTERVAL_MS);
  updateRadioStateIndicator();
}

function connectFleetCoreLive() {
  let settled = false;
  setOfflineState(liveReconnectDelayMs > 1000 ? "Offline — reconnecting" : "Connecting…");
  const socket = new WebSocket(fleetCoreServerUrl());
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
      settled = true;
      clearTimeout(timeout);
    }
    if (liveMode) setOfflineState("Offline — reconnecting");
    scheduleReconnect();
  });

  liveSocket = socket;
}

function drawSignalMeter() {
  const { width, height } = signalCanvas;
  signalCtx.clearRect(0, 0, width, height);
  const barWidth = width / state.meterLevels.length;
  const amplitude = state.powered ? (state.speaking ? 1 : 0.35) : 0.05;
  for (let i = 0; i < state.meterLevels.length; i += 1) {
    const target = state.powered ? Math.random() * amplitude : 0.03;
    state.meterLevels[i] += (target - state.meterLevels[i]) * 0.35;
    const barHeight = Math.max(2, state.meterLevels[i] * height);
    signalCtx.fillStyle = state.speaking ? "#d8b46a" : "#8ad7c1";
    signalCtx.globalAlpha = state.powered ? 0.85 : 0.25;
    signalCtx.fillRect(i * barWidth + 1, height - barHeight, barWidth - 2, barHeight);
  }
  state.animationFrame = window.requestAnimationFrame(drawSignalMeter);
}

function setPowered(powered) {
  state.powered = powered;
  powerButton.textContent = powered ? "Power Off" : "Power On";
  powerButton.classList.toggle("is-on", powered);
  powerStatusEl.textContent = powered ? "On" : "Off";
  powerStatusEl.classList.toggle("is-on", powered);

  if (powered) {
    initAudio();
    if (audioContext && audioContext.state === "suspended") audioContext.resume();
    applyVolume();
    // No scripted schedule to start -- transmissions only ever come from
    // the live FleetCore queue (see enterLiveMode()/livePump()). If not
    // connected yet, the console just sits Offline until it is.
  } else {
    clearSpeechTimeout();
    clearCurrentTransmission();
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    liveQueue.length = 0;
    setSpeaking(false);
  }
}

powerButton.addEventListener("click", () => setPowered(!state.powered));

channelChips.forEach((chip) => {
  chip.addEventListener("click", () => {
    const channel = chip.dataset.channel;
    if (state.activeChannels.has(channel)) {
      state.activeChannels.delete(channel);
      chip.classList.remove("is-active");
    } else {
      state.activeChannels.add(channel);
      chip.classList.add("is-active");
    }
    updateChannelCount();
  });
});

stationChips.forEach((chip) => {
  chip.addEventListener("click", () => {
    state.selectedStation = chip.dataset.station;
    updateStationScope();
    window.setTimeout(livePump, 0);
  });
});

if (commandDisciplineSelect) {
  commandDisciplineSelect.addEventListener("change", () => {
    // Command Discipline is operator-set, never derived (packet §4) --
    // radio_silence takes effect immediately, same pump cycle.
    updateRadioStateIndicator();
    window.setTimeout(livePump, 0);
  });
}

volumeSlider.addEventListener("input", applyVolume);

muteButton.addEventListener("click", () => {
  state.muted = !state.muted;
  muteButton.textContent = state.muted ? "Unmute" : "Mute";
  muteButton.setAttribute("aria-pressed", String(state.muted));
  applyVolume();
});

if (window.speechSynthesis) {
  window.speechSynthesis.addEventListener("voiceschanged", () => state.voiceForSpeaker.clear());
}

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

updateChannelCount();
updateStationScope();
updateRadioStateIndicator();
drawSignalMeter();

// Live is the default now (Admiral's call, 2026-07-11), matching Fleet
// Motion: every page load attempts a FleetCore connection. Scripted
// chatter still works exactly as before unless/until a snapshot actually
// arrives; a failed attempt fails closed and silently at the application
// level (see connectFleetCoreLive()'s timeout), it's only the accepted
// browser-native console error tradeoff that changed, not the fallback
// behavior. ?fleetcoreServer= still overrides the server URL if needed.
connectFleetCoreLive();
