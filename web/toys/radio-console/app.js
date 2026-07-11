// Ambience-only bridge instrument: scripted transmissions, spoken aloud via
// the browser's SpeechSynthesis API where available, over a synthesized
// static bed and squelch pops built with Web Audio. No FleetCore
// dependency -- see ../../fleetcore/ENGINEERING_REPORT.md's toy list for
// why: this is presentation layer, not world state, and works identically
// whether or not any live backend exists.
const TRANSMISSIONS = [
  { channel: "fleet-comms", speaker: "Watch Officer", text: "Scout Alpha, Monad Actual, report position and status." },
  { channel: "fleet-comms", speaker: "Scout Alpha", text: "Monad Actual, Scout Alpha, holding station, all quiet." },
  { channel: "fleet-comms", speaker: "Scout Bravo", text: "Bridge, this is Scout Bravo, screen clear, no contacts of interest." },
  { channel: "fleet-comms", speaker: "Scout Charlie", text: "Monad Actual, Scout Charlie, contact bearing two-seven-zero, range eight, no immediate concern." },
  { channel: "fleet-comms", speaker: "Watch Officer", text: "All stations, Monad Actual, course and speed unchanged, log entry recorded." },
  { channel: "fleet-comms", speaker: "Scout Alpha", text: "Monad Actual, Scout Alpha, relieving Bravo on picket in five." },
  { channel: "fleet-comms", speaker: "Watch Officer", text: "Fleet, Monad Actual, radio check, respond in sequence." },
  { channel: "weather", speaker: "Coastal Weather Service", text: "Arabian Sea advisory: winds light and variable, sea state one, visibility unrestricted." },
  { channel: "weather", speaker: "Coastal Weather Service", text: "Weather update: haze reducing visibility to six nautical miles near the strait, monitor radar." },
  { channel: "weather", speaker: "Coastal Weather Service", text: "No small craft advisories in effect. Swell under one meter through the watch." },
  { channel: "weather", speaker: "Coastal Weather Service", text: "Overnight forecast: clear skies, light easterly breeze, no change expected before dawn." },
  { channel: "weather", speaker: "Coastal Weather Service", text: "Barometric pressure steady. No systems tracked within two hundred nautical miles." },
  { channel: "traffic", speaker: "Harbor Control", text: "Tanker Gulf Star, requesting routing clearance, over." },
  { channel: "traffic", speaker: "Dhow Lantern", text: "All stations, this is Dhow Lantern, transiting outbound, maintaining course and speed." },
  { channel: "traffic", speaker: "Pilot Amber", text: "Harbor Control, Pilot Amber, pilot aboard, proceeding to berth." },
  { channel: "traffic", speaker: "Coaster Qeshm", text: "Coaster Qeshm, standing by on channel, holding for inbound clearance." },
  { channel: "traffic", speaker: "Harbor Control", text: "All stations, routine traffic advisory, channel congestion expected near the anchorage through the watch." },
  { channel: "traffic", speaker: "Gulf Star", text: "Harbor Control, Gulf Star, clearance received, underway." }
];

const CHANNEL_LABELS = {
  "fleet-comms": "Fleet Comms",
  weather: "Weather",
  traffic: "Traffic"
};

const MIN_INTERVAL_MS = 6000;
const MAX_INTERVAL_MS = 16000;
const SQUELCH_DURATION_S = 0.12;

const powerButton = document.querySelector("#powerButton");
const powerStatusEl = document.querySelector("#powerStatus");
const channelCountEl = document.querySelector("#channelCount");
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
  scheduleTimer: null,
  speaking: false,
  voiceForSpeaker: new Map(),
  animationFrame: null,
  meterLevels: new Array(24).fill(0.08)
};

let audioContext = null;
let masterGain = null;
let staticGain = null;
let noiseBuffer = null;

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
  staticGain.gain.value = 0.05;
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
  staticGain.gain.linearRampToValueAtTime(down ? 0.012 : 0.05, now + (down ? 0.15 : 0.4));
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

function transmit() {
  const pool = TRANSMISSIONS.filter((entry) => state.activeChannels.has(entry.channel));
  if (!pool.length) return;
  const entry = pool[Math.floor(Math.random() * pool.length)];
  appendTranscript(entry);
  speak(entry);
}

function scheduleNext() {
  window.clearTimeout(state.scheduleTimer);
  if (!state.powered) return;
  const delay = MIN_INTERVAL_MS + Math.random() * (MAX_INTERVAL_MS - MIN_INTERVAL_MS);
  state.scheduleTimer = window.setTimeout(() => {
    if (state.activeChannels.size) transmit();
    scheduleNext();
  }, delay);
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
    scheduleNext();
  } else {
    window.clearTimeout(state.scheduleTimer);
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
