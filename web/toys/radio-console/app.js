// Ambience bridge instrument: transmissions spoken aloud via the browser's
// SpeechSynthesis API where available, over a synthesized static bed and
// squelch pops built with Web Audio. Fully FleetCore-connected, on
// purpose: no scripted fallback. connectFleetCoreLive() runs on load and
// keeps retrying with backoff until fleetcore-serve's snapshots start
// arriving; only then does it enter live mode and start speaking, driven
// by real state changes from the live snapshot stream and retained event
// tail (vessel status changes, vessel_events, captain controls, escort
// intents, agent decisions, canon ledger updates, and explicit
// RecordWatchEvent messages) -- never a random timer. While disconnected,
// the console stays visibly "Offline -- reconnecting", never silent
// scripted chatter standing in for real data. ?fleetcoreServer= overrides
// the server URL if needed.
const CHANNEL_LABELS = {
  "fleet-comms": "Fleet Comms",
  weather: "Weather",
  traffic: "Traffic"
};

const SQUELCH_DURATION_S = 0.12;
// Real-world wire, not FleetCore -- deliberately kept out of the
// transmission-scoring/speech pipeline above (TRANSMISSION_PROFILES,
// scoreTransmission()) so an NPR headline can never be spoken in the same
// voice/urgency system as a fleet watch event, which would misrepresent
// real-world news as fleet radio traffic. Rendered as its own panel
// instead. Source: tools/npr-headlines/fetch.py, written server-side
// (NPR's feed only grants CORS to apps.npr.org) to web/data/npr-headlines.json,
// refreshed on a timer -- see docs/deployment.md for the fetch schedule.
const NEWSWIRE_URL = "/data/npr-headlines.json";
const NEWSWIRE_REFRESH_MS = 5 * 60 * 1000;
let newswireRefreshTimer = null;
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

const STATION_MEMORY_LIMIT = 6;

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
  if (commandDiscipline === "quiet_watch") return "QUIET_WATCH";
  if (pendingRequestCount > 0) return "PREPARING_REPORT";
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
        ? `${factors.pendingRequestCount} PENDING ${factors.pendingRequestCount === 1 ? "REQUEST" : "REQUESTS"}`
        : "NO PENDING TRAFFIC"
    );
    if (factors.trafficLoad !== "none") parts.push(`TRAFFIC ${factors.trafficLoad.toUpperCase()}`);
    if (factors.severity !== "routine") parts.push(`SEVERITY ${factors.severity.toUpperCase()}`);
    if (factors.stationMemoryLine) parts.push(factors.stationMemoryLine);
  }
  return parts.join(" · ");
}

function isSuppressedByDiscipline(entry, discipline) {
  if (discipline === "radio_silence") return entry.sourceAuthority !== "human";
  if (discipline === "quiet_watch") return entry.kind === "status";
  return false;
}

function updateRadioStateIndicator() {
  if (!radioStateEl) return;
  const discipline = commandDisciplineSelect ? commandDisciplineSelect.value : "normal";
  // Only counts entries that would actually be eligible to transmit under
  // the current discipline -- caught by this task's own acceptance test:
  // counting *all* pending entries regardless of suppression made
  // "PREPARING REPORT" show up even during quiet_watch when nothing but
  // suppressed routine chatter was actually pending.
  const pendingRequestCount = liveQueue.filter(
    (entry) => entry.threadState === "pending" && !isSuppressedByDiscipline(entry, discipline)
  ).length;
  // Reflects the same hard rule livePump() actually enforces -- true only
  // when something is actually sitting suppressed in the queue under the
  // current discipline, not just whenever a suppressing mode is set.
  const suppressed = liveQueue.some((entry) => isSuppressedByDiscipline(entry, discipline));
  const factors = {
    connected: liveMode,
    powered: state.powered,
    suppressed,
    pendingRequestCount,
    trafficLoad: deriveTrafficLoad(liveQueue.length),
    severity: deriveOperationalSeverity(lastSnapshotVessels),
    commandDiscipline: discipline,
    activeStationCount: state.activeChannels.size,
    stationMemoryLine: stationMemoryLine(state.selectedStation)
  };
  radioStateEl.textContent = buildStatusLine(factors);
  updateDiagnostics();
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
const newswireLogEl = document.querySelector("#newswireLog");
const newswireUpdatedEl = document.querySelector("#newswireUpdated");
const newswireTopicEl = document.querySelector("#newswireTopic");
const newswireTopicTitleEl = document.querySelector("#newswireTopicTitle");
const newswireTopicTimeEl = document.querySelector("#newswireTopicTime");
const newswireTopicLinkEl = document.querySelector("#newswireTopicLink");
const newswireReadButton = document.querySelector("#newswireReadButton");
const newswireVoiceStatusEl = document.querySelector("#newswireVoiceStatus");
const signalCtx = signalCanvas.getContext("2d");
let selectedNewswireItem = null;
let newswireUtterance = null;

// --- Diagnostics DOM refs (Captain's packet, 2026-07-16: "connected is not
// the same as heard") ---
const diagSummaryLine = document.querySelector("#diagSummaryLine");
const diagQueuedCountEl = document.querySelector("#diagQueuedCount");
const diagCurrentMessageEl = document.querySelector("#diagCurrentMessage");
const diagLastAcceptedEl = document.querySelector("#diagLastAccepted");
const diagLoopStateEl = document.querySelector("#diagLoopState");
const diagSourceTagEl = document.querySelector("#diagSourceTag");
const audioPathListEl = document.querySelector("#audioPathList");
const diagLogEl = document.querySelector("#diagLog");
const testToneButton = document.querySelector("#testToneButton");
const testMessageButton = document.querySelector("#testMessageButton");
const stopPlaybackButton = document.querySelector("#stopPlaybackButton");
const outputDeviceSelect = document.querySelector("#outputDeviceSelect");
const outputLevelMeterEl = document.querySelector("#outputLevelMeter");
const outputLevelReadoutEl = document.querySelector("#outputLevelReadout");
const qualityTestButton = document.querySelector("#qualityTestButton");
const qualityFreqEl = document.querySelector("#qualityFreq");
const qualitySnrEl = document.querySelector("#qualitySnr");
const qualityDropoutsEl = document.querySelector("#qualityDropouts");
const qualityLatencyEl = document.querySelector("#qualityLatency");
const qualityVerdictEl = document.querySelector("#qualityVerdict");

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
  nextThreadId: 1,
  stationMemory: new Map()
};

let audioContext = null;
let masterGain = null;
let staticGain = null;
let noiseBuffer = null;
let analyserNode = null;
let analyserData = null;
let activeTestTone = null;
// Only ever set true by a *measured* audible test tone pass (see
// runTestTone()) -- never by a transmission simply completing. Speech
// synthesis output never passes through the analyser (browsers don't
// route SpeechSynthesis through the Web Audio graph), so a spoken
// transmission finishing proves the browser *attempted* to speak, not that
// anything audible came out. This is the deliberate "connected is not the
// same as heard" line from the Captain's packet -- overall radio state
// stays UNVERIFIED until a real measurement backs it up.
let audioConfirmedThisSession = false;
let lastAudioFault = null;
let lastAcceptedEntry = null;
const diagLogEntries = [];
const AUDIO_PATH_STAGES = ["synthesisRequested", "audioGenerated", "streamDelivered", "playbackStarted", "audibleVerified"];
const audioPathState = {};
AUDIO_PATH_STAGES.forEach((stage) => { audioPathState[stage] = { status: "pending", detail: "" }; });

let liveMode = false;
let liveSocket = null;
let liveReconnectTimer = null;
let liveReconnectDelayMs = 1000;
let livePumpTimer = null;
let speechTimeoutTimer = null;
let lastVesselStatus = null; // Map<vesselId, status>, null until the first live snapshot seeds it
let lastSnapshotVessels = []; // most recent snapshot's vessels, for on-demand severity derivation
let lastWatchEventCount = null; // null until the first live snapshot seeds it
let lastFuelSeverity = null; // Map<vesselId, "routine"|"elevated"|"critical">, null until seeded
let lastEscortMode = null; // null until the first live snapshot seeds it
let lastVesselEventSeq = null; // null until the first live snapshot seeds it
let lastCanonEventSeq = null; // null until the first live snapshot seeds it
let lastCaptainControlSignatures = null; // Map<vesselId, signature>, null until seeded
let lastEscortIntentSignatures = null; // Map<decisionId, signature>, null until seeded
let lastAgentDecisionCount = null; // null until seeded
let firstOperationalSnapshot = true;
const liveQueue = [];
const LIVE_CONNECT_TIMEOUT_MS = 2500;
const LIVE_PUMP_INTERVAL_MS = 700;
const MAX_CONTENT_LINES_PER_SNAPSHOT = 6;
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
    `<span class="channel-tag">${(entry.source || "unknown").toUpperCase()}</span>` +
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
    station: entry.station || stationForEntry(entry),
    // Source Identification (packet §6): every entry is one of Simulated
    // (diagnostic test injection), Generated (reserved -- this console has
    // no LLM-generation content path, by design), Live (real FleetCore
    // state), or Unknown. Defaults to "live" since every existing content
    // path (diffVesselStates, diffFuelLevels, diffCanonEvents, etc.) is
    // real FleetCore state; only the diagnostics test injector overrides
    // this to "simulated".
    source: entry.source || "live"
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

function stationMemoryEntries(station) {
  if (!state.stationMemory.has(station)) {
    state.stationMemory.set(station, []);
  }
  return state.stationMemory.get(station);
}

function stationReportSignature(station) {
  if (station === "engineering") {
    const fuelParts = (lastSnapshotVessels || [])
      .filter((vessel) => typeof vessel.fuel_fraction === "number")
      .map((vessel) => `${vessel.id}:${fuelSeverity(vessel.fuel_fraction)}`)
      .sort();
    return fuelParts.length ? `engineering:${fuelParts.join("|")}` : "engineering:none";
  }
  if (station === "traffic") {
    const trafficParts = (lastSnapshotVessels || [])
      .filter((vessel) => VESSEL_CHANNEL[vessel.kind] === "traffic")
      .map((vessel) => `${vessel.id}:${vessel.status}`)
      .sort();
    return trafficParts.length ? `traffic:${trafficParts.join("|")}` : "traffic:none";
  }
  if (station === "weather") {
    return "weather:none";
  }
  const bridgeParts = (lastSnapshotVessels || [])
    .filter((vessel) => VESSEL_CHANNEL[vessel.kind] !== "traffic")
    .map((vessel) => `${vessel.id}:${vessel.status}`)
    .sort();
  return `bridge:${lastWatchEventCount}:${bridgeParts.join("|") || "none"}`;
}

function stationReportSummary(station) {
  if (station === "engineering") {
    const severities = (lastSnapshotVessels || [])
      .filter((vessel) => typeof vessel.fuel_fraction === "number")
      .map((vessel) => fuelSeverity(vessel.fuel_fraction));
    if (!severities.length) return "ENGINEERING NO FUEL REPORT";
    if (severities.some((severity) => severity === "critical")) return "ENGINEERING CRITICAL FUEL";
    if (severities.some((severity) => severity === "elevated")) return "ENGINEERING ELEVATED FUEL";
    return "ENGINEERING ROUTINE";
  }
  if (station === "traffic") {
    const trafficCount = (lastSnapshotVessels || []).filter((vessel) => VESSEL_CHANNEL[vessel.kind] === "traffic").length;
    return trafficCount > 0 ? `TRAFFIC ${trafficCount} CONTACT${trafficCount === 1 ? "" : "S"}` : "TRAFFIC CLEAR";
  }
  if (station === "weather") {
    return "WEATHER QUIET";
  }
  return lastWatchEventCount > 0 ? `BRIDGE ${lastWatchEventCount} WATCH${lastWatchEventCount === 1 ? "" : "ES"}` : "BRIDGE QUIET";
}

function rememberStationTransmission(entry) {
  if (!entry.station) return;
  const memory = stationMemoryEntries(entry.station);
  memory.push({
    signature: stationReportSignature(entry.station),
    summary: stationReportSummary(entry.station),
    text: entry.text,
    at: Date.now()
  });
  while (memory.length > STATION_MEMORY_LIMIT) {
    memory.shift();
  }
}

function stationMemoryLine(station) {
  const memory = stationMemoryEntries(station);
  if (!memory.length) return "NO PRIOR REPORT";
  const latest = memory[memory.length - 1];
  return latest.signature === stationReportSignature(station) ? "NO CHANGE SINCE LAST REPORT" : "";
}

function truncated(value, limit = 88) {
  const text = String(value || "").trim();
  if (!text) return "";
  return text.length <= limit ? text : `${text.slice(0, Math.max(0, limit - 1)).trimEnd()}…`;
}

function countWhere(items, predicate) {
  return (items || []).reduce((count, item) => count + (predicate(item) ? 1 : 0), 0);
}

function snapshotCounts(snapshot) {
  const vessels = snapshot.vessels || [];
  return {
    moving: countWhere(vessels, (vessel) => vessel.status === "underway" || vessel.status === "transiting"),
    holding: countWhere(vessels, (vessel) => vessel.status === "holding" || vessel.status === "paused"),
    activeScouts: countWhere(vessels, (vessel) => vessel.kind === "scout"),
    traffic: countWhere(vessels, (vessel) => vessel.kind === "passive-traffic"),
    elevatedFuel: countWhere(vessels, (vessel) => fuelSeverity(vessel.fuel_fraction) === "elevated"),
    criticalFuel: countWhere(vessels, (vessel) => fuelSeverity(vessel.fuel_fraction) === "critical"),
    routineFuel: countWhere(vessels, (vessel) => fuelSeverity(vessel.fuel_fraction) === "routine"),
    openControls: countWhere(snapshot.captain_controls || [], (control) => control.enabled),
    disabledControls: countWhere(snapshot.captain_controls || [], (control) => !control.enabled),
    pendingIntents: (snapshot.escort_intents || []).filter((intent) => intent.executed_tick == null).length,
    completedIntents: (snapshot.escort_intents || []).filter((intent) => intent.executed_tick != null).length
  };
}

function queueNarratedEntry(entry) {
  if (snapshotNarrationBudget <= 0) return false;
  snapshotNarrationBudget -= 1;
  queueLiveEntry(entry);
  return true;
}

function captainControlSignature(control) {
  return [
    control.captain_id,
    control.vessel_id,
    control.role,
    control.enabled ? "enabled" : "disabled",
    control.runtime_status,
    control.provider,
    control.status_message,
    control.last_report_tick ?? ""
  ].join("|");
}

function escortIntentSignature(intent) {
  return [
    intent.decision_id,
    intent.captain_id,
    intent.vessel_id,
    intent.posture,
    intent.target_contact_id || "",
    intent.objective,
    intent.assessment,
    intent.reconsider_at_tick,
    intent.accepted_tick,
    intent.executed_tick ?? "",
    intent.consequence ?? ""
  ].join("|");
}

function canonEventCursor(event) {
  return typeof event?.fleet_event_sequence === "number" ? event.fleet_event_sequence : -1;
}

function vesselEventCursor(event) {
  return typeof event?.event_seq === "number" ? event.event_seq : -1;
}

function initializeOperationalCursors(snapshot) {
  lastVesselEventSeq = (snapshot.vessel_events || []).reduce((max, event) => Math.max(max, vesselEventCursor(event)), -1);
  lastCanonEventSeq = (snapshot.canon_events || []).reduce((max, event) => Math.max(max, canonEventCursor(event)), -1);
  lastCaptainControlSignatures = new Map((snapshot.captain_controls || []).map((control) => [control.vessel_id, captainControlSignature(control)]));
  lastEscortIntentSignatures = new Map((snapshot.escort_intents || []).map((intent) => [intent.decision_id, escortIntentSignature(intent)]));
  lastAgentDecisionCount = (snapshot.agent_decisions || []).length;
}

function queueBaselineOperationalWatch(snapshot) {
  const counts = snapshotCounts(snapshot);
  const escortLabel = ESCORT_MODE_LABELS[snapshot.escort_mode] || snapshot.escort_mode || "unknown";
  queueNarratedEntry({
    kind: "status",
    channel: "fleet-comms",
    speaker: "Bridge",
    text: `Bridge, live watch established. ${counts.moving} vessel${counts.moving === 1 ? "" : "s"} moving, ${counts.holding} holding, escort mode ${escortLabel}.`,
    station: "bridge"
  });

  if (counts.criticalFuel > 0 || counts.elevatedFuel > 0 || counts.routineFuel > 0) {
    const fuelText = counts.criticalFuel > 0
      ? `${counts.criticalFuel} critical and ${counts.elevatedFuel} elevated fuel margin${counts.criticalFuel + counts.elevatedFuel === 1 ? "" : "s"}`
      : counts.elevatedFuel > 0
        ? `${counts.elevatedFuel} elevated fuel margin${counts.elevatedFuel === 1 ? "" : "s"}`
        : `${counts.routineFuel} routine fuel margin${counts.routineFuel === 1 ? "" : "s"}`;
    queueNarratedEntry({
      kind: "status",
      channel: "fleet-comms",
      speaker: "Engineering",
      text: `Engineering, ${fuelText}; margins are being watched.`,
      station: "engineering"
    });
  } else {
    queueNarratedEntry({
      kind: "status",
      channel: "fleet-comms",
      speaker: "Engineering",
      text: "Engineering, all tracked fuel margins routine.",
      station: "engineering"
    });
  }

  if (counts.traffic > 0) {
    queueNarratedEntry({
      kind: "status",
      channel: "traffic",
      speaker: "Traffic",
      text: `Traffic, ${counts.traffic} contact${counts.traffic === 1 ? "" : "s"} on screen and ${counts.moving} moving targets under watch.`,
      station: "traffic"
    });
  } else {
    queueNarratedEntry({
      kind: "status",
      channel: "traffic",
      speaker: "Traffic",
      text: "Traffic, screen clear.",
      station: "traffic"
    });
  }

  if (counts.pendingIntents > 0 || counts.disabledControls > 0) {
    const requestBits = [];
    if (counts.pendingIntents > 0) requestBits.push(`${counts.pendingIntents} escort request${counts.pendingIntents === 1 ? "" : "s"} pending review`);
    if (counts.disabledControls > 0) requestBits.push(`${counts.disabledControls} captain control${counts.disabledControls === 1 ? "" : "s"} disabled`);
    queueNarratedEntry({
      kind: "status",
      channel: "fleet-comms",
      speaker: "Bridge",
      text: `Bridge, ${requestBits.join("; ")}.`,
      station: "bridge"
    });
  }
}

function diffCaptainControls(controls) {
  if (!Array.isArray(controls)) return;
  if (lastCaptainControlSignatures === null) return;
  controls.forEach((control) => {
    const signature = captainControlSignature(control);
    const previous = lastCaptainControlSignatures.get(control.vessel_id);
    if (previous === signature) return;
    lastCaptainControlSignatures.set(control.vessel_id, signature);
    queueNarratedEntry({
      kind: "status",
      channel: "fleet-comms",
      speaker: "Bridge",
      text: `${control.captain_id} on ${control.vessel_id} is now ${control.runtime_status.toLowerCase()}${control.enabled ? "" : " and disabled"}.`,
      station: "bridge"
    });
  });
}

function diffEscortIntents(intents) {
  if (!Array.isArray(intents)) return;
  if (lastEscortIntentSignatures === null) return;
  intents.forEach((intent) => {
    const signature = escortIntentSignature(intent);
    const previous = lastEscortIntentSignatures.get(intent.decision_id);
    if (previous === signature) return;
    lastEscortIntentSignatures.set(intent.decision_id, signature);
    const posture = String(intent.posture || "").replace(/_/g, " ").toLowerCase();
    const objective = truncated(intent.objective, 96) || "unrecorded objective";
    const station = intent.posture === "InvestigateContact" ? "traffic" : "bridge";
    const text = intent.executed_tick == null
      ? `Bridge, ${intent.captain_id} requests ${posture} for ${intent.vessel_id}: ${objective}; awaiting decision.`
      : `Bridge, ${intent.captain_id}'s ${posture} request for ${intent.vessel_id} has been executed.`;
    queueNarratedEntry({
      kind: "status",
      channel: "fleet-comms",
      speaker: "Bridge",
      text,
      station
    });
  });
}

function diffAgentDecisions(records) {
  if (!Array.isArray(records)) return;
  if (lastAgentDecisionCount === null) return;
  if (records.length <= lastAgentDecisionCount) return;
  records.slice(lastAgentDecisionCount).forEach((record) => {
    const posture = String(record.posture || "").replace(/_/g, " ").toLowerCase();
    const outcome = String(record.outcome || "").toLowerCase();
    const shortResult = truncated(record.result, 108);
    queueNarratedEntry({
      kind: "watch",
      channel: "fleet-comms",
      speaker: "Bridge",
      text: `Decision ${outcome} for ${record.captain_id} on ${record.vessel_id}: ${posture}${shortResult ? ` — ${shortResult}` : ""}.`,
      station: "bridge"
    });
  });
  lastAgentDecisionCount = records.length;
}

function diffCanonEvents(events) {
  if (!Array.isArray(events)) return;
  if (lastCanonEventSeq === null) return;
  const fresh = events.filter((event) => canonEventCursor(event) > lastCanonEventSeq);
  if (!fresh.length) return;
  lastCanonEventSeq = Math.max(lastCanonEventSeq, ...fresh.map(canonEventCursor));
  queueNarratedEntry({
    kind: "status",
    channel: "fleet-comms",
    speaker: "Bridge",
    text: `Canon ledger advanced by ${fresh.length} change${fresh.length === 1 ? "" : "s"}.`,
    station: "bridge"
  });
}

function vesselById(id) {
  return (lastSnapshotVessels || []).find((vessel) => vessel.id === id) || null;
}

function vesselDisplayName(id) {
  const vessel = vesselById(id);
  if (!vessel) return id;
  return speakerNameFor(vessel);
}

function diffVesselEvents(events) {
  if (!Array.isArray(events)) return;
  if (lastVesselEventSeq === null) return;
  const fresh = events
    .filter((event) => vesselEventCursor(event) > lastVesselEventSeq)
    .sort((a, b) => vesselEventCursor(a) - vesselEventCursor(b));
  if (!fresh.length) return;
  lastVesselEventSeq = Math.max(lastVesselEventSeq, ...fresh.map(vesselEventCursor));

  fresh.forEach((event) => {
    switch (event.type) {
      case "route_replaced": {
        const name = vesselDisplayName(event.vessel_id);
        queueNarratedEntry({
          kind: "status",
          channel: "fleet-comms",
          speaker: "Bridge",
          text: `Bridge, ${name} route updated; ${event.remaining_leg_count} leg${event.remaining_leg_count === 1 ? "" : "s"} remain.`,
          station: "bridge"
        });
        break;
      }
      case "route_completed": {
        const name = vesselDisplayName(event.vessel_id);
        queueNarratedEntry({
          kind: "status",
          channel: "fleet-comms",
          speaker: "Bridge",
          text: `Bridge, ${name} route complete and vessel on station.`,
          station: "bridge"
        });
        break;
      }
      case "waypoint_reached": {
        const name = vesselDisplayName(event.vessel_id);
        const station = vesselById(event.vessel_id)?.kind === "passive-traffic" ? "traffic" : "bridge";
        queueNarratedEntry({
          kind: "status",
          channel: station === "traffic" ? "traffic" : "fleet-comms",
          speaker: station === "traffic" ? "Traffic" : "Bridge",
          text: `${station === "traffic" ? "Traffic" : "Bridge"}, ${name} cleared a waypoint; ${event.remaining_leg_count} leg${event.remaining_leg_count === 1 ? "" : "s"} remain.`,
          station
        });
        break;
      }
      case "holding": {
        const name = vesselDisplayName(event.vessel_id);
        queueNarratedEntry({
          kind: "status",
          channel: "fleet-comms",
          speaker: "Bridge",
          text: `Bridge, ${name} is holding station.`,
          station: "bridge"
        });
        break;
      }
      case "escort_station_changed": {
        const label = ESCORT_MODE_LABELS[event.new_mode] || event.new_mode;
        queueNarratedEntry({
          kind: "status",
          channel: "fleet-comms",
          speaker: "Bridge",
          text: `Bridge, escorts shifting to ${label}.`,
          station: "bridge"
        });
        break;
      }
      case "fuel_status_changed": {
        const name = vesselDisplayName(event.vessel_id);
        const recommendation = event.new_severity === "critical" ? "recommend holding" : "monitoring consumption";
        const percent = Math.round((event.fuel_fraction || 0) * 100);
        queueNarratedEntry({
          kind: "fuel",
          channel: "fleet-comms",
          speaker: "Engineering",
          text: `Engineering reports ${name} at ${percent} percent fuel margin, ${recommendation}.`,
          station: "engineering"
        });
        break;
      }
      default:
        break;
    }
  });
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
  if (nextState === "completed") {
    rememberStationTransmission(entry);
  }
  if (entry.transcriptNode) {
    const tags = entry.transcriptNode.querySelectorAll(".channel-tag");
    if (tags[2]) tags[2].textContent = nextState;
  }
  updateRadioStateIndicator();
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
  setAudioPathStage("synthesisRequested", "ok");
  // No SpeechSynthesis at all, muted, or no voices installed (common on
  // minimal Linux desktops and headless/sandboxed environments) all fall
  // back to the same timed visual cue -- a silent console that never shows
  // "Transmitting..." reads as broken, not quiet.
  const voices = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
  if (!window.speechSynthesis || state.muted || !voices.length) {
    // Muted is an operator choice, not a defect -- the remaining stages
    // are "unverified" (nothing to measure, but nothing is broken either).
    // No SpeechSynthesis / no voices is a real capability gap: those
    // stages are marked "fail" since audio genuinely cannot be produced.
    const reason = state.muted ? "muted" : (!window.speechSynthesis ? "no SpeechSynthesis API in this browser" : "no TTS voices installed");
    const status = state.muted ? "unverified" : "fail";
    ["audioGenerated", "streamDelivered", "playbackStarted", "audibleVerified"].forEach((stage) => setAudioPathStage(stage, status, reason));
    if (status === "fail") lastAudioFault = reason;
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
  utterance.onstart = () => {
    setSpeaking(true);
    // onstart is the only lifecycle signal the Web Speech API exposes --
    // there's no separate "buffer generated" / "handed to OS" event, so
    // audioGenerated/streamDelivered/playbackStarted all key off it
    // honestly rather than inventing false granularity.
    setAudioPathStage("audioGenerated", "ok");
    setAudioPathStage("streamDelivered", "ok");
    setAudioPathStage("playbackStarted", "ok");
    // Deliberately NOT "ok": SpeechSynthesis output is never routed through
    // the Web Audio graph, so this console has no analyser tap on it and
    // genuinely cannot measure whether sound left the speakers. onstart
    // firing proves the browser *attempted* playback, not that anything
    // was heard -- see AUDIO_PATH_STAGES' doc comment.
    setAudioPathStage("audibleVerified", "unverified", "browser speech output cannot be independently measured by this console (see Play Test Tone for a measured check)");
  };
  utterance.onend = () => {
    completeTransmission(entry);
  };
  utterance.onerror = (event) => {
    const detail = `speechSynthesis error: ${event && event.error ? event.error : "unknown"}`;
    ["audioGenerated", "streamDelivered", "playbackStarted", "audibleVerified"].forEach((stage) => {
      if (audioPathState[stage].status === "pending") setAudioPathStage(stage, "fail", detail);
    });
    lastAudioFault = detail;
    completeTransmission(entry, "completed");
  };
  // Safety net: if onstart/onend never fire at all (observed in some
  // sandboxed environments even when getVoices() reports voices), don't
  // leave the indicator stuck on "Transmitting..." forever.
  clearSpeechTimeout();
  speechTimeoutTimer = window.setTimeout(() => {
    speechTimeoutTimer = null;
    if (audioPathState.audioGenerated.status === "pending") {
      const detail = "onstart never fired within the expected window";
      ["audioGenerated", "streamDelivered", "playbackStarted", "audibleVerified"].forEach((stage) => setAudioPathStage(stage, "fail", detail));
      lastAudioFault = detail;
    }
    completeTransmission(entry);
  }, estimatedSpeakingMs(entry.text) + 2000);
  window.speechSynthesis.speak(utterance);
}

// --- Diagnostics: Audio Path Status, Content Queue, Test Controls, Output ---
// (Captain's packet, RADIO CONSOLE — ESSENTIAL FEATURE PACKET, 2026-07-16.
// Operating rule: "Connected is not the same as heard.")

function setAudioPathStage(stage, status, detail) {
  audioPathState[stage] = { status, detail: detail || "" };
  renderAudioPath();
  updateDiagnostics();
}

function resetAudioPath() {
  AUDIO_PATH_STAGES.forEach((stage) => { audioPathState[stage] = { status: "pending", detail: "" }; });
  lastAudioFault = null;
  renderAudioPath();
  updateDiagnostics();
}

function renderAudioPath() {
  if (!audioPathListEl) return;
  AUDIO_PATH_STAGES.forEach((stage) => {
    const li = audioPathListEl.querySelector(`[data-stage="${stage}"]`);
    if (!li) return;
    const entry = audioPathState[stage];
    li.classList.remove("stage-pending", "stage-ok", "stage-fail", "stage-unverified");
    li.classList.add(`stage-${entry.status}`);
    li.title = entry.detail || "";
  });
}

// Real, measured level -- taps masterGain (everything routed to the
// speakers except SpeechSynthesis output, which browsers never expose to
// Web Audio; see speak()'s onstart handler). This is what makes "audible
// output verified" for the test tone an actual measurement rather than a
// claim, per packet §3/§4.
function ensureAnalyser() {
  if (!audioContext || analyserNode) return;
  analyserNode = audioContext.createAnalyser();
  analyserNode.fftSize = 256;
  analyserData = new Uint8Array(analyserNode.frequencyBinCount);
  masterGain.connect(analyserNode);
}

function currentLevel() {
  if (!analyserNode) return 0;
  analyserNode.getByteTimeDomainData(analyserData);
  let sumSquares = 0;
  for (let i = 0; i < analyserData.length; i += 1) {
    const norm = (analyserData[i] - 128) / 128;
    sumSquares += norm * norm;
  }
  return Math.sqrt(sumSquares / analyserData.length);
}

function logDiag(action, result, detail) {
  diagLogEntries.push({ at: Date.now(), action, result, detail: detail || "" });
  while (diagLogEntries.length > 30) diagLogEntries.shift();
  renderDiagLog();
}

function renderDiagLog() {
  if (!diagLogEl) return;
  if (!diagLogEntries.length) {
    diagLogEl.innerHTML = `<li class="empty-note">No diagnostic actions run yet.</li>`;
    return;
  }
  diagLogEl.innerHTML = diagLogEntries
    .map((entry) => {
      const time = new Date(entry.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      const cls = entry.result === "fail" ? "log-fail" : entry.result === "ok" || entry.result === "pass" || entry.result === "accepted" ? "log-ok" : "";
      return `<li class="${cls}"><span class="timestamp">${time}</span> ${entry.action}: ${entry.result}${entry.detail ? ` — ${entry.detail}` : ""}</li>`;
    })
    .join("");
}

function pathSummaryLabel() {
  if (AUDIO_PATH_STAGES.some((stage) => audioPathState[stage].status === "fail")) return "FAULT";
  if (audioPathState.audibleVerified.status === "ok") return "VERIFIED";
  return "UNVERIFIED";
}

// Overall Radio State (packet §1) -- deliberately conservative. "LIVE" is
// only ever reached via a measured-audible test tone pass this session
// (see runTestTone()), never merely because content is flowing. A
// transmission completing proves the browser attempted speech, not that
// anything was heard.
function deriveOverallRadioState() {
  if (!state.powered) return "IDLE";
  if (!liveMode) return "FAULT";
  if (lastAudioFault) return "FAULT";
  if (audioConfirmedThisSession) return "LIVE";
  return "UNVERIFIED";
}

function updateDiagSummary() {
  if (!diagSummaryLine) return;
  const loop = state.powered && liveMode ? "ACTIVE" : "IDLE";
  diagSummaryLine.textContent = `RADIO ${deriveOverallRadioState()} — CONTENT ${loop} — AUDIO PATH ${pathSummaryLabel()}`;
}

function updateDiagnostics() {
  if (diagQueuedCountEl) diagQueuedCountEl.textContent = String(liveQueue.length);
  if (diagCurrentMessageEl) {
    diagCurrentMessageEl.textContent = state.currentTransmission
      ? `${state.currentTransmission.speaker}: ${state.currentTransmission.text}`
      : "—";
  }
  if (diagLastAcceptedEl) {
    diagLastAcceptedEl.textContent = lastAcceptedEntry
      ? `${lastAcceptedEntry.speaker} (${lastAcceptedEntry.source})`
      : "—";
  }
  if (diagLoopStateEl) diagLoopStateEl.textContent = state.powered && liveMode ? "Active" : "Idle";
  if (diagSourceTagEl) {
    diagSourceTagEl.textContent = state.currentTransmission
      ? (state.currentTransmission.source || "unknown")
      : "—";
  }
  updateDiagSummary();
}

// --- Test Controls (packet §4) ---
// Every control here must produce a logged, reviewable result -- see
// logDiag() calls below. None of these three simulate success; each one
// drives the exact same speak()/audio-path machinery real content uses.

function runTestTone() {
  if (activeTestTone) return; // already running, ignore a double-click
  initAudio();
  if (!audioContext) {
    logDiag("test_tone", "fail", "Web Audio unavailable in this browser.");
    return;
  }
  if (audioContext.state === "suspended") audioContext.resume();
  ensureAnalyser();
  resetAudioPath();
  setAudioPathStage("synthesisRequested", "ok");
  // Claim the same "currently speaking" slot livePump() already respects
  // (state.speaking + currentTransmissionScore), scored higher than
  // anything real content can reach -- otherwise, in a world this
  // chatty, a real transmission firing mid-measurement calls
  // transmitEntry() -> resetAudioPath() and silently overwrites the
  // test tone's result before the 400ms sample window even finishes.
  // Also explicitly interrupt whatever might already be mid-flight: a
  // real transmission's own speechTimeoutTimer keeps ticking regardless
  // of who "owns" state.speaking, and completeTransmission() clears
  // state.speaking/currentTransmissionScore unconditionally when it
  // fires -- without this, that pre-existing timer firing mid-test
  // silently releases this lock out from under the test tone. The
  // permanent diagLog entry below would still be correct either way, but
  // the live Audio Path Status panel would show something else's result
  // instead of this test's. Released in sample()'s completion branch below.
  interruptCurrentTransmission();
  setSpeaking(true);
  state.currentTransmissionScore = Infinity;
  const osc = audioContext.createOscillator();
  osc.type = "sine";
  osc.frequency.value = 440;
  const toneGain = audioContext.createGain();
  toneGain.gain.value = 0.25;
  osc.connect(toneGain);
  toneGain.connect(masterGain);
  setAudioPathStage("audioGenerated", "ok");
  const now = audioContext.currentTime;
  osc.start(now);
  activeTestTone = osc;
  setAudioPathStage("streamDelivered", "ok");
  setAudioPathStage("playbackStarted", "ok");

  let peak = 0;
  let samples = 0;
  const startedAt = performance.now();
  const NOISE_FLOOR = 0.02;
  const SAMPLE_WINDOW_MS = 400;
  function sample() {
    peak = Math.max(peak, currentLevel());
    samples += 1;
    if (performance.now() - startedAt < SAMPLE_WINDOW_MS) {
      window.requestAnimationFrame(sample);
      return;
    }
    try { osc.stop(); } catch (error) { /* already stopped */ }
    activeTestTone = null;
    const audible = peak > NOISE_FLOOR;
    const detail = `measured peak RMS ${peak.toFixed(3)} over ${samples} samples (noise floor ${NOISE_FLOOR})`;
    setAudioPathStage("audibleVerified", audible ? "ok" : "fail", detail);
    if (audible) {
      audioConfirmedThisSession = true;
      lastAudioFault = null;
    } else {
      lastAudioFault = "test tone produced no measurable signal";
    }
    logDiag("test_tone", audible ? "pass" : "fail", detail);
    updateDiagSummary();
    // Hold the slot a little longer than the measurement itself so the
    // completed result is actually visible to a human before real content
    // (which in an active world can resume within milliseconds of the
    // slot opening) overwrites it via the next transmitEntry()'s
    // resetAudioPath(). The diagLog entry above is permanent regardless;
    // this hold is only about the live Audio Path Status panel.
    window.setTimeout(() => {
      setSpeaking(false);
      state.currentTransmissionScore = -Infinity;
      window.setTimeout(livePump, 0);
    }, 1800);
  }
  window.requestAnimationFrame(sample);
}

function runTestMessage() {
  if (!state.powered) {
    logDiag("inject_test_message", "fail", "Radio is powered off.");
    return;
  }
  const entry = {
    kind: "watch",
    channel: "fleet-comms",
    speaker: "Diagnostics",
    // sourceAuthority "human" matches the existing RecordWatchEvent
    // precedent (TRANSMISSION_PROFILES.watch) -- a deliberate operator
    // action, not routine chatter, so it isn't silently dropped by
    // radio_silence/quiet_watch the way ordinary status entries are.
    sourceAuthority: "human",
    text: "This is a Radio Console diagnostic test message.",
    station: "bridge",
    source: "simulated"
  };
  queueLiveEntry(entry);
  logDiag("inject_test_message", "accepted", "Queued for transmission through the real content pipeline.");
}

function runStopPlayback() {
  if (window.speechSynthesis) window.speechSynthesis.cancel();
  if (activeTestTone) {
    try { activeTestTone.stop(); } catch (error) { /* already stopped */ }
    activeTestTone = null;
  }
  interruptCurrentTransmission();
  logDiag("stop_playback", "ok", "Playback stopped.");
  updateDiagnostics();
}

// --- Output Controls: device selection (packet §5) ---
// Best-effort: AudioContext.setSinkId is a newer, Chromium-first API, and
// even where supported it can only route the Web Audio graph (the static
// bed, squelch, and test tone) -- SpeechSynthesis output has no device-
// selection API in any browser. Both constraints are surfaced honestly
// rather than pretending device selection covers all audio on the page.
async function populateOutputDevices() {
  if (!outputDeviceSelect) return;
  if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
    outputDeviceSelect.innerHTML = `<option value="">Not supported in this browser</option>`;
    outputDeviceSelect.disabled = true;
    return;
  }
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const outputs = devices.filter((device) => device.kind === "audiooutput");
    if (!outputs.length) return; // keep the "System default" placeholder
    outputDeviceSelect.innerHTML =
      `<option value="">System default</option>` +
      outputs.map((device) => `<option value="${device.deviceId}">${device.label || "Output device"}</option>`).join("");
    if (typeof AudioContext !== "undefined" && !AudioContext.prototype.setSinkId) {
      outputDeviceSelect.title = "This browser can list output devices but cannot route audio to a non-default one (AudioContext.setSinkId unsupported). Selection will have no effect.";
    }
  } catch (error) {
    // Real failure (not every browser grants this without a prior
    // getUserMedia permission) -- leave the default option in place rather
    // than claiming a device list that isn't real.
  }
}

if (outputDeviceSelect) {
  outputDeviceSelect.addEventListener("change", async () => {
    const deviceId = outputDeviceSelect.value;
    if (!audioContext || typeof audioContext.setSinkId !== "function") {
      logDiag("select_output_device", "fail", "AudioContext.setSinkId unsupported in this browser -- device selection has no effect here.");
      return;
    }
    try {
      await audioContext.setSinkId(deviceId || "default");
      logDiag("select_output_device", "ok", deviceId ? `Routed Web Audio output to ${outputDeviceSelect.selectedOptions[0]?.textContent}` : "Routed to system default.");
    } catch (error) {
      logDiag("select_output_device", "fail", String(error));
    }
  });
}

if (testToneButton) testToneButton.addEventListener("click", runTestTone);
if (testMessageButton) testMessageButton.addEventListener("click", runTestMessage);
if (stopPlaybackButton) stopPlaybackButton.addEventListener("click", runStopPlayback);

function transmitEntry(entry) {
  state.currentTransmission = entry;
  state.currentTransmissionScore = entry.score ?? scoreTransmission(entry);
  recordThreadState(entry, "acked");
  appendTranscript(entry);
  resetAudioPath();
  speak(entry);
  updateDiagnostics();
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
  lastAcceptedEntry = queued;
  updateDiagnostics();
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

const ESCORT_MODE_LABELS = {
  off: "escort stood down",
  loose: "loose escort",
  patrol: "patrol escort",
  tight: "tight escort",
  screen: "screening formation"
};

// Fleet-wide (World::escort_mode is one value for the whole fleet, not
// per-vessel -- see fleetcore/src/vessel.rs's EscortStationChanged doc
// comment), so this is a single scalar diff, not a per-vessel map like
// diffVesselStates/diffFuelLevels above.
function diffEscortMode(escortMode) {
  if (typeof escortMode !== "string") return;
  const seeding = lastEscortMode === null;
  const previous = lastEscortMode;
  lastEscortMode = escortMode;
  if (seeding || previous === escortMode) return;
  const label = ESCORT_MODE_LABELS[escortMode] || escortMode;
  queueLiveEntry({
    kind: "status",
    channel: "fleet-comms",
    speaker: "Bridge",
    text: `Bridge, escorts shifting to ${label}.`,
    station: "bridge"
  });
}

function diffWatchEvents(watchEvents) {
  const events = watchEvents || [];
  const seeding = lastWatchEventCount === null;
  if (seeding || events.length <= lastWatchEventCount) {
    lastWatchEventCount = events.length;
    return;
  }
  // Fixes a real starvation bug: before this, every power-on/reconnect
  // replayed the *entire* watch-event history at once (lastWatchEventCount
  // started at 0, so a multi-day-old backlog looked "new"). Those replayed
  // entries are watch-kind (authority 1.0, 30s expiry) and always outscore
  // status-kind entries (authority 0.86, 12s expiry) in scoreTransmission,
  // so anything else -- including a fresh EscortStationChanged/fuel report
  // -- got queued behind them and silently expired before ever airing.
  // Seeding on the first snapshot (matching diffVesselStates/diffFuelLevels'
  // existing pattern) means only genuinely new watch events queue at all.
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
  snapshotNarrationBudget = MAX_CONTENT_LINES_PER_SNAPSHOT;
  if (firstOperationalSnapshot) {
    queueBaselineOperationalWatch(snapshot);
    initializeOperationalCursors(snapshot);
    firstOperationalSnapshot = false;
  }
  diffWatchEvents(snapshot.watch_events);
  diffVesselStates(snapshot.vessels || []);
  diffFuelLevels(snapshot.vessels || []);
  diffCaptainControls(snapshot.captain_controls || []);
  diffEscortIntents(snapshot.escort_intents || []);
  diffAgentDecisions(snapshot.agent_decisions || []);
  diffCanonEvents(snapshot.canon_events || []);
  diffVesselEvents(snapshot.vessel_events || []);
  diffEscortMode(snapshot.escort_mode);
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
  // quiet_watch is a real operating mode too, not just a label: caught by
  // this task's own acceptance-test pass showing "PREPARING REPORT" while
  // quiet_watch was selected, because nothing actually suppressed routine
  // traffic. Suppresses routine status chatter; watch notes (human) and
  // fuel reports at elevated/critical severity still get through -- quiet
  // watch means "don't chatter," not "hide a real emergency."
  const quietWatch = discipline === "quiet_watch";

  let next = null;
  for (const entry of liveQueue) {
    if (!state.activeChannels.has(entry.channel)) continue;
    if (!stationCanObserve(entry, state.selectedStation)) continue;
    if (silenced && entry.sourceAuthority !== "human") continue;
    if (quietWatch && entry.kind === "status") continue;
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
  // Output Controls' "current audio level meter" (packet §5) -- kept
  // deliberately separate from the decorative bars above. This is a real
  // AnalyserNode reading of the Web Audio graph (static bed, squelch, test
  // tone), never randomized, and never boosted just because state.speaking
  // is true: it only rises when this console can actually prove signal is
  // present. It reads near-zero during ordinary speech, honestly, because
  // SpeechSynthesis output doesn't pass through this analyser at all.
  const measured = currentLevel();
  if (outputLevelMeterEl) outputLevelMeterEl.value = measured;
  if (outputLevelReadoutEl) outputLevelReadoutEl.textContent = `${Math.round(measured * 100)}%`;
  state.animationFrame = window.requestAnimationFrame(drawSignalMeter);
}

function renderNewswire(payload) {
  if (!payload || !Array.isArray(payload.items) || payload.items.length === 0) {
    newswireLogEl.innerHTML = '<li class="empty-note">No headlines available.</li>';
    return;
  }
  newswireUpdatedEl.textContent = new Date(payload.fetched_at).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit"
  });
  newswireLogEl.replaceChildren();
  const selectTopic = (item, row) => {
    stopNewswireSpeech();
    newswireLogEl.querySelectorAll("li").forEach((entry) => entry.classList.remove("is-selected"));
    row.classList.add("is-selected");
    newswireTopicTitleEl.textContent = item.title;
    newswireTopicTimeEl.textContent = item.pubDate
      ? `NPR · ${new Date(item.pubDate).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}`
      : "NPR News Headlines";
    newswireTopicLinkEl.href = item.link;
    selectedNewswireItem = item;
    newswireTopicEl.hidden = false;
  };
  payload.items.forEach((item, index) => {
    const row = document.createElement("li");
    const button = document.createElement("button");
    const timestamp = document.createElement("span");
    button.type = "button";
    button.textContent = item.title;
    timestamp.className = "timestamp";
    timestamp.textContent = item.pubDate
      ? new Date(item.pubDate).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      : "";
    button.addEventListener("click", () => selectTopic(item, row));
    row.append(button, timestamp);
    newswireLogEl.appendChild(row);
    if (index === 0) selectTopic(item, row);
  });
}

function stopNewswireSpeech() {
  if (newswireUtterance && window.speechSynthesis) window.speechSynthesis.cancel();
  newswireUtterance = null;
  newswireReadButton.textContent = "Read NPR headline";
  newswireVoiceStatusEl.textContent = "News voice idle · separate from fleet radio";
  newswireVoiceStatusEl.classList.remove("is-reading");
}

function readSelectedNewswireHeadline() {
  if (newswireUtterance) return stopNewswireSpeech();
  if (!selectedNewswireItem || !window.speechSynthesis || typeof SpeechSynthesisUtterance === "undefined") {
    newswireVoiceStatusEl.textContent = "News voice unavailable in this browser";
    return;
  }
  const utterance = new SpeechSynthesisUtterance(`From NPR News Headlines. ${selectedNewswireItem.title}`);
  const voices = window.speechSynthesis.getVoices();
  utterance.voice = voices.find((voice) => /^en(-|_)/i.test(voice.lang) && /natural|enhanced|premium/i.test(voice.name))
    || voices.find((voice) => /^en(-|_)/i.test(voice.lang))
    || null;
  utterance.rate = 0.96;
  utterance.pitch = 1;
  utterance.volume = volumeToLinear();
  utterance.onstart = () => {
    newswireReadButton.textContent = "Stop NPR reading";
    newswireVoiceStatusEl.textContent = `Reading NPR headline${utterance.voice ? ` · ${utterance.voice.name}` : ""}`;
    newswireVoiceStatusEl.classList.add("is-reading");
  };
  utterance.onend = stopNewswireSpeech;
  utterance.onerror = stopNewswireSpeech;
  newswireUtterance = utterance;
  window.speechSynthesis.speak(utterance);
}

newswireReadButton.addEventListener("click", readSelectedNewswireHeadline);

async function fetchNewswire() {
  try {
    const response = await fetch(`${NEWSWIRE_URL}?t=${Date.now()}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    renderNewswire(await response.json());
  } catch (error) {
    console.warn("Radio Console: newswire fetch failed", error);
  }
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
    ensureAnalyser();
    applyVolume();
    // No scripted schedule to start -- transmissions only ever come from
    // the live FleetCore queue (see enterLiveMode()/livePump()). If not
    // connected yet, the console just sits Offline until it is.
    fetchNewswire();
    clearInterval(newswireRefreshTimer);
    newswireRefreshTimer = window.setInterval(fetchNewswire, NEWSWIRE_REFRESH_MS);
  } else {
    clearSpeechTimeout();
    clearCurrentTransmission();
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    liveQueue.length = 0;
    setSpeaking(false);
    clearInterval(newswireRefreshTimer);
    newswireRefreshTimer = null;
    resetAudioPath();
  }
  updateDiagnostics();
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
resetAudioPath();
populateOutputDevices();
if (navigator.mediaDevices && navigator.mediaDevices.addEventListener) {
  navigator.mediaDevices.addEventListener("devicechange", populateOutputDevices);
}
drawSignalMeter();

// Live is the default now (Admiral's call, 2026-07-11), matching Fleet
// Motion: every page load attempts a FleetCore connection. Scripted
// chatter still works exactly as before unless/until a snapshot actually
// arrives; a failed attempt fails closed and silently at the application
// level (see connectFleetCoreLive()'s timeout), it's only the accepted
// browser-native console error tradeoff that changed, not the fallback
// behavior. ?fleetcoreServer= still overrides the server URL if needed.
connectFleetCoreLive();
