(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const ui = {
    seed: $("seedText"), start: $("startBtn"), step: $("stepBtn"), reset: $("resetBtn"),
    rLow: $("rLow"), rHigh: $("rHigh"), cLow: $("cLow"), cHigh: $("cHigh"), decay: $("decay"),
    rLowOut: $("rLowOut"), rHighOut: $("rHighOut"), cLowOut: $("cLowOut"), cHighOut: $("cHighOut"), decayOut: $("decayOut"),
    recurrence: $("recurrenceValue"), coherence: $("coherenceValue"), perturb: $("perturbValue"),
    recurrenceBar: $("recurrenceBar"), coherenceBar: $("coherenceBar"), perturbBar: $("perturbBar"),
    rLowMark: $("rLowMark"), rHighMark: $("rHighMark"), cLowMark: $("cLowMark"), cHighMark: $("cHighMark"),
    statePill: $("statePill"), status: $("runStatus"), dot: $("liveDot"), wake: $("wake"),
    events: $("eventList"), count: $("stepCount"), canvas: $("phasePlot")
  };

  const fragments = {
    water: ["the water remembers the signal", "a wake folds through the dark", "the current keeps an earlier shape", "below the surface, distance becomes pressure"],
    signal: ["the signal returns wearing another frequency", "static opens into a narrow room", "the receiver mistakes memory for weather", "a carrier tone leans toward the horizon"],
    vessel: ["the vessel holds its line", "the hull translates pressure into direction", "each instrument names a different sea", "the bridge listens for the missing interval"],
    memory: ["memory circles the same unlit marker", "an old phrase leaves by another door", "the remembered thing changes its depth", "what repeats is not always what returns"],
    threshold: ["the boundary moves when it is watched", "coherence survives as a slender thread", "the next association arrives sideways", "a small correction decays into choice"],
    night: ["night gathers around the unclosed sentence", "the dark is structured by distant lamps", "silence acquires a navigable edge", "morning remains possible but unnamed"]
  };
  const connectors = ["and", "while", "because", "until", "as if", "then"];
  const keys = Object.keys(fragments);
  let state;

  function hash(text) {
    let h = 2166136261;
    for (let i = 0; i < text.length; i++) { h ^= text.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }

  function random() {
    state.rng += 0x6D2B79F5;
    let t = state.rng;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  }

  function config() {
    return {
      rLow: +ui.rLow.value / 100, rHigh: +ui.rHigh.value / 100,
      cLow: +ui.cLow.value / 100, cHigh: +ui.cHigh.value / 100,
      halfLife: +ui.decay.value
    };
  }

  function normalizeBands(changed) {
    if (changed === ui.rLow && +ui.rLow.value >= +ui.rHigh.value) ui.rHigh.value = Math.min(95, +ui.rLow.value + 5);
    if (changed === ui.rHigh && +ui.rHigh.value <= +ui.rLow.value) ui.rLow.value = Math.max(20, +ui.rHigh.value - 5);
    if (changed === ui.cLow && +ui.cLow.value >= +ui.cHigh.value) ui.cHigh.value = Math.min(80, +ui.cLow.value + 5);
    if (changed === ui.cHigh && +ui.cHigh.value <= +ui.cLow.value) ui.cLow.value = Math.max(10, +ui.cHigh.value - 5);
    const c = config();
    ui.rLowOut.value = c.rLow.toFixed(2); ui.rHighOut.value = c.rHigh.toFixed(2);
    ui.cLowOut.value = c.cLow.toFixed(2); ui.cHighOut.value = c.cHigh.toFixed(2);
    ui.decayOut.value = `${c.halfLife} steps`;
    ui.rLowMark.style.left = `${c.rLow * 100}%`; ui.rHighMark.style.left = `${c.rHigh * 100}%`;
    ui.cLowMark.style.left = `${c.cLow * 100}%`; ui.cHighMark.style.left = `${c.cHigh * 100}%`;
    draw();
  }

  function initialState() {
    const seed = ui.seed.value.trim() || "The signal leaves a wake";
    return {
      rng: hash(seed), step: 0, recurrence: .36, coherence: .78, perturb: 0,
      mode: "metastable", correctionAge: 0, running: false, timer: null,
      focus: Math.floor(hash(seed) % keys.length), repeats: 0,
      points: [{ r: .36, c: .78, mode: "metastable" }], sentences: []
    };
  }

  function log(message, kind = "neutral") {
    const row = document.createElement("div");
    row.className = `event ${kind}`;
    row.innerHTML = `<time>${String(state.step).padStart(3, "0")}</time><p></p>`;
    row.querySelector("p").textContent = message;
    ui.events.prepend(row);
  }

  function setMode(next, message, kind) {
    if (state.mode !== next) {
      state.mode = next;
      state.correctionAge = 0;
      if (next !== "metastable") state.perturb = Math.max(state.perturb, .86);
      log(message, kind);
    }
  }

  function advanceController() {
    const c = config();
    const drift = (random() - .5) * .09;
    const fixationPull = .025 + Math.max(0, state.repeats - 1) * .022;

    state.recurrence += fixationPull + drift - state.perturb * .16;
    state.coherence += (random() - .5) * .09 - state.perturb * (state.mode === "entrapment" ? .015 : -.11);

    if (state.mode === "metastable") {
      if (state.recurrence > c.rHigh) setMode("entrapment", "Upper band crossed. Orthogonal shift engaged.", "boundary");
      else if (state.coherence < c.cLow) setMode("rescue", "Lower coherence band crossed. Constraint relaxation damped; topic anchor strengthened.", "boundary");
    } else if (state.mode === "entrapment" && state.recurrence < c.rLow) {
      setMode("metastable", "Recurrence fell below exit threshold. Correction now decaying.", "stable");
    } else if (state.mode === "rescue" && state.coherence > c.cHigh) {
      setMode("metastable", "Coherence recovered above exit threshold. Correction now decaying.", "stable");
    }

    if (state.perturb > 0) {
      state.correctionAge += 1;
      state.perturb *= Math.pow(.5, 1 / c.halfLife);
      if (state.perturb < .025) state.perturb = 0;
    }

    state.recurrence = Math.max(.04, Math.min(.97, state.recurrence));
    state.coherence = Math.max(.06, Math.min(.97, state.coherence));
  }

  function generateSentence() {
    const previousFocus = state.focus;
    if (state.mode === "entrapment" && state.perturb > .25) {
      const jump = 2 + Math.floor(random() * (keys.length - 2));
      state.focus = (state.focus + jump) % keys.length;
      state.repeats = 0;
      log(`Associative bearing rotated: ${keys[previousFocus]} → ${keys[state.focus]}.`, "correction");
    } else if (state.mode === "rescue" && state.perturb > .25) {
      state.focus = Math.abs(hash(ui.seed.value)) % keys.length;
      state.repeats = 0;
      log(`Long-horizon anchor restored: ${keys[state.focus]}.`, "correction");
    } else if (random() > state.recurrence) {
      state.focus = (state.focus + (random() > .5 ? 1 : keys.length - 1)) % keys.length;
      state.repeats = 0;
    } else {
      state.repeats++;
    }

    const bank = fragments[keys[state.focus]];
    const first = bank[Math.floor(random() * bank.length)];
    let sentence = first;
    if (state.coherence > .38 || random() > .5) {
      const near = state.coherence > .55 ? state.focus : Math.floor(random() * keys.length);
      const secondBank = fragments[keys[near]];
      sentence += ` ${connectors[Math.floor(random() * connectors.length)]} ${secondBank[Math.floor(random() * secondBank.length)]}`;
    }
    return sentence.charAt(0).toUpperCase() + sentence.slice(1) + ".";
  }

  function step() {
    state.step++;
    advanceController();
    const sentence = generateSentence();
    state.sentences.push(sentence);
    state.points.push({ r: state.recurrence, c: state.coherence, mode: state.mode });
    if (state.points.length > 70) state.points.shift();
    render(sentence);
  }

  function render(sentence) {
    const percent = (v) => `${Math.round(v * 100)}%`;
    ui.recurrence.textContent = state.recurrence.toFixed(2);
    ui.coherence.textContent = state.coherence.toFixed(2);
    ui.perturb.textContent = state.perturb.toFixed(2);
    ui.recurrenceBar.style.width = percent(state.recurrence);
    ui.coherenceBar.style.width = percent(state.coherence);
    ui.perturbBar.style.width = percent(state.perturb);
    ui.perturbBar.style.background = state.perturb > .1 ? "var(--amber)" : "var(--sea)";
    ui.count.textContent = `STEP ${String(state.step).padStart(3, "0")}`;

    const labels = { metastable: "METASTABLE BAND", entrapment: "SHIFTING BASIN", rescue: "COHERENCE RESCUE" };
    ui.statePill.textContent = labels[state.mode];
    ui.statePill.style.color = state.mode === "metastable" ? "var(--sea)" : "var(--amber)";
    ui.statePill.style.borderColor = state.mode === "metastable" ? "var(--sea)" : "var(--amber)";

    if (sentence) {
      ui.wake.querySelector(".placeholder")?.remove();
      ui.wake.querySelector(".latest")?.classList.remove("latest");
      const p = document.createElement("p");
      p.className = "latest";
      p.innerHTML = `<span class="step-tag">${String(state.step).padStart(3, "0")}</span>`;
      p.append(document.createTextNode(sentence));
      ui.wake.append(p);
      while (ui.wake.children.length > 18) ui.wake.firstElementChild.remove();
      ui.wake.scrollTop = ui.wake.scrollHeight;
    }
    draw();
  }

  function draw() {
    if (!state) return;
    const canvas = ui.canvas;
    const rect = canvas.getBoundingClientRect();
    const scale = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.floor(rect.width * scale));
    canvas.height = Math.max(1, Math.floor(rect.height * scale));
    const ctx = canvas.getContext("2d");
    ctx.scale(scale, scale);
    const w = rect.width, h = rect.height, pad = 24, c = config();
    const x = (v) => pad + v * (w - pad * 2);
    const y = (v) => h - pad - v * (h - pad * 2);

    ctx.strokeStyle = "#222a2f"; ctx.lineWidth = 1;
    for (let i = 1; i < 5; i++) {
      ctx.beginPath(); ctx.moveTo(pad, y(i / 5)); ctx.lineTo(w - pad, y(i / 5)); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(x(i / 5), pad); ctx.lineTo(x(i / 5), h - pad); ctx.stroke();
    }
    ctx.fillStyle = "#78d6c512";
    ctx.fillRect(x(c.rLow), y(c.cHigh), x(c.rHigh) - x(c.rLow), y(c.cLow) - y(c.cHigh));
    ctx.strokeStyle = "#f4b35e55"; ctx.setLineDash([4, 6]);
    [c.rLow, c.rHigh].forEach(v => { ctx.beginPath(); ctx.moveTo(x(v), pad); ctx.lineTo(x(v), h-pad); ctx.stroke(); });
    [c.cLow, c.cHigh].forEach(v => { ctx.beginPath(); ctx.moveTo(pad, y(v)); ctx.lineTo(w-pad, y(v)); ctx.stroke(); });
    ctx.setLineDash([]);

    if (state.points.length > 1) {
      ctx.beginPath();
      state.points.forEach((p, i) => i ? ctx.lineTo(x(p.r), y(p.c)) : ctx.moveTo(x(p.r), y(p.c)));
      ctx.strokeStyle = "#78d6c5aa"; ctx.lineWidth = 1.5; ctx.stroke();
    }
    state.points.forEach((p, i) => {
      const recent = i / Math.max(1, state.points.length - 1);
      ctx.beginPath(); ctx.arc(x(p.r), y(p.c), i === state.points.length - 1 ? 5 : 2, 0, Math.PI * 2);
      ctx.fillStyle = p.mode === "metastable" ? `rgba(120,214,197,${.15 + recent * .75})` : `rgba(244,179,94,${.2 + recent * .75})`;
      ctx.fill();
    });
  }

  function toggle() {
    state.running = !state.running;
    ui.start.textContent = state.running ? "Pause run" : (state.step ? "Resume run" : "Start run");
    ui.status.textContent = state.running ? "RUNNING / OBSERVING" : "PAUSED / HOLDING";
    ui.dot.classList.toggle("running", state.running);
    if (state.running) {
      step();
      state.timer = setInterval(step, 1150);
    } else {
      clearInterval(state.timer);
      state.timer = null;
    }
  }

  function reset() {
    if (state?.timer) clearInterval(state.timer);
    state = initialState();
    ui.start.textContent = "Start run";
    ui.status.textContent = "IDLE / READY";
    ui.dot.classList.remove("running");
    ui.wake.innerHTML = '<p class="placeholder">The first phrase is waiting below the surface.</p>';
    ui.events.innerHTML = '<div class="event neutral"><time>000</time><p>Instrument initialized.</p></div>';
    render();
  }

  ui.start.addEventListener("click", toggle);
  ui.step.addEventListener("click", () => { if (!state.running) step(); });
  ui.reset.addEventListener("click", reset);
  [ui.rLow, ui.rHigh, ui.cLow, ui.cHigh, ui.decay].forEach(el => el.addEventListener("input", () => normalizeBands(el)));
  window.addEventListener("resize", draw);
  normalizeBands();
  reset();
})();
