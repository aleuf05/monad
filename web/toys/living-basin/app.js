// The Living Basin -- live viewer driver. The simulation itself
// (engine.js) actually ticks in this browser tab; nothing here is a
// replay of precomputed data. Diagnostic-card text is built by walking
// the live EventLog's real caused_by graph through the same fixed
// per-event-type templates the Python engine uses (see engine.js's
// lineText) -- no LLM, no recomputation from current state.

const CELL_PX = 10; // 64 * 10 = 640, matches the canvas element size

const DEMO_SEED = 42;
const DEMO_RAIN = new RainSchedule([new RainEvent(100, 20, 48)]);
const DEMO_HERBIVORE_BAND = [12, 50, 12, 50];

const state = {
  sim: null,
  elevRange: [0, 1],
  playing: false,
  playTimer: null,
  activeLayers: new Set(["vegetation_biomass", "surface_water", "trail_intensity", "erosion_depth", "provenance"]),
  lockedCell: null,
};

function $(id) { return document.getElementById(id); }

function newSimulation() {
  const sim = new Simulation(DEMO_SEED, DEMO_RAIN, DEMO_HERBIVORE_BAND);
  let elMin = Infinity, elMax = -Infinity;
  for (const row of sim.world.fields.elevation) for (const v of row) { if (v < elMin) elMin = v; if (v > elMax) elMax = v; }
  state.sim = sim;
  state.elevRange = [elMin, Math.max(elMin + 1e-6, elMax)];
  state.lockedCell = null;
  $("seedVal").textContent = sim.seed;
}

// -- lineage text (mirrors engine/lineage.py's fixed templates) -----------

const NODE_LABELS = {
  rain_started: "Weather Node", saturation_exceeded: "Hydrology Node",
  root_loss: "Flora Node", cohesion_degraded: "Soil Node",
  trail_formed: "Herbivore Node", grazed_patch_formed: "Herbivore Node",
  pool_formed: "Hydrology Node", gully_formed: "Erosion Node",
  override_applied: "Authored Override",
};

function lineText(evt) {
  const label = NODE_LABELS[evt.event_type] || "Node";
  const i = evt.inputs || {};
  let text;
  switch (evt.event_type) {
    case "rain_started": text = `Rainfall began at ${i.rainfall_mm_per_hour}mm/hr for ${i.duration_ticks} ticks`; break;
    case "saturation_exceeded": text = `Local saturation exceeded ${Math.round((i.soil_saturation || 0) * 100)}%`; break;
    case "root_loss": text = `Root density fell to ${i.root_density}`; break;
    case "cohesion_degraded": text = `Organic cohesion degraded to ${i.soil_cohesion}`; break;
    case "trail_formed": text = `Trail intensity reached ${i.trail_intensity} from repeated passage`; break;
    case "grazed_patch_formed": text = `Grazing pressure reached ${i.grazing_pressure}`; break;
    case "pool_formed": text = `Standing water reached ${i.surface_water}mm and persisted`; break;
    case "gully_formed": text = `Erosion depth reached ${i.erosion_depth} (runoff ${i.runoff}, cohesion ${i.soil_cohesion}, slope ${i.local_slope})`; break;
    case "override_applied": text = `Field '${i.field}' set to ${evt.result && evt.result.after} by ${i.actor}: ${i.reason}`; break;
    default: text = evt.event_type;
  }
  return `${label}: ${text}`;
}

function diagnosticCard(feature) {
  const eventLog = state.sim.eventLog;
  const genesisId = feature.causal_event_ids[0];
  const genesisEvt = eventLog.get(genesisId);
  const chain = eventLog.lineage(genesisId);
  const hasOverride = feature.authored_override || feature.causal_event_ids.some(eid => {
    const e = eventLog.get(eid);
    return e && e.authored_override;
  });
  return {
    feature_type: feature.feature_type,
    cells: feature.cells,
    genesis_tick: feature.genesis_tick,
    status: feature.current_status,
    lineage: chain.map((e, idx) => `${idx + 1}. ${lineText(e)}`),
    overrides: hasOverride ? "Present -- see event log for actor/reason" : "None",
  };
}

// -- rendering --------------------------------------------------------------

function colorFor(layer, value) {
  switch (layer) {
    case "vegetation_biomass": return `rgba(94, 158, 94, ${Math.min(0.75, value * 0.8)})`;
    case "surface_water": return `rgba(70, 140, 200, ${Math.min(0.9, value / 60)})`;
    case "trail_intensity": return `rgba(201, 154, 91, ${Math.min(0.85, value)})`;
    case "erosion_depth": return `rgba(150, 60, 40, ${Math.min(0.9, value / 2)})`;
    default: return null;
  }
}

function draw() {
  const canvas = $("terrain");
  const ctx = canvas.getContext("2d");
  const sim = state.sim;
  const n = sim.world.n;
  const fields = sim.world.fields;
  const [elMin, elMax] = state.elevRange;
  const elRange = elMax - elMin;

  for (let r = 0; r < n; r++) {
    for (let c = 0; c < n; c++) {
      const norm = (fields.elevation[r][c] - elMin) / elRange;
      const shade = 30 + Math.round(norm * 55);
      ctx.fillStyle = `rgb(${shade + 8}, ${shade + 6}, ${shade})`;
      ctx.fillRect(c * CELL_PX, r * CELL_PX, CELL_PX, CELL_PX);
    }
  }

  for (const layer of ["vegetation_biomass", "surface_water", "trail_intensity", "erosion_depth"]) {
    if (!state.activeLayers.has(layer)) continue;
    const grid = fields[layer];
    for (let r = 0; r < n; r++) {
      for (let c = 0; c < n; c++) {
        const v = grid[r][c];
        if (v <= 0.01) continue;
        const color = colorFor(layer, v);
        if (!color) continue;
        ctx.fillStyle = color;
        ctx.fillRect(c * CELL_PX, r * CELL_PX, CELL_PX, CELL_PX);
      }
    }
  }

  if (state.activeLayers.has("provenance")) {
    ctx.strokeStyle = "rgba(240, 225, 180, 0.85)";
    ctx.lineWidth = 1;
    for (const feat of sim.features.all()) {
      for (const [r, c] of feat.cells) {
        ctx.strokeRect(c * CELL_PX + 1, r * CELL_PX + 1, CELL_PX - 2, CELL_PX - 2);
      }
    }
  }

  if (state.lockedCell) {
    const [lr, lc] = state.lockedCell;
    ctx.strokeStyle = "#f6c76d";
    ctx.lineWidth = 2;
    ctx.strokeRect(lc * CELL_PX, lr * CELL_PX, CELL_PX, CELL_PX);
  }

  $("tickVal").textContent = sim.tickCount;
}

// -- diagnostic card ----------------------------------------------------

function showCardForCell(r, c) {
  const feature = state.sim.features.featureAt([r, c]);

  if (!feature) {
    $("cardEmpty").hidden = false;
    $("cardEmpty").textContent = `Cell (${r}, ${c}): no registered feature here. No causal claim to show.`;
    $("card").hidden = true;
    return;
  }

  const card = diagnosticCard(feature);
  $("cardEmpty").hidden = true;
  $("card").hidden = false;
  $("cardType").textContent = `${card.feature_type} (${feature.feature_id})`;
  $("cardCell").textContent = card.cells.map(cell => `[${cell[0]}, ${cell[1]}]`).join(", ");
  $("cardTick").textContent = card.genesis_tick;
  $("cardStatus").textContent = card.status;
  const list = $("cardLineage");
  list.innerHTML = "";
  for (const line of card.lineage) {
    const li = document.createElement("li");
    li.textContent = line.replace(/^\d+\.\s*/, "");
    list.appendChild(li);
  }
  const overridesEl = $("cardOverrides");
  overridesEl.textContent = card.overrides;
  overridesEl.className = card.overrides === "None" ? "none" : "present";
}

function cellFromEvent(evt) {
  const canvas = $("terrain");
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  const x = (evt.clientX - rect.left) * scaleX;
  const y = (evt.clientY - rect.top) * scaleY;
  const c = Math.floor(x / CELL_PX);
  const r = Math.floor(y / CELL_PX);
  const n = state.sim.world.n;
  if (r < 0 || c < 0 || r >= n || c >= n) return null;
  return [r, c];
}

// -- playback (live ticking, not scrubbing) ---------------------------------

function stepOnce() {
  state.sim.tick();
  draw();
  if (state.lockedCell) showCardForCell(state.lockedCell[0], state.lockedCell[1]);
}

function play() {
  if (state.playing) return;
  state.playing = true;
  $("btnPlay").textContent = "⏸ Pause";
  const interval = Number($("speed").value);
  state.playTimer = setInterval(stepOnce, interval);
}

function pause() {
  state.playing = false;
  $("btnPlay").textContent = "▶ Play";
  if (state.playTimer) clearInterval(state.playTimer);
  state.playTimer = null;
}

function reset() {
  pause();
  newSimulation();
  draw();
  $("cardEmpty").hidden = false;
  $("cardEmpty").textContent = "Hover or click a cell to inspect it.";
  $("card").hidden = true;
}

// -- wiring ----------------------------------------------------------------

function wireControls() {
  $("btnPlay").addEventListener("click", () => (state.playing ? pause() : play()));
  $("btnStep").addEventListener("click", () => { pause(); stepOnce(); });
  $("btnReset").addEventListener("click", reset);
  $("speed").addEventListener("change", () => { if (state.playing) { pause(); play(); } });

  document.querySelectorAll("input[data-layer]").forEach(box => {
    box.addEventListener("change", () => {
      const layer = box.dataset.layer;
      if (box.checked) state.activeLayers.add(layer); else state.activeLayers.delete(layer);
      draw();
    });
  });

  const canvas = $("terrain");
  canvas.addEventListener("mousemove", e => {
    if (state.lockedCell) return;
    const cell = cellFromEvent(e);
    if (cell) showCardForCell(cell[0], cell[1]);
  });
  canvas.addEventListener("click", e => {
    const cell = cellFromEvent(e);
    if (!cell) return;
    state.lockedCell = state.lockedCell && state.lockedCell[0] === cell[0] && state.lockedCell[1] === cell[1] ? null : cell;
    if (state.lockedCell) showCardForCell(cell[0], cell[1]);
    draw();
  });
}

function main() {
  newSimulation();
  wireControls();
  draw();
  $("statusMsg").textContent = "Live -- ticking in this browser tab. Rain begins at tick 100.";
}

main();
