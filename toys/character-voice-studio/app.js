const $ = (id) => document.getElementById(id);
const axes = ["tension", "warmth", "energy", "restraint"];
let handle = null;

function selectedCharacter() { return MonadCharacters.get($("character").value); }
function showCharacter() {
  const character = selectedCharacter();
  $("role").textContent = character.role;
  $("description").textContent = character.description;
}

MonadCharacters.list().forEach((character) => {
  $("character").add(new Option(character.name, character.id));
});
$("character").value = "captain.monad";
showCharacter();
$("character").addEventListener("change", showCharacter);
axes.forEach((axis) => $(axis).addEventListener("input", () => { $(`${axis}Out`).value = $(axis).value; }));

$("speak").addEventListener("click", async () => {
  if (handle) { handle.stop(); handle = null; }
  const character = selectedCharacter();
  const controls = Object.fromEntries(axes.map((axis) => [axis, Number($(axis).value) / 100]));
  const performance = MonadPerformance.plan(character.id, {
    character: character.traits,
    intent: $("intent").value,
    controls,
    context: { surface: "character-voice-studio", operator_directed: true }
  });
  MonadVoice.setProfile({ speaker: character.id, ...character.voice, ...performance.voice });
  $("inspection").textContent = `${character.name} · ${performance.label}\n${axes.map((axis) => `${axis}: ${Math.round(performance.axes[axis] * 100)} → ${Math.round(performance.target[axis] * 100)}`).join(" · ")}\n${performance.reasons.join(" / ")}`;
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
