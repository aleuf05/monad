(function (global) {
  "use strict";

  const characters = new Map();

  function register(definition) {
    if (!definition?.id || !definition?.name) throw new Error("Character requires id and name");
    const character = {
      schema_version: "monad.character.v0.1",
      role: "character",
      traits: {},
      voice: { provider_id: "browser-speechsynthesis" },
      provenance: { kind: "synthetic-character", consent: "not-applicable" },
      ...definition,
      traits: { ...(definition.traits || {}) },
      voice: { provider_id: "browser-speechsynthesis", ...(definition.voice || {}) }
    };
    characters.set(character.id, character);
    return character;
  }

  function get(id) { return characters.get(id) || null; }
  function list() { return [...characters.values()]; }
  function assignVoices(voices = []) {
    const candidates = voices
      .filter((voice) => /^en([_-]|$)/i.test(voice.lang || ""))
      .concat(voices.filter((voice) => !/^en([_-]|$)/i.test(voice.lang || "")))
      .filter((voice, index, all) => all.findIndex((item) => item.voice_id === voice.voice_id) === index);
    const assignments = {};
    const used = new Set();
    list().forEach((character, index) => {
      const preferred = candidates.find((voice) => !used.has(voice.voice_id) && character.voice.preferred_labels?.some((label) => new RegExp(label, "i").test(voice.label)))
        || candidates.find((voice) => !used.has(voice.voice_id))
        || candidates[index % Math.max(1, candidates.length)]
        || null;
      assignments[character.id] = preferred;
      if (preferred) used.add(preferred.voice_id);
    });
    return assignments;
  }

  register({
    id: "captain.monad",
    name: "Captain Monad",
    role: "command presence",
    description: "Measured, restrained authority; warm enough to reassure without losing command weight.",
    traits: { caution: 0.65, initiative: 0.45, humor: 0.2, trust: 0.55 },
    voice: { rate: 0.96, pitch: 1, volume: 1, preferred_labels: ["Daniel", "Alex", "David", "\\bmale\\b"] }
  });
  register({
    id: "captain.alpha",
    name: "Captain Alpha",
    role: "forward reconnaissance",
    description: "Concise, tactical and understated, with alert curiosity.",
    traits: { caution: 0.55, initiative: 0.65, humor: 0.25, trust: 0.5 },
    voice: { preferred_labels: ["Samantha", "Zira", "\\bfemale\\b"] }
  });
  register({
    id: "captain.bravo",
    name: "Captain Bravo",
    role: "flank security",
    description: "Measured, deliberate and low-drama.",
    traits: { caution: 0.6, initiative: 0.45, humor: 0.15, trust: 0.5 },
    voice: { preferred_labels: ["UK English Male", "George", "Arthur"] }
  });
  register({
    id: "captain.charlie",
    name: "Captain Charlie",
    role: "rear guard",
    description: "Dry and procedural, with an occasional wry edge.",
    traits: { caution: 0.65, initiative: 0.4, humor: 0.3, trust: 0.55 },
    voice: { preferred_labels: ["UK English Female", "Karen", "Moira"] }
  });

  global.MonadCharacters = { register, get, list, assignVoices };
})(typeof window === "undefined" ? globalThis : window);
