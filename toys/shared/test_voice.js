const assert = require("assert");
global.SpeechSynthesisUtterance = function (text) { this.text = text; };
let voices = [{ name: "Natural English", voiceURI: "natural", lang: "en-US" }];
global.speechSynthesis = { getVoices: () => voices, speak(u) { u.onstart?.(); u.onend?.(); }, cancel() {} };
require("./voice.js");
assert.equal(MonadVoice.listProviders()[0].id, "browser-speechsynthesis");
MonadVoice.setProfile({ speaker: "captain.monad", provider_id: "missing", fallback_provider_id: "browser-speechsynthesis", rate: 0.96 });
(async () => {
  const result = await MonadVoice.speak("captain.monad", "Report");
  assert.equal(result.fallback_used, true);
  assert.equal(result.handle.voice_id, "natural");
  assert.equal(result.attempts[0].status, "missing");

  voices = [];
  const delayed = MonadVoice.speak("captain.monad", "Delayed voice report");
  setTimeout(() => { voices = [{ name: "Delayed English", voiceURI: "delayed", lang: "en-US" }]; }, 20);
  const delayedResult = await delayed;
  assert.equal(delayedResult.handle.voice_id, "delayed");

  voices = [];
  await assert.rejects(
    MonadVoice.speak("captain.monad", "No voice report"),
    /No TTS voices installed in this browser/
  );
  console.log("voice engine tests passed");
})().catch((error) => { console.error(error); process.exit(1); });
