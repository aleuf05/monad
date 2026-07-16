const $ = (id) => document.getElementById(id);
const axes = ["tension", "warmth", "energy", "restraint"];
let handle = null;
let availableVoices = [];
let voiceAssignments = {};
const voiceOverrides = new Map();
let richConfigured = false;
let lastRichEstimate = null;

function richPayload() {
  const character = selectedCharacter();
  const tension = Number($("tension").value);
  const warmth = Number($("warmth").value);
  const energy = Number($("energy").value);
  const restraint = Number($("restraint").value);
  return {
    character_id: character.id,
    transcript: $("text").value.trim(),
    performance: {
      intent: $("intent").value,
      audience: "the listener",
      setting: "a close, dry studio recording",
      affect: `tension ${tension}/100, warmth ${warmth}/100, energy ${energy}/100`,
      pace: energy > 70 ? "brisk but intelligible" : energy < 35 ? "slow and reflective" : "measured",
      restraint: `${restraint}/100; remain natural and resist caricature`
    }
  };
}

async function richRequest(path, payload) {
  const response = await fetch(`/voice-api/${path}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `Rich voice ${response.status}`);
  return result;
}

fetch("/voice-api/status").then((response) => response.json()).then((status) => {
  richConfigured = status.configured;
  $("richStatus").textContent = status.configured
    ? `Rich voice ready · Gemini · $${status.budget.usd_used.toFixed(4)} / $${status.budget.usd_limit.toFixed(2)} today`
    : "Rich voice service online · Gemini key not commissioned · free rehearsal remains available";
}).catch(() => { $("richStatus").textContent = "Rich voice service not commissioned · free rehearsal remains available"; });

function selectedCharacter() { return MonadCharacters.get($("character").value); }
function showCharacter() {
  const character = selectedCharacter();
  $("role").textContent = character.role;
  $("description").textContent = character.description;
  const binding = voiceOverrides.get(character.id) || voiceAssignments[character.id];
  if (binding) $("voice").value = binding.voice_id;
}

async function discoverVoices() {
  const provider = MonadVoice.listProviders().find((item) => item.id === "browser-speechsynthesis");
  availableVoices = provider ? await provider.listVoices() : [];
  voiceAssignments = MonadCharacters.assignVoices(availableVoices);
  $("voice").replaceChildren(...availableVoices.map((voice) => new Option(`${voice.label} · ${voice.lang || "unknown language"}`, voice.voice_id)));
  const distinct = new Set(Object.values(voiceAssignments).filter(Boolean).map((voice) => voice.voice_id)).size;
  const enough = availableVoices.length >= MonadCharacters.list().length;
  $("voiceCoverage").textContent = enough ? `Distinct cast ready · ${distinct} voices assigned.` : `Limited cast · device exposes ${availableVoices.length} voice(s); some characters must share.`;
  $("voiceCoverage").classList.toggle("limited", !enough);
  showCharacter();
}

MonadCharacters.list().forEach((character) => {
  $("character").add(new Option(character.name, character.id));
});
$("character").value = "captain.monad";
showCharacter();
$("character").addEventListener("change", showCharacter);
$("voice").addEventListener("change", () => {
  const voice = availableVoices.find((item) => item.voice_id === $("voice").value);
  if (voice) voiceOverrides.set(selectedCharacter().id, voice);
});
axes.forEach((axis) => $(axis).addEventListener("input", () => { $(`${axis}Out`).value = $(axis).value; }));
discoverVoices().catch((error) => { $("voiceCoverage").textContent = error.message; });

$("speak").addEventListener("click", async () => {
  if (handle) { handle.stop(); handle = null; }
  const character = selectedCharacter();
  const voice = voiceOverrides.get(character.id) || voiceAssignments[character.id];
  const controls = Object.fromEntries(axes.map((axis) => [axis, Number($(axis).value) / 100]));
  const performance = MonadPerformance.plan(character.id, {
    character: character.traits,
    intent: $("intent").value,
    controls,
    context: { surface: "character-voice-studio", operator_directed: true }
  });
  MonadVoice.setProfile({ speaker: character.id, ...character.voice, voice_id: voice?.voice_id, ...performance.voice });
  $("inspection").textContent = `${character.name} · ${voice?.label || "no installed voice"} · ${performance.label}\n${axes.map((axis) => `${axis}: ${Math.round(performance.axes[axis] * 100)} → ${Math.round(performance.target[axis] * 100)}`).join(" · ")}\n${performance.reasons.join(" / ")}`;
  $("status").textContent = "Requesting voice…";
  try {
    const result = await MonadVoice.speak(character.id, $("text").value.trim() || "No line entered.");
    handle = result.handle;
    handle.onstart = () => { $("status").textContent = `Performing · ${handle.voice_label || handle.provider_label}`; };
    handle.onend = () => { handle = null; $("status").textContent = "Performance complete"; };
    handle.onerror = () => { handle = null; $("status").textContent = "Voice failed"; };
  } catch (error) { $("status").textContent = error.message; }
});

$("reset").addEventListener("click", () => {
  MonadPerformance.reset(selectedCharacter().id);
  $("inspection").textContent = "Continuity reset for selected character.";
});

$("estimateRich").addEventListener("click", async () => {
  $("generateRich").disabled = true;
  $("richStatus").textContent = "Estimating locally — no Gemini call…";
  try {
    lastRichEstimate = await richRequest("estimate", richPayload());
    $("richStatus").textContent = lastRichEstimate.cache_hit
      ? "Cached rich take ready · generation cost $0"
      : `New rich take · up to ${lastRichEstimate.seconds.toFixed(1)} sec · estimated $${lastRichEstimate.max_usd.toFixed(4)} · generation requires one explicit click`;
    $("generateRich").disabled = !(lastRichEstimate.cache_hit || richConfigured);
  } catch (error) { $("richStatus").textContent = error.message; }
});

$("generateRich").addEventListener("click", async () => {
  $("generateRich").disabled = true;
  $("richStatus").textContent = lastRichEstimate?.cache_hit ? "Loading cached take…" : "Generating one Gemini rich take…";
  try {
    const artifact = await richRequest("render", richPayload());
    const audio = $("richAudio");
    audio.src = artifact.audio_url;
    audio.hidden = false;
    await audio.play();
    $("richStatus").textContent = `${artifact.cache_hit ? "Cached" : "Generated"} rich take · ${artifact.seconds.toFixed(1)} sec · $${artifact.usd.toFixed(4)}`;
  } catch (error) { $("richStatus").textContent = error.message; }
});
