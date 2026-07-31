// The Living Basin -- static replay viewer.
//
// Nothing here invents state or explanations: every layer value comes from
// a precomputed snapshot written by run_demo.py, and every diagnostic-card
// line comes from a real Event record in events.jsonl, walked via
// caused_by links exactly as engine/lineage.py does server-side. This file
// re-implements that same template-based (non-LLM) lineage formatting in
// JS so the viewer can work as static files with no server.

const CELL_PX = 10; // 64 * 10 = 640, matches the canvas element size

const state = {
  worldInit: null,
  snapshots: [],
  featuresById: {},
  cellToFeatureIds: new Map(), // "r,c" -> [feature_id, ...] in creation order
  eventsById: new Map(),
  snapshotIndex: 0,
  playing: false,
  playTimer: null,
  activeLayers: new Set(["vegetation_biomass", "surface_water", "trail_intensity", "erosion_depth", "provenance"]),
  lockedCell: null,
};

const els = {};

function $(id) { return document.getElementById(id); }

async function loadData() {
  const [worldInit, snapshots, featuresRaw, eventsText] = await Promise.all([
    fetch("../data/world_init.json").then(r => r.json()),
    fetch("../data/snapshots.json").then(r => r.json()),
    fetch("../data/features.json").then(r => r.json()),
    fetch("../data/events.jsonl").then(r => r.text()),
  ]);

  state.worldInit = worldInit;
  state.snapshots = snapshots;
  state.featuresById = featuresRaw;

  for (const line of eventsText.split("\n")) {
    if (!line.trim()) continue;
    const evt = JSON.parse(line);
    state.eventsById.set(evt.event_id, evt);
  }

  for (const [fid, feat] of Object.entries(featuresRaw)) {
    for (const [r, c] of feat.cells) {
      const key = `${r},${c}`;
      if (!state.cellToFeatureIds.has(key)) state.cellToFeatureIds.set(key, []);
      state.cellToFeatureIds.get(key).push(fid);
    }
  }
}

// -- deterministic lineage templates (mirrors engine/lineage.py) -----------

const NODE_LABELS = {
  rain_started: "Weather Node",
  saturation_exceeded: "Hydrology Node",
  root_loss: "Flora Node",
  cohesion_degraded: "Soil Node",
  trail_formed: "Herbivore Node",
  grazed_patch_formed: "Herbivore Node",
  pool_formed: "Hydrology Node",
  gully_formed: "Erosion Node",
  override_applied: "Authored Override",
};

function lineText(evt) {
  const label = NODE_LABELS[evt.event_type] || "Node";
  const i = evt.inputs || {};
  let text;
  switch (evt.event_type) {
    case "rain_started":
      text = `Rainfall began at ${i.rainfall_mm_per_hour}mm/hr for ${i.duration_ticks} ticks`;
      break;
    case "saturation_exceeded":
      text = `Local saturation exceeded ${Math.round((i.soil_saturation || 0) * 100)}%`;
      break;
    case "root_loss":
      text = `Root density fell to ${i.root_density}`;
      break;
    case "cohesion_degraded":
      text = `Organic cohesion degraded to ${i.soil_cohesion}`;
      break;
    case "trail_formed":
      text = `Trail intensity reached ${i.trail_intensity} from repeated passage`;
      break;
    case "grazed_patch_formed":
      text = `Grazing pressure reached ${i.grazing_pressure}`;
      break;
    case "pool_formed":
      text = `Standing water reached ${i.surface_water}mm and persisted`;
      break;
    case "gully_formed":
      text = `Erosion depth reached ${i.erosion_depth} (runoff ${i.runoff}, cohesion ${i.soil_cohesion}, slope ${i.local_slope})`;
      break;
    case "override_applied":
      text = `Field '${i.field}' set to ${evt.result && evt.result.after} by ${i.actor}: ${i.reason}`;
      break;
    default:
      text = evt.event_type;
  }
  return `${label}: ${text}`;
}

function buildLineage(eventId, seen = new Set()) {
  const evt = state.eventsById.get(eventId);
  if (!evt || seen.has(eventId)) return [];
  seen.add(eventId);
  let out = [];
  for (const parentId of evt.caused_by || []) {
    out = out.concat(buildLineage(parentId, seen));
  }
  out.push(evt);
  return out;
}

function diagnosticCard(feature) {
  const genesisId = feature.causal_event_ids[0];
  const genesisEvt = state.eventsById.get(genesisId);
  const chain = buildLineage(genesisId);
  const hasOverride =
    feature.authored_override ||
    feature.causal_event_ids.some(eid => {
      const e = state.eventsById.get(eid);
      return e && e.authored_override;
    });
  return {
    feature_type: feature.feature_type,
    cells: feature.cells,
    genesis_tick: feature.genesis_tick,
    status: feature.current_status,
    lineage: chain.map((e, idx) => `${idx + 1}. ${lineText(e)}`),
    overrides: hasOverride ? "Present -- see event log for actor/reason" : "None",
    genesis_inputs: genesisEvt ? genesisEvt.inputs : {},
  };
}

// -- rendering --------------------------------------------------------------

function currentSnapshot() {
  return state.snapshots[state.snapshotIndex];
}

function colorFor(layer, value, elevNorm) {
  switch (layer) {
    case "vegetation_biomass":
      return `rgba(94, 158, 94, ${Math.min(0.75, value * 0.8)})`;
    case "surface_water":
      return `rgba(70, 140, 200, ${Math.min(0.9, value / 60)})`;
    case "trail_intensity":
      return `rgba(201, 154, 91, ${Math.min(0.85, value)})`;
    case "erosion_depth":
      return `rgba(150, 60, 40, ${Math.min(0.9, value / 2)})`;
    default:
      return null;
  }
}

function draw() {
  const canvas = $("terrain");
  const ctx = canvas.getContext("2d");
  const snap = currentSnapshot();
  if (!snap) return;
  const n = state.worldInit.grid_size;
  const layers = snap.layers;
  const elev = layers.elevation;

  let elMin = Infinity, elMax = -Infinity;
  for (const row of elev) for (const v of row) { if (v < elMin) elMin = v; if (v > elMax) elMax = v; }
  const elRange = Math.max(1e-6, elMax - elMin);

  for (let r = 0; r < n; r++) {
    for (let c = 0; c < n; c++) {
      const norm = (elev[r][c] - elMin) / elRange; // 0 = low/loam, 1 = high/ridge
      const shade = 30 + Math.round(norm * 55); // dark loam hollows -> pale slate ridges
      ctx.fillStyle = `rgb(${shade + 8}, ${shade + 6}, ${shade})`;
      ctx.fillRect(c * CELL_PX, r * CELL_PX, CELL_PX, CELL_PX);
    }
  }

  for (const layer of ["vegetation_biomass", "surface_water", "trail_intensity", "erosion_depth"]) {
    if (!state.activeLayers.has(layer)) continue;
    const grid = layers[layer];
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
    for (const [key, fids] of state.cellToFeatureIds.entries()) {
      const [r, c] = key.split(",").map(Number);
      const visible = fids.some(fid => state.featuresById[fid].genesis_tick <= snap.tick);
      if (!visible) continue;
      ctx.strokeStyle = "rgba(240, 225, 180, 0.85)";
      ctx.lineWidth = 1;
      ctx.strokeRect(c * CELL_PX + 1, r * CELL_PX + 1, CELL_PX - 2, CELL_PX - 2);
    }
  }

  if (state.lockedCell) {
    const [lr, lc] = state.lockedCell;
    ctx.strokeStyle = "#f6c76d";
    ctx.lineWidth = 2;
    ctx.strokeRect(lc * CELL_PX, lr * CELL_PX, CELL_PX, CELL_PX);
  }

  $("tickVal").textContent = snap.tick;
  $("tickMax").textContent = state.worldInit.total_ticks;
  $("scrub").value = state.snapshotIndex;
}

// -- diagnostic card ----------------------------------------------------

function showCardForCell(r, c) {
  const key = `${r},${c}`;
  const fids = state.cellToFeatureIds.get(key) || [];
  const snap = currentSnapshot();
  const visibleFids = fids.filter(fid => state.featuresById[fid].genesis_tick <= snap.tick);

  if (visibleFids.length === 0) {
    $("cardEmpty").hidden = false;
    $("cardEmpty").textContent =
      fids.length > 0
        ? `Cell (${r}, ${c}) will register a feature later in the run (not yet, at tick ${snap.tick}).`
        : `Cell (${r}, ${c}): no registered feature here. No causal claim to show.`;
    $("card").hidden = true;
    return;
  }

  const fid = visibleFids[visibleFids.length - 1]; // most recently formed
  const feature = state.featuresById[fid];
  const card = diagnosticCard(feature);

  $("cardEmpty").hidden = true;
  $("card").hidden = false;
  $("cardType").textContent = `${card.feature_type} (${fid})`;
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
  const n = state.worldInit.grid_size;
  if (r < 0 || c < 0 || r >= n || c >= n) return null;
  return [r, c];
}

// -- playback ------------------------------------------------------------

function goToIndex(idx) {
  state.snapshotIndex = Math.max(0, Math.min(state.snapshots.length - 1, idx));
  draw();
  if (state.lockedCell) showCardForCell(state.lockedCell[0], state.lockedCell[1]);
}

function stepOnce() {
  if (state.snapshotIndex >= state.snapshots.length - 1) {
    pause();
    return;
  }
  goToIndex(state.snapshotIndex + 1);
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

// -- wiring ----------------------------------------------------------------

function wireControls() {
  $("btnPlay").addEventListener("click", () => (state.playing ? pause() : play()));
  $("btnStep").addEventListener("click", () => { pause(); stepOnce(); });
  $("btnReset").addEventListener("click", () => { pause(); goToIndex(0); });
  $("speed").addEventListener("change", () => { if (state.playing) { pause(); play(); } });
  $("scrub").addEventListener("input", e => { pause(); goToIndex(Number(e.target.value)); });

  document.querySelectorAll("input[data-layer]").forEach(box => {
    box.addEventListener("change", () => {
      const layer = box.dataset.layer;
      if (box.checked) state.activeLayers.add(layer);
      else state.activeLayers.delete(layer);
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
    state.lockedCell =
      state.lockedCell && state.lockedCell[0] === cell[0] && state.lockedCell[1] === cell[1]
        ? null
        : cell;
    if (state.lockedCell) showCardForCell(cell[0], cell[1]);
    draw();
  });
}

async function main() {
  try {
    await loadData();
  } catch (err) {
    $("statusMsg").textContent = "Failed to load run data -- run run_demo.py first, and serve this directory over HTTP (not file://).";
    $("statusMsg").classList.add("error");
    return;
  }
  $("statusMsg").textContent = `Loaded ${state.snapshots.length} snapshots, ${state.eventsById.size} events, ${Object.keys(state.featuresById).length} features.`;
  $("seedVal").textContent = state.worldInit.seed;
  $("scrub").max = state.snapshots.length - 1;
  wireControls();
  goToIndex(0);
}

main();
