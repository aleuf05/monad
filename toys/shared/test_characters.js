const assert = require("assert");
require("./characters.js");
assert(MonadCharacters.list().length >= 4);
assert.equal(MonadCharacters.get("captain.monad").role, "command presence");
assert.equal(MonadCharacters.get("captain.monad").provenance.kind, "synthetic-character");
assert.throws(() => MonadCharacters.register({ name: "Missing id" }), /requires id and name/);
const voices = [
  { voice_id: "daniel", label: "Daniel", lang: "en-GB" },
  { voice_id: "samantha", label: "Samantha", lang: "en-US" },
  { voice_id: "george", label: "George", lang: "en-GB" },
  { voice_id: "karen", label: "Karen", lang: "en-AU" }
];
const assigned = MonadCharacters.assignVoices(voices);
assert.equal(assigned["captain.monad"].voice_id, "daniel");
assert.equal(assigned["captain.alpha"].voice_id, "samantha");
assert.equal(new Set(Object.values(assigned).map((voice) => voice.voice_id)).size, 4, "cast receives distinct voices when available");
console.log("character model tests passed");
