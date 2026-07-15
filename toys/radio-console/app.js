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

const powerButton = document.querySelector("#powerButton");
const powerStatusEl = document.querySelector("#powerStatus");
const channelCountEl = document.querySelector("#channelCount");
const dataSourceEl = document.querySelector("#dataSourceValue");
const channelChips = Array.from(document.querySelectorAll(".channel-chip"));
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
  speaking: false,
  voiceForSpeaker: new Map(),
  animationFrame: null,
  meterLevels: new Array(24).fill(0.08)
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
let lastVesselStatus = null; // Map<vesselId, status>, null until the first live snapshot seeds it
let lastWatchEventCount = 0;
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
    `<span class="speaker">${entry.speaker}</span>${entry.text}` +
    `<span class="timestamp">${time}</span>`;
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

function speak(entry) {
  // No SpeechSynthesis at all, muted, or no voices installed (common on
  // minimal Linux desktops and headless/sandboxed environments) all fall
  // back to the same timed visual cue -- a silent console that never shows
  // "Transmitting..." reads as broken, not quiet.
  const voices = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
  if (!window.speechSynthesis || state.muted || !voices.length) {
    setSpeaking(true);
    window.setTimeout(() => setSpeaking(false), estimatedSpeakingMs(entry.text));
    return;
  }
  const utterance = new SpeechSynthesisUtterance(entry.text);
  const voice = pickVoiceFor(entry.speaker);
  if (voice) utterance.voice = voice;
  utterance.volume = volumeToLinear();
  utterance.rate = 1.05;
  utterance.pitch = 0.95;
  utterance.onstart = () => setSpeaking(true);
  utterance.onend = () => setSpeaking(false);
  utterance.onerror = () => setSpeaking(false);
  // Safety net: if onstart/onend never fire at all (observed in some
  // sandboxed environments even when getVoices() reports voices), don't
  // leave the indicator stuck on "Transmitting..." forever.
  window.setTimeout(() => setSpeaking(false), estimatedSpeakingMs(entry.text) + 2000);
  window.speechSynthesis.speak(utterance);
}

function transmitEntry(entry) {
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
  liveQueue.push(entry);
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
    queueLiveEntry({ channel, speaker: name, text: `${name}, ${line}` });
  });
}

function diffWatchEvents(watchEvents) {
  const events = watchEvents || [];
  if (events.length <= lastWatchEventCount) {
    lastWatchEventCount = events.length;
    return;
  }
  events.slice(lastWatchEventCount).forEach((event) => {
    queueLiveEntry({ channel: "fleet-comms", speaker: "Watch Officer", text: event.message });
  });
  lastWatchEventCount = events.length;
}

function applyLiveSnapshot(snapshot) {
  diffWatchEvents(snapshot.watch_events);
  diffVesselStates(snapshot.vessels || []);
}

function livePump() {
  if (!state.powered || state.speaking || !liveQueue.length) return;
  const next = liveQueue.find((entry) => state.activeChannels.has(entry.channel));
  if (!next) {
    liveQueue.length = 0; // Nothing filtered-in queued is worth holding onto once channels change.
    return;
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
    if (window.speechSynthesis) window.speechSynthesis.cancel();
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
drawSignalMeter();

// Live is the default now (Admiral's call, 2026-07-11), matching Fleet
// Motion: every page load attempts a FleetCore connection. Scripted
// chatter still works exactly as before unless/until a snapshot actually
// arrives; a failed attempt fails closed and silently at the application
// level (see connectFleetCoreLive()'s timeout), it's only the accepted
// browser-native console error tradeoff that changed, not the fallback
// behavior. ?fleetcoreServer= still overrides the server URL if needed.
connectFleetCoreLive();
