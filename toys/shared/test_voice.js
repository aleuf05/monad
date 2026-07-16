const assert = require("assert");
global.SpeechSynthesisUtterance = function (text) { this.text = text; };
global.speechSynthesis = { getVoices: () => [{ name: "Natural English", voiceURI: "natural", lang: "en-US" }], speak(u) { u.onstart?.(); u.onend?.(); }, cancel() {} };
require("./voice.js");
assert.equal(MonadVoice.listProviders()[0].id, "browser-speechsynthesis");
MonadVoice.setProfile({ speaker: "captain.monad", provider_id: "missing", fallback_provider_id: "browser-speechsynthesis", rate: 0.96 });
MonadVoice.speak("captain.monad", "Report").then((result) => {
  assert.equal(result.fallback_used, true);
  assert.equal(result.handle.voice_id, "natural");
  assert.equal(result.attempts[0].status, "missing");
  console.log("voice engine tests passed");
}).catch((error) => { console.error(error); process.exit(1); });
