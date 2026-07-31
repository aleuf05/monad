// The Living Basin -- JS port of the Python engine (engine/*.py), so the
// simulation actually ticks live in the browser instead of replaying a
// precomputed run. Kept as a single file and ported function-for-function
// against the Python source, same tick order, same thresholds, same
// causal-event/feature/lineage model. The one real difference is the RNG:
// JS has no stdlib equivalent of Python's Mersenne Twister, so this uses a
// small seeded PRNG (mulberry32) -- determinism holds *within* a JS run
// (same seed -> same result here, every time), it just won't reproduce the
// Python engine's exact numbers. See tools/living-basin/engine/ for the
// tested Python reference implementation this was ported from.

const CONFIG = {
  GRID_SIZE: 64,

  RAINFALL_DT_HOURS: 0.12,
  INFILTRATION_BASE: 0.06,
  INFILTRATION_ROOT_BONUS: 0.10,
  EVAPORATION_RATE: 0.03,
  DEEP_DRAINAGE_RATE: 0.025,
  SURFACE_WATER_LOSS_RATE: 0.07,
  RUNOFF_FLOW_FRACTION: 0.45,
  SATURATION_THRESHOLD: 0.85,
  MOISTURE_CONVERSION: 0.010,

  VEG_GROWTH_RATE: 0.02,
  VEG_MOISTURE_OPTIMAL: 0.5,
  ROOT_APPROACH_RATE: 0.03,
  LOW_ROOT_THRESHOLD: 0.20,

  HERBIVORE_COUNT: 6,
  GRAZE_RATE: 0.12,
  GRAZING_PRESSURE_GAIN: 0.20,
  GRAZING_PRESSURE_DECAY: 0.01,
  GRAZED_PATCH_THRESHOLD: 0.6,
  TRAIL_GAIN_PER_PASS: 0.08,
  TRAIL_DECAY: 0.002,
  TRAIL_MATURE_THRESHOLD: 0.25,

  COHESION_BASE: 0.50,
  COHESION_ROOT_WEIGHT: 0.35,
  COHESION_ORGANIC_WEIGHT: 0.15,
  COHESION_SATURATION_PENALTY: 0.35,
  COHESION_RELAX_RATE: 0.15,
  COHESION_DEGRADED_THRESHOLD: 0.35,

  EROSION_RUNOFF_THRESHOLD: 0.15,
  EROSION_SATURATION_THRESHOLD: 0.80,
  EROSION_COHESION_THRESHOLD: 0.40,
  EROSION_SLOPE_THRESHOLD: 0.02,
  EROSION_RATE: 0.6,
  GULLY_DEPTH_THRESHOLD: 0.35,

  POOL_WATER_THRESHOLD: 3.0,
  POOL_PERSIST_TICKS: 6,

  ORGANIC_GROWTH_RATE: 0.01,
};

const FIELD_NAMES = [
  "elevation", "soil_moisture", "soil_cohesion", "organic_content",
  "root_density", "vegetation_biomass", "surface_water", "erosion_depth",
  "trail_intensity", "grazing_pressure",
];

// -- seeded RNG (mulberry32) -- Python's random.Random API surface used by
// the engine is just uniform(a,b) and randint(a,b) (inclusive); this
// implements exactly that against a small deterministic generator.
class SeededRandom {
  constructor(seed) {
    this.state = seed >>> 0;
  }
  next() {
    this.state |= 0; this.state = (this.state + 0x6D2B79F5) | 0;
    let t = Math.imul(this.state ^ (this.state >>> 15), 1 | this.state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }
  uniform(a, b) { return a + this.next() * (b - a); }
  randint(a, b) { return a + Math.floor(this.next() * (b - a + 1)); }
}

function makeField(n, fill) {
  const grid = new Array(n);
  for (let r = 0; r < n; r++) grid[r] = new Array(n).fill(fill);
  return grid;
}

function generateElevation(seed, n) {
  const cx = n / 2.0, cy = n / 2.0;
  const rng = new SeededRandom(seed);
  const elev = makeField(n, 0.0);
  for (let r = 0; r < n; r++) {
    for (let c = 0; c < n; c++) {
      const dx = (c - cx) / n, dy = (r - cy) / n;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const bowl = dist * dist * 18.0;
      const slope = (c - r) * 0.06;
      const roughness = rng.uniform(-0.15, 0.15);
      elev[r][c] = bowl + slope + roughness;
    }
  }
  return elev;
}

// -- World -------------------------------------------------------------

class World {
  constructor(seed) {
    this.seed = seed;
    const n = CONFIG.GRID_SIZE;
    this.n = n;
    this.fields = {};
    for (const name of FIELD_NAMES) this.fields[name] = makeField(n, 0.0);
    this.fields.elevation = generateElevation(seed, n);
    this.fields.soil_cohesion = makeField(n, CONFIG.COHESION_BASE);
    this.fields.organic_content = makeField(n, 0.15);
    this.fields.vegetation_biomass = makeField(n, 0.35);
    this.fields.root_density = makeField(n, 0.30);
    this.flowDirection = new Array(n);
    for (let r = 0; r < n; r++) this.flowDirection[r] = new Array(n).fill(null);
    this.recomputeFlowDirections();
  }

  inBounds(r, c) { return r >= 0 && r < this.n && c >= 0 && c < this.n; }

  neighbors(r, c, diagonal = true) {
    const offsets = [[-1, 0], [1, 0], [0, -1], [0, 1]];
    if (diagonal) offsets.push([-1, -1], [-1, 1], [1, -1], [1, 1]);
    const out = [];
    for (const [dr, dc] of offsets) {
      const nr = r + dr, nc = c + dc;
      if (this.inBounds(nr, nc)) out.push([nr, nc]);
    }
    return out;
  }

  effectiveElevation(r, c) {
    return this.fields.elevation[r][c] - this.fields.erosion_depth[r][c];
  }

  recomputeFlowDirections() {
    for (let r = 0; r < this.n; r++) {
      for (let c = 0; c < this.n; c++) {
        const here = this.effectiveElevation(r, c);
        let best = null, bestDrop = 0.0;
        for (const [nr, nc] of this.neighbors(r, c, true)) {
          const drop = here - this.effectiveElevation(nr, nc);
          if (drop > bestDrop) { bestDrop = drop; best = [nr, nc]; }
        }
        this.flowDirection[r][c] = best;
      }
    }
  }

  localSlope(r, c) {
    const target = this.flowDirection[r][c];
    if (!target) return 0.0;
    const [nr, nc] = target;
    return Math.max(0.0, this.effectiveElevation(r, c) - this.effectiveElevation(nr, nc));
  }

  inflowSlope(r, c) {
    const here = this.effectiveElevation(r, c);
    let best = 0.0;
    for (const [nr, nc] of this.neighbors(r, c, true)) {
      const drop = this.effectiveElevation(nr, nc) - here;
      if (drop > best) best = drop;
    }
    return best;
  }
}

// -- weather -------------------------------------------------------------

class RainEvent {
  constructor(startTick, durationTicks, rainfallMmPerHour) {
    this.startTick = startTick;
    this.durationTicks = durationTicks;
    this.rainfallMmPerHour = rainfallMmPerHour;
    this.endTick = startTick + durationTicks;
  }
  activeAt(tick) { return tick >= this.startTick && tick < this.endTick; }
}

class RainSchedule {
  // Stateless by design -- safe to reuse across Simulation instances or a
  // reset, exactly like the Python engine (see ARCHITECTURE.md's
  // Determinism section for the bug this avoided there).
  constructor(events) {
    this.events = [...events].sort((a, b) => a.startTick - b.startTick);
  }
  activeRate(tick) {
    for (const evt of this.events) if (evt.activeAt(tick)) return evt.rainfallMmPerHour;
    return 0.0;
  }
  justStarted(tick) {
    for (const evt of this.events) if (evt.startTick === tick) return evt;
    return null;
  }
}

// -- hydrology ------------------------------------------------------------

function applyRainfall(world, rateMmPerHour) {
  if (rateMmPerHour <= 0) return;
  const sw = world.fields.surface_water;
  const deposit = rateMmPerHour * CONFIG.RAINFALL_DT_HOURS;
  for (let r = 0; r < world.n; r++) for (let c = 0; c < world.n; c++) sw[r][c] += deposit;
}

function infiltrateAndEvaporate(world) {
  const sw = world.fields.surface_water, sm = world.fields.soil_moisture, roots = world.fields.root_density;
  for (let r = 0; r < world.n; r++) {
    for (let c = 0; c < world.n; c++) {
      let capacity = CONFIG.INFILTRATION_BASE + CONFIG.INFILTRATION_ROOT_BONUS * roots[r][c];
      capacity *= 1.0 - 0.6 * sm[r][c];
      const infiltrated = Math.min(sw[r][c], sw[r][c] * capacity + 0.02);
      sw[r][c] -= infiltrated;
      sm[r][c] = Math.min(1.0, sm[r][c] + infiltrated * CONFIG.MOISTURE_CONVERSION);
      sm[r][c] = Math.max(0.0, sm[r][c] * (1.0 - CONFIG.EVAPORATION_RATE) - CONFIG.DEEP_DRAINAGE_RATE * sm[r][c]);
      sw[r][c] = Math.max(0.0, sw[r][c] * (1.0 - CONFIG.SURFACE_WATER_LOSS_RATE));
    }
  }
}

function redistributeFlow(world) {
  const sw = world.fields.surface_water, n = world.n;
  const outflow = makeField(n, 0.0), inflow = makeField(n, 0.0);
  for (let r = 0; r < n; r++) {
    for (let c = 0; c < n; c++) {
      const target = world.flowDirection[r][c];
      if (!target || sw[r][c] <= 0) continue;
      const moved = sw[r][c] * CONFIG.RUNOFF_FLOW_FRACTION;
      outflow[r][c] = moved;
      inflow[target[0]][target[1]] += moved;
    }
  }
  for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) sw[r][c] = sw[r][c] - outflow[r][c] + inflow[r][c];
  return [outflow, inflow];
}

function newlySaturatedCells(world, previousSaturation) {
  const sm = world.fields.soil_moisture, out = [];
  for (let r = 0; r < world.n; r++) {
    for (let c = 0; c < world.n; c++) {
      const now = sm[r][c] >= CONFIG.SATURATION_THRESHOLD;
      if (now && !previousSaturation[r][c]) out.push([r, c]);
      previousSaturation[r][c] = now;
    }
  }
  return out;
}

// -- vegetation ---------------------------------------------------------

function growAndBuildOrganics(world) {
  const biomass = world.fields.vegetation_biomass, organic = world.fields.organic_content, sm = world.fields.soil_moisture;
  for (let r = 0; r < world.n; r++) {
    for (let c = 0; c < world.n; c++) {
      const m = sm[r][c];
      const moistureFactor = Math.max(0.0, 1.0 - Math.abs(m - CONFIG.VEG_MOISTURE_OPTIMAL) / CONFIG.VEG_MOISTURE_OPTIMAL);
      const headroom = 1.0 - biomass[r][c];
      biomass[r][c] = Math.min(1.0, biomass[r][c] + CONFIG.VEG_GROWTH_RATE * moistureFactor * headroom);
      if (biomass[r][c] > 0.5) {
        organic[r][c] = Math.min(1.0, organic[r][c] + CONFIG.ORGANIC_GROWTH_RATE * (biomass[r][c] - 0.5));
      }
    }
  }
}

function updateRootDensity(world, previousLowRoot) {
  const roots = world.fields.root_density, biomass = world.fields.vegetation_biomass, out = [];
  for (let r = 0; r < world.n; r++) {
    for (let c = 0; c < world.n; c++) {
      roots[r][c] += (biomass[r][c] - roots[r][c]) * CONFIG.ROOT_APPROACH_RATE;
      roots[r][c] = Math.max(0.0, Math.min(1.0, roots[r][c]));
      const nowLow = roots[r][c] < CONFIG.LOW_ROOT_THRESHOLD;
      if (nowLow && !previousLowRoot[r][c]) out.push([r, c]);
      previousLowRoot[r][c] = nowLow;
    }
  }
  return out;
}

// -- herbivores -----------------------------------------------------------

class Herbivore {
  constructor(id, start) { this.id = id; this.position = start; }
}

function spawnHerbivores(world, rng, startBand) {
  const [r0, r1, c0, c1] = startBand;
  const herds = [];
  for (let i = 0; i < CONFIG.HERBIVORE_COUNT; i++) {
    herds.push(new Herbivore(i, [rng.randint(r0, r1), rng.randint(c0, c1)]));
  }
  return herds;
}

function herbivoreWeight(world, r, c, curElev) {
  const biomass = world.fields.vegetation_biomass[r][c];
  const elev = world.effectiveElevation(r, c);
  const climbPenalty = Math.max(0.0, elev - curElev);
  return Math.max(0.02, 0.4 + 3.0 * biomass - 1.2 * climbPenalty);
}

function herbivoresStep(world, herds, rng) {
  const biomass = world.fields.vegetation_biomass, pressure = world.fields.grazing_pressure;
  const visited = [], grazed = [];
  for (const h of herds) {
    const [r, c] = h.position;
    const curElev = world.effectiveElevation(r, c);
    const options = [[r, c], ...world.neighbors(r, c, true)];
    const weights = options.map(([orr, occ]) => herbivoreWeight(world, orr, occ, curElev));
    const total = weights.reduce((a, b) => a + b, 0);
    const pick = rng.uniform(0, total);
    let acc = 0.0, chosen = options[options.length - 1];
    for (let i = 0; i < options.length; i++) {
      acc += weights[i];
      if (pick <= acc) { chosen = options[i]; break; }
    }
    h.position = chosen;
    visited.push(chosen);
    const [vr, vc] = chosen;
    if (biomass[vr][vc] > 0.01) {
      const grazedAmount = Math.min(biomass[vr][vc], CONFIG.GRAZE_RATE);
      biomass[vr][vc] -= grazedAmount;
      pressure[vr][vc] = Math.min(1.0, pressure[vr][vc] + CONFIG.GRAZING_PRESSURE_GAIN);
      grazed.push(chosen);
    }
  }
  return [visited, grazed];
}

function decayGrazingPressure(world) {
  const pressure = world.fields.grazing_pressure;
  for (let r = 0; r < world.n; r++) for (let c = 0; c < world.n; c++) {
    pressure[r][c] = Math.max(0.0, pressure[r][c] - CONFIG.GRAZING_PRESSURE_DECAY);
  }
}

// -- trails ---------------------------------------------------------------

function accumulateTrails(world, visitedCells) {
  const trail = world.fields.trail_intensity;
  for (let r = 0; r < world.n; r++) for (let c = 0; c < world.n; c++) {
    trail[r][c] = Math.max(0.0, trail[r][c] - CONFIG.TRAIL_DECAY);
  }
  for (const [r, c] of visitedCells) trail[r][c] = Math.min(1.0, trail[r][c] + CONFIG.TRAIL_GAIN_PER_PASS);
}

// -- erosion ---------------------------------------------------------------

function cohesionTarget(world, r, c) {
  const roots = world.fields.root_density[r][c], organic = world.fields.organic_content[r][c], sm = world.fields.soil_moisture[r][c];
  const satExcess = Math.max(0.0, sm - CONFIG.SATURATION_THRESHOLD) / Math.max(1e-6, 1.0 - CONFIG.SATURATION_THRESHOLD);
  const target = CONFIG.COHESION_BASE + CONFIG.COHESION_ROOT_WEIGHT * roots + CONFIG.COHESION_ORGANIC_WEIGHT * organic - CONFIG.COHESION_SATURATION_PENALTY * satExcess;
  return Math.max(0.0, Math.min(1.0, target));
}

function updateCohesion(world, previousLowCohesion) {
  const cohesion = world.fields.soil_cohesion, out = [];
  for (let r = 0; r < world.n; r++) {
    for (let c = 0; c < world.n; c++) {
      const target = cohesionTarget(world, r, c);
      cohesion[r][c] += (target - cohesion[r][c]) * CONFIG.COHESION_RELAX_RATE;
      const nowLow = cohesion[r][c] <= CONFIG.COHESION_DEGRADED_THRESHOLD;
      if (nowLow && !previousLowCohesion[r][c]) out.push([r, c]);
      previousLowCohesion[r][c] = nowLow;
    }
  }
  return out;
}

function applyErosion(world, outflow, inflow, rainfallRate) {
  const depth = world.fields.erosion_depth, cohesion = world.fields.soil_cohesion;
  const sm = world.fields.soil_moisture, roots = world.fields.root_density;
  const accrued = [];
  for (let r = 0; r < world.n; r++) {
    for (let c = 0; c < world.n; c++) {
      const ro = Math.max(outflow[r][c], inflow[r][c]);
      if (ro <= CONFIG.EROSION_RUNOFF_THRESHOLD) continue;
      if (sm[r][c] < CONFIG.EROSION_SATURATION_THRESHOLD) continue;
      if (cohesion[r][c] > CONFIG.EROSION_COHESION_THRESHOLD) continue;
      const slope = Math.max(world.localSlope(r, c), world.inflowSlope(r, c));
      if (slope < CONFIG.EROSION_SLOPE_THRESHOLD) continue;

      const excessRunoff = ro - CONFIG.EROSION_RUNOFF_THRESHOLD;
      const weakness = 1.0 - cohesion[r][c];
      const gain = CONFIG.EROSION_RATE * excessRunoff * weakness * 0.08;
      depth[r][c] += gain;
      cohesion[r][c] = Math.max(0.0, cohesion[r][c] - gain * 0.5);

      accrued.push({
        cell: [r, c],
        rainfall_mm_per_hour: rainfallRate,
        soil_saturation: round4(sm[r][c]),
        soil_cohesion: round4(cohesion[r][c]),
        root_density: round4(roots[r][c]),
        local_slope: round4(slope),
        runoff: round4(ro),
        erosion_depth: round4(depth[r][c]),
        erosion_depth_delta: round4(gain),
      });
    }
  }
  return accrued;
}

function round4(v) { return Math.round(v * 10000) / 10000; }

// -- events / provenance ----------------------------------------------------

class LEvent {
  constructor(eventId, tick, eventType, cell, inputs, causedBy, result, authoredOverride) {
    this.event_id = eventId;
    this.tick = tick;
    this.event_type = eventType;
    this.cell = cell;
    this.inputs = inputs;
    this.caused_by = causedBy || [];
    this.result = result || {};
    this.authored_override = !!authoredOverride;
  }
}

class EventLog {
  constructor() { this._events = []; this._byId = new Map(); this._counter = 0; }

  record(tick, eventType, cell, inputs, causedBy, result, authoredOverride) {
    this._counter += 1;
    const idCell = cell ? `_${String(cell[0]).padStart(2, "0")}${String(cell[1]).padStart(2, "0")}` : "";
    const eventId = `evt_${eventType}_${String(tick).padStart(6, "0")}${idCell}_${this._counter}`;
    const evt = new LEvent(eventId, tick, eventType, cell ? [...cell] : null, inputs, causedBy, result, authoredOverride);
    this._events.push(evt);
    this._byId.set(eventId, evt);
    return evt;
  }

  get(eventId) { return this._byId.get(eventId) || null; }
  all() { return this._events; }
  get size() { return this._events.length; }

  lineage(eventId, seen) {
    seen = seen || new Set();
    const evt = this.get(eventId);
    if (!evt || seen.has(eventId)) return [];
    seen.add(eventId);
    let out = [];
    for (const parentId of evt.caused_by) out = out.concat(this.lineage(parentId, seen));
    out.push(evt);
    return out;
  }

  isAcyclic() {
    for (const evt of this._events) {
      const visited = new Set();
      const stack = [...evt.caused_by];
      while (stack.length) {
        const pid = stack.pop();
        if (pid === evt.event_id) return false;
        if (visited.has(pid)) continue;
        visited.add(pid);
        const parent = this.get(pid);
        if (parent) stack.push(...parent.caused_by);
      }
    }
    return true;
  }
}

// -- features -------------------------------------------------------------

class Feature {
  constructor(featureId, featureType, cells, genesisTick, genesisEventId) {
    this.feature_id = featureId;
    this.feature_type = featureType;
    this.cells = cells.map(c => [...c]);
    this.genesis_tick = genesisTick;
    this.current_status = "Stable";
    this.causal_event_ids = [genesisEventId];
    this.authored_override = false;
  }
}

class FeatureRegistry {
  constructor() {
    this._features = new Map();
    this._byCell = new Map();       // "r,c" -> [feature_id, ...]
    this._byCellType = new Map();   // "r,c|type" -> feature_id
    this._counters = new Map();
  }

  _newId(featureType) {
    const key = featureType.toLowerCase();
    const n = (this._counters.get(key) || 0) + 1;
    this._counters.set(key, n);
    return `feature_${key}_${String(n).padStart(4, "0")}`;
  }

  featureOfTypeAt(cell, featureType) {
    const fid = this._byCellType.get(`${cell[0]},${cell[1]}|${featureType}`);
    return fid ? this._features.get(fid) : null;
  }

  featuresAt(cell) {
    const ids = this._byCell.get(`${cell[0]},${cell[1]}`) || [];
    return ids.map(id => this._features.get(id));
  }

  get(featureId) { return this._features.get(featureId) || null; }
  all() { return [...this._features.values()]; }

  create(featureType, cells, genesisTick, genesisEventId) {
    const feat = new Feature(this._newId(featureType), featureType, cells, genesisTick, genesisEventId);
    this._features.set(feat.feature_id, feat);
    for (const c of cells) {
      const key = `${c[0]},${c[1]}`;
      if (!this._byCell.has(key)) this._byCell.set(key, []);
      this._byCell.get(key).push(feat.feature_id);
      this._byCellType.set(`${key}|${featureType}`, feat.feature_id);
    }
    return feat;
  }

  appendEvent(featureId, eventId) {
    const feat = this._features.get(featureId);
    if (feat && !feat.causal_event_ids.includes(eventId)) feat.causal_event_ids.push(eventId);
  }

  markOverride(featureId) {
    const feat = this._features.get(featureId);
    if (feat) feat.authored_override = true;
  }
}

// -- overrides -------------------------------------------------------------
// Ported for data-model parity with the Python engine (see README's
// "How authored overrides are detected"); v0's UI doesn't call this yet.

function applyOverride(sim, tick, cell, fieldName, newValue, actor, reason) {
  const [r, c] = cell;
  const before = sim.world.fields[fieldName][r][c];
  sim.world.fields[fieldName][r][c] = newValue;
  const evt = sim.eventLog.record(tick, "override_applied", cell, { field: fieldName, actor, reason }, [], { before, after: newValue }, true);
  const feat = sim.features.featureAt ? sim.features.featureAt(cell) : null;
  if (feat) {
    sim.features.appendEvent(feat.feature_id, evt.event_id);
    sim.features.markOverride(feat.feature_id);
  }
  return evt;
}

// -- simulation orchestrator ------------------------------------------------

class Simulation {
  constructor(seed, rainSchedule, herbivoreStartBand) {
    this.seed = seed;
    this.world = new World(seed);
    this.eventLog = new EventLog();
    this.features = new FeatureRegistry();
    this.tickCount = 0;
    this.rng = new SeededRandom((seed ^ 0x5EEDF00D) >>> 0);
    this.rainSchedule = rainSchedule || new RainSchedule([]);
    this.herds = spawnHerbivores(this.world, this.rng, herbivoreStartBand || [12, 50, 12, 50]);

    const n = this.world.n;
    this._previousSaturation = makeField(n, false);
    this._previousLowRoot = makeField(n, false);
    this._previousLowCohesion = makeField(n, false);
    this._poolPersist = makeField(n, 0);

    this._lastRainEventId = null;
    this._lastSaturationEvent = new Map();
    this._lastRootLossEvent = new Map();
    this._lastCohesionEvent = new Map();
  }

  tick() {
    const t = this.tickCount, world = this.world;

    const rate = this.rainSchedule.activeRate(t);
    const started = this.rainSchedule.justStarted(t);
    if (started) {
      const evt = this.eventLog.record(t, "rain_started", null, {
        rainfall_mm_per_hour: started.rainfallMmPerHour, duration_ticks: started.durationTicks,
      });
      this._lastRainEventId = evt.event_id;
    }

    applyRainfall(world, rate);
    infiltrateAndEvaporate(world);
    world.recomputeFlowDirections();
    const [outflow, inflow] = redistributeFlow(world);
    const newlySat = newlySaturatedCells(world, this._previousSaturation);

    growAndBuildOrganics(world);
    const newlyLowRoot = updateRootDensity(world, this._previousLowRoot);

    const [visited, grazed] = herbivoresStep(world, this.herds, this.rng);
    decayGrazingPressure(world);

    accumulateTrails(world, visited);

    const newlyLowCohesion = updateCohesion(world, this._previousLowCohesion);
    const erosionInputs = applyErosion(world, outflow, inflow, rate);

    this._recordSaturationEvents(t, newlySat);
    this._recordRootLossEvents(t, newlyLowRoot);
    this._recordCohesionEvents(t, newlyLowCohesion);
    this._detectTrails(t, visited);
    this._detectGrazedPatches(t, grazed);
    this._detectPools(t);
    this._detectGullies(t, erosionInputs);

    this.tickCount += 1;
  }

  run(numTicks) { for (let i = 0; i < numTicks; i++) this.tick(); }

  _recordSaturationEvents(t, cells) {
    const sm = this.world.fields.soil_moisture;
    for (const cell of cells) {
      const evt = this.eventLog.record(t, "saturation_exceeded", cell,
        { soil_saturation: round4(sm[cell[0]][cell[1]]) },
        this._lastRainEventId ? [this._lastRainEventId] : []);
      this._lastSaturationEvent.set(key(cell), evt.event_id);
    }
  }

  _recordRootLossEvents(t, cells) {
    const roots = this.world.fields.root_density;
    for (const cell of cells) {
      const evt = this.eventLog.record(t, "root_loss", cell, { root_density: round4(roots[cell[0]][cell[1]]) });
      this._lastRootLossEvent.set(key(cell), evt.event_id);
    }
  }

  _recordCohesionEvents(t, cells) {
    const coh = this.world.fields.soil_cohesion;
    for (const cell of cells) {
      const causes = [];
      const k = key(cell);
      if (this._lastRootLossEvent.has(k)) causes.push(this._lastRootLossEvent.get(k));
      if (this._lastSaturationEvent.has(k)) causes.push(this._lastSaturationEvent.get(k));
      const evt = this.eventLog.record(t, "cohesion_degraded", cell, { soil_cohesion: round4(coh[cell[0]][cell[1]]) }, causes);
      this._lastCohesionEvent.set(k, evt.event_id);
    }
  }

  _detectTrails(t, visitedCells) {
    const trail = this.world.fields.trail_intensity, seen = new Set();
    for (const cell of visitedCells) {
      const k = key(cell);
      if (seen.has(k)) continue;
      seen.add(k);
      if (trail[cell[0]][cell[1]] >= CONFIG.TRAIL_MATURE_THRESHOLD && !this.features.featureOfTypeAt(cell, "HerbivoreTrail")) {
        const evt = this.eventLog.record(t, "trail_formed", cell, { trail_intensity: round4(trail[cell[0]][cell[1]]) });
        this.features.create("HerbivoreTrail", [cell], t, evt.event_id);
      }
    }
  }

  _detectGrazedPatches(t, grazedCells) {
    const pressure = this.world.fields.grazing_pressure, seen = new Set();
    for (const cell of grazedCells) {
      const k = key(cell);
      if (seen.has(k)) continue;
      seen.add(k);
      if (pressure[cell[0]][cell[1]] >= CONFIG.GRAZED_PATCH_THRESHOLD && !this.features.featureOfTypeAt(cell, "GrazedPatch")) {
        const evt = this.eventLog.record(t, "grazed_patch_formed", cell, { grazing_pressure: round4(pressure[cell[0]][cell[1]]) });
        this.features.create("GrazedPatch", [cell], t, evt.event_id);
      }
    }
  }

  _detectPools(t) {
    const sw = this.world.fields.surface_water, n = this.world.n;
    for (let r = 0; r < n; r++) {
      for (let c = 0; c < n; c++) {
        if (!this.world.flowDirection[r][c] && sw[r][c] >= CONFIG.POOL_WATER_THRESHOLD) {
          this._poolPersist[r][c] += 1;
        } else {
          this._poolPersist[r][c] = 0;
        }
        if (this._poolPersist[r][c] === CONFIG.POOL_PERSIST_TICKS && !this.features.featureOfTypeAt([r, c], "WaterPool")) {
          const evt = this.eventLog.record(t, "pool_formed", [r, c], { surface_water: round4(sw[r][c]) },
            this._lastRainEventId ? [this._lastRainEventId] : []);
          this.features.create("WaterPool", [[r, c]], t, evt.event_id);
        }
      }
    }
  }

  _detectGullies(t, erosionInputs) {
    for (const info of erosionInputs) {
      const cell = info.cell;
      if (info.erosion_depth < CONFIG.GULLY_DEPTH_THRESHOLD) continue;
      if (this.features.featureOfTypeAt(cell, "ErosiveGully")) continue;
      const causes = [];
      if (this._lastRainEventId) causes.push(this._lastRainEventId);
      const k = key(cell);
      if (this._lastSaturationEvent.has(k)) causes.push(this._lastSaturationEvent.get(k));
      if (this._lastRootLossEvent.has(k)) causes.push(this._lastRootLossEvent.get(k));
      if (this._lastCohesionEvent.has(k)) causes.push(this._lastCohesionEvent.get(k));

      const inputs = { ...info };
      delete inputs.cell;
      delete inputs.erosion_depth_delta;
      const evt = this.eventLog.record(t, "gully_formed", cell, inputs, causes, { erosion_depth_delta: info.erosion_depth_delta });
      const feat = this.features.create("ErosiveGully", [cell], t, evt.event_id);
      evt.result.feature_id = feat.feature_id;
    }
  }
}

function key(cell) { return `${cell[0]},${cell[1]}`; }

// FeatureRegistry.featureAt (most-recently-created feature at a cell) is
// used by overrides.applyOverride and the viewer's click handler.
FeatureRegistry.prototype.featureAt = function (cell) {
  const feats = this.featuresAt(cell);
  return feats.length ? feats[feats.length - 1] : null;
};

// No-op in the browser; lets Node load this file for dry-run verification.
if (typeof module !== "undefined") {
  module.exports = { CONFIG, World, Simulation, RainEvent, RainSchedule, SeededRandom, applyOverride };
}
