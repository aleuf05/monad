(function (global) {
  "use strict";

  const providers = new Map();
  const profiles = new Map();
  const listeners = new Set();
  const VOICE_ENUMERATION_TIMEOUT_MS = 1500;

  function emit(event) {
    listeners.forEach((listener) => listener(event));
  }

  function preferredVoice(voices, voiceId, lang = "en") {
    return voices.find((voice) => voice.voice_id === voiceId)
      || voices.find((voice) => voice.lang.toLowerCase().startsWith(lang) && /natural|enhanced|premium/i.test(voice.label))
      || voices.find((voice) => voice.lang.toLowerCase().startsWith(lang))
      || voices[0]
      || null;
  }

  function waitForBrowserVoices(synth) {
    const available = () => synth.getVoices();
    const initial = available();
    if (initial.length) return Promise.resolve(initial);

    return new Promise((resolve) => {
      let settled = false;
      const finish = (voices) => {
        if (settled) return;
        settled = true;
        global.clearInterval(poll);
        global.clearTimeout(timeout);
        synth.removeEventListener?.("voiceschanged", check);
        resolve(voices);
      };
      const check = () => {
        const voices = available();
        if (voices.length) finish(voices);
      };
      const poll = global.setInterval(check, 50);
      const timeout = global.setTimeout(() => finish(available()), VOICE_ENUMERATION_TIMEOUT_MS);
      synth.addEventListener?.("voiceschanged", check);
    });
  }

  const browserProvider = {
    id: "browser-speechsynthesis",
    label: "Browser Speech",
    requiresKey: false,
    capabilities: { streaming: false, ssml: false, offline: true, costClass: "free" },
    isAvailable() {
      return Boolean(global.speechSynthesis && global.SpeechSynthesisUtterance);
    },
    async listVoices() {
      if (!this.isAvailable()) return [];
      const voices = await waitForBrowserVoices(global.speechSynthesis);
      return voices.map((voice) => ({
        voice_id: voice.voiceURI || voice.name,
        label: voice.name,
        lang: voice.lang || "",
        native: voice
      }));
    },
    async speak(text, options = {}) {
      if (!this.isAvailable()) throw new Error("Speech synthesis is unavailable in this browser");
      const voices = await this.listVoices();
      if (!voices.length) throw new Error("No TTS voices installed in this browser");
      const selected = preferredVoice(voices, options.voice_id, options.lang || "en");
      const utterance = new global.SpeechSynthesisUtterance(text);
      utterance.voice = selected?.native || null;
      utterance.rate = options.rate ?? 1;
      utterance.pitch = options.pitch ?? 1;
      utterance.volume = options.volume ?? 1;
      let stopped = false;
      const handle = {
        provider_id: this.id,
        provider_label: this.label,
        voice_id: selected?.voice_id || null,
        voice_label: selected?.label || null,
        stop() { stopped = true; global.speechSynthesis.cancel(); },
        onstart: null, onend: null, onerror: null
      };
      utterance.onstart = () => { if (!stopped) handle.onstart?.(handle); };
      utterance.onend = () => { if (!stopped) handle.onend?.(handle); };
      utterance.onerror = (error) => { if (!stopped) handle.onerror?.(error, handle); };
      global.setTimeout(() => global.speechSynthesis.speak(utterance), 0);
      return handle;
    }
  };

  function registerProvider(provider) {
    for (const field of ["id", "label", "requiresKey", "capabilities", "isAvailable", "listVoices", "speak"]) {
      if (provider[field] == null) throw new Error(`Voice provider missing ${field}`);
    }
    providers.set(provider.id, provider);
  }

  function setProfile(profile) {
    if (!profile?.speaker || !profile?.provider_id) throw new Error("Voice profile requires speaker and provider_id");
    profiles.set(profile.speaker, { schema_version: "monad.voiceprofile.v0.1", rate: 1, pitch: 1, volume: 1, fallback_provider_id: "browser-speechsynthesis", ...profile });
  }

  function getProfile(speaker) {
    return profiles.get(speaker) || { schema_version: "monad.voiceprofile.v0.1", speaker, provider_id: "browser-speechsynthesis", fallback_provider_id: "browser-speechsynthesis", rate: 1, pitch: 1, volume: 1 };
  }

  async function speak(speaker, text, overrides = {}) {
    const profile = { ...getProfile(speaker), ...overrides };
    const chain = [...new Set([profile.provider_id, profile.fallback_provider_id].filter(Boolean))];
    const attempts = [];
    for (const providerId of chain) {
      const provider = providers.get(providerId);
      if (!provider) { attempts.push({ provider_id: providerId, status: "missing" }); continue; }
      if (!provider.isAvailable()) { attempts.push({ provider_id: providerId, status: "unavailable" }); continue; }
      try {
        const handle = await provider.speak(text, profile);
        const result = { handle, profile, attempts, fallback_used: providerId !== profile.provider_id };
        emit({ type: "voice-start-requested", speaker, provider_id: providerId, ...result });
        return result;
      } catch (error) {
        attempts.push({ provider_id: providerId, status: "failed", error: error.message });
      }
    }
    const error = new Error(attempts.map((attempt) => `${attempt.provider_id}: ${attempt.error || attempt.status}`).join("; ") || "No voice provider configured");
    error.attempts = attempts;
    emit({ type: "voice-failed", speaker, attempts });
    throw error;
  }

  registerProvider(browserProvider);
  global.MonadVoice = { registerProvider, setProfile, getProfile, listProviders: () => [...providers.values()], speak, onTelemetry(listener) { listeners.add(listener); return () => listeners.delete(listener); }, preferredVoice };
})(typeof window === "undefined" ? globalThis : window);
