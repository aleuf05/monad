/**
 * Monad Education 001 — Moonbase Architect v0.1
 * Physics & Environmental Simulation Engine
 * 
 * Physical Constants & Baseline Assumptions:
 * - Lunar Gravity: 1.62 m/s² (0.166 g)
 * - Solar Irradiance: 1361 W/m² (at normal incidence)
 * - Diurnal Cycle: 708.7 hours (~29.53 Earth days; 354.35h Day / 354.35h Night)
 * - Surface Temperature: +120°C (393 K) day, -130°C to -246°C (143 K to 27 K) night
 * - Galactic Cosmic Rays (GCR) + Solar Particle Events: ~300-800 mSv/year unshielded
 * - Human Daily Requirements: 0.84 kg O2, 2.5 L H2O, 2500 kcal food, generating 1.0 kg CO2
 */

export const LUNAR_CONSTANTS = {
  GRAVITY: 1.62, // m/s²
  SOLAR_FLUX: 1361, // W/m²
  DIURNAL_HOURS: 708.7, // Total lunar day length
  HALF_CYCLE_HOURS: 354.35,
  STEFAN_BOLTZMANN: 5.670374e-8, // W/(m²·K⁴)
  TEMP_DAY_K: 393, // ~120°C
  TEMP_NIGHT_K: 120, // ~ -153°C
  TEMP_PSR_K: 40, // Permanently Shadowed Region (~ -233°C)
  UNSHIELDED_RAD_RATE: 0.08, // mSv/hour (~700 mSv/year)
  SAFE_RAD_THRESHOLD: 0.0023, // ~20 mSv/year (occupational radiation limit)
  ATMOSPHERE_EARTH_KPA: 101.3,
  ATMOSPHERE_EXPLORATION_KPA: 56.0 // 34% O2, 66% N2 (reduced decompression risk)
};

export const MODULE_TYPES = {
  'cmd-core': {
    id: 'cmd-core',
    name: 'Command & Avionics Core',
    category: 'command',
    icon: '⚡',
    costCredits: 850000,
    massKg: 12000,
    basePowerKw: 8.0,
    heatKw: 6.5,
    crewCapacity: 2,
    shieldingFactor: 0.45,
    pressureKpa: 101.3,
    description: 'Central nerve center with redundant avionics, comms array, deep-space antenna, and habitat control computers.',
    specs: {
      crew: 2,
      powerReq: '8.0 kW',
      hull: 'Al-Li 2195 alloy with 15-layer MLI blanket',
      lifeExpectancy: '30 years'
    }
  },
  'hab-dome': {
    id: 'hab-dome',
    name: 'Inflatable Habitation Dome',
    category: 'habitat',
    icon: '🛖',
    costCredits: 620000,
    massKg: 8500,
    basePowerKw: 4.5,
    heatKw: 3.8,
    crewCapacity: 4,
    shieldingFactor: 0.25, // Needs regolith cover
    pressureKpa: 101.3,
    description: '12m expandable composite habitat with private crew sleeping quarters, galley, hygiene unit, and medical station.',
    specs: {
      crew: 4,
      volume: '450 m³',
      hull: 'Vectran / Kevlar multi-ply inflatable bladder with micrometeorite bumper',
      burstMargin: '4.2x working pressure'
    }
  },
  'bio-hydro': {
    id: 'bio-hydro',
    name: 'Bioregenerative Hydroponics',
    category: 'life-support',
    icon: '🌱',
    costCredits: 740000,
    massKg: 9800,
    basePowerKw: 14.0, // High lighting requirements
    heatKw: 11.0,
    crewCapacity: 0,
    shieldingFactor: 0.35,
    pressureKpa: 101.3,
    o2ProductionKgHr: 0.15, // Produces ~3.6 kg/day O2
    co2AbsorptionKgHr: 0.18,
    foodYieldKcalDay: 5000,
    description: 'Automated aeroponic vertical crop towers and spirulina photobioreactors recycling CO2 into O2 and fresh nutrition.',
    specs: {
      crops: 'Dwarf wheat, sweet potatoes, microgreens, spirulina algae',
      co2Scrub: '4.3 kg/day',
      o2Gen: '3.6 kg/day',
      lighting: 'Tunable LED Photosynthetic Active Radiation (PAR) spectrum'
    }
  },
  'eclss-core': {
    id: 'eclss-core',
    name: 'ECLSS Recycling Processor',
    category: 'life-support',
    icon: '♻️',
    costCredits: 920000,
    massKg: 11500,
    basePowerKw: 9.5,
    heatKw: 8.0,
    crewCapacity: 0,
    shieldingFactor: 0.40,
    pressureKpa: 101.3,
    waterRecoveryRate: 0.98, // 98% closed loop water recovery
    o2RecoveryRate: 0.95,
    description: 'Advanced closed-loop environmental control: Sabatier CO2 reduction, urine processor distillation, and catalytic water purifier.',
    specs: {
      waterEfficiency: '98.2% recovery',
      o2Efficiency: '95.0% recovery',
      processors: 'Sabatier reactor (CO2 + 4H2 -> CH4 + 2H2O), Bosch carbon deposition, Vapor Compression Distillation'
    }
  },
  'reg-shield': {
    id: 'reg-shield',
    name: 'Sintered Regolith Arch',
    category: 'shielding',
    icon: '🛡️',
    costCredits: 310000,
    massKg: 45000, // Heavy in-situ mass
    basePowerKw: 0.0,
    heatKw: 0.0,
    crewCapacity: 0,
    shieldingFactor: 0.94, // 94% radiation reduction (2.5m thick sintered regolith)
    thermalInsulation: 0.92,
    description: '3D-printed microwave-sintered basalt arch. Provides massive shielding against Galactic Cosmic Rays, Solar Particle Events, and thermal extremes.',
    specs: {
      thickness: '2.5 meters sintered basalt',
      density: '1.85 g/cm³',
      radiationAttenuation: 'Dose reduced by 94%',
      thermalLag: 'Damps 250°C surface swing to within ±3°C internally'
    }
  },
  'pv-array': {
    id: 'pv-array',
    name: 'Deployable Solar PV Array',
    category: 'power',
    icon: '☀️',
    costCredits: 420000,
    massKg: 4200,
    peakPowerKw: 45.0, // In full sunlight
    heatKw: 0.0,
    crewCapacity: 0,
    shieldingFactor: 0.0,
    description: 'High-efficiency triple-junction GaAs solar arrays mounted on sun-tracking masts with electrodynamic dust-repelling coatings.',
    specs: {
      peakOutput: '45.0 kW (normal solar incidence)',
      efficiency: '34.2% multi-junction GaAs',
      dustMitigation: 'Active electrodynamic standing wave screen',
      tracking: 'Dual-axis azimuth/elevation drive'
    }
  },
  'rfc-batt': {
    id: 'rfc-batt',
    name: 'Regenerative Fuel Cell Bank',
    category: 'power',
    icon: '🔋',
    costCredits: 680000,
    massKg: 14000,
    storageKwh: 1200.0, // 1.2 MWh storage
    chargeEfficiency: 0.85,
    dischargeEfficiency: 0.88,
    maxDischargeKw: 35.0,
    description: 'Reversible PEM electrolyzer / fuel cell system. Stores daytime solar surplus as H2/O2 and discharges steady power during the 354h lunar night.',
    specs: {
      capacity: '1,200 kWh energy buffer',
      peakDischarge: '35 kW',
      reactants: 'Cryogenic H2 and O2 storage vessels'
    }
  },
  'kilo-nuc': {
    id: 'kilo-nuc',
    name: 'Kilopower Fission Reactor',
    category: 'power',
    icon: '⚛️',
    costCredits: 1850000,
    massKg: 18000,
    basePowerKw: -40.0, // Supplies 40 kW continuously day and night
    heatKw: 120.0, // High waste heat to dissipate
    crewCapacity: 0,
    shieldingFactor: 0.0,
    radiationEmitterDistance: 3, // Requires exclusion zone
    description: 'Enriched uranium U-235 solid-cast core reactor with sodium heat pipes and Stirling engines. Generates continuous baseline power unaffected by lunar night.',
    specs: {
      continuousPower: '40.0 kW (24/7/365 continuous)',
      fuel: 'Cast alloy U-235 with BeO radial reflector',
      heatExchangers: 'Sodium heat pipes coupled to Stirling convertors',
      operationalLife: '15 years unserviced'
    }
  },
  'isru-ice': {
    id: 'isru-ice',
    name: 'Cryo-Regolith Water Extractor',
    category: 'isru',
    icon: '🧊',
    costCredits: 780000,
    massKg: 9500,
    basePowerKw: 16.0,
    heatKw: 12.5,
    waterProductionLDay: 60.0, // 60 liters / day from icy permafrost
    crewCapacity: 0,
    shieldingFactor: 0.10,
    description: 'Sublimation dome and auger drill operating at crater boundaries to extract water ice volatiles from polar permanently shadowed cold traps.',
    specs: {
      extractionRate: '60 Liters/day H2O',
      volatiles: 'Water ice (H2O), Ammonia (NH3), Carbon dioxide (CO2)',
      technology: 'Downhole thermal coring with vacuum sublimation condenser'
    }
  },
  'isru-o2': {
    id: 'isru-o2',
    name: 'Molten Regolith O2 Electrolyzer',
    category: 'isru',
    icon: '🫧',
    costCredits: 820000,
    massKg: 11000,
    basePowerKw: 22.0,
    heatKw: 18.0,
    o2ProductionKgHr: 0.85, // ~20.4 kg/day
    crewCapacity: 0,
    shieldingFactor: 0.10,
    description: 'High-temperature molten regolith electrolysis (MRE) breaking down lunar ilmenite (FeTiO3) and silicates into pure breathable oxygen and structural iron.',
    specs: {
      o2Yield: '20.4 kg/day',
      operatingTemp: '1600°C molten bath',
      byproducts: 'Metallic iron/titanium ingots for construction'
    }
  },
  'therm-rad': {
    id: 'therm-rad',
    name: 'Deployable Thermal Radiator',
    category: 'thermal',
    icon: '❄️',
    costCredits: 380000,
    massKg: 3600,
    basePowerKw: 1.2,
    heatDissipationKw: 40.0, // Dissipates up to 40 kW of waste heat
    crewCapacity: 0,
    shieldingFactor: 0.0,
    description: 'Silver-teflon coated aluminum composite panels with embedded ammonia loops rejecting excess habitat and reactor heat to deep space (3 Kelvin sink).',
    specs: {
      coolingCapacity: '40.0 kW at 300K radiator temperature',
      workingFluid: 'Anhydrous ammonia (NH3) two-phase loop',
      emissivity: '0.92, Solar absorptivity: 0.08'
    }
  },
  'dust-lock': {
    id: 'dust-lock',
    name: 'Electrostatic Airlock & Suitport',
    category: 'utility',
    icon: '🚪',
    costCredits: 510000,
    massKg: 7200,
    basePowerKw: 3.5,
    heatKw: 2.0,
    crewCapacity: 0,
    shieldingFactor: 0.50,
    pressureKpa: 101.3,
    dustMitigationRate: 0.99, // Stops abrasive toxic dust from entering
    description: 'Dual-chamber vacuum airlock with rear-entry suitports and electron-beam dust showers preventing hazardous jagged lunar regolith dust intrusion.',
    specs: {
      dustRejection: '99.2% airborne particle removal',
      suitports: '2 external suit docking interfaces (no air dumped during EVA)',
      evacuationTime: '180 seconds to full vacuum recovery'
    }
  }
};

export const PRESET_SCENARIOS = {
  artemis: {
    id: 'artemis',
    name: 'Scenario 01: Artemis Base Camp',
    location: 'Shackleton Crater Rim (89.9° S)',
    solarAvailability: 0.88, // 88% solar illumination year-round
    crewTarget: 4,
    budgetCredits: 5000000,
    description: 'Deploy a four-astronaut exploratory base camp at the Lunar South Pole with solar power, closed-loop ECLSS, and regolith radiation shielding.',
    objectives: [
      { id: 'crew', text: 'Support 4 Crew Members in safe habitat quarters', check: (s) => s.totalCrewCapacity >= 4 },
      { id: 'power', text: 'Maintain positive power grid margin across all cycles', check: (s) => s.powerMarginKw >= 0 },
      { id: 'eclss', text: 'Provide positive net Oxygen and Water life support', check: (s) => s.netO2KgDay >= 0 && s.netH2OLDay >= 0 },
      { id: 'rad', text: 'Keep average crew radiation dose under 25 mSv/yr', check: (s) => s.avgRadiationDoseMsvYear <= 25.0 },
      { id: 'airlock', text: 'Install at least one Dust-Lock Airlock for safe EVA egress', check: (s) => s.counts['dust-lock'] >= 1 }
    ],
    initialModules: [
      { typeId: 'cmd-core', x: 4, y: 4 },
      { typeId: 'hab-dome', x: 5, y: 4 },
      { typeId: 'dust-lock', x: 6, y: 4 },
      { typeId: 'pv-array', x: 3, y: 2 },
      { typeId: 'rfc-batt', x: 3, y: 4 }
    ]
  },
  lavatube: {
    id: 'lavatube',
    name: 'Scenario 02: Marius Hills Lava Tube',
    location: 'Oceanus Procellarum (14.2° N, 56.8° W)',
    solarAvailability: 0.50, // Standard 354h day / 354h night
    crewTarget: 8,
    budgetCredits: 8500000,
    description: 'Construct a deep subterranean outpost sheltered under a volcanic basalt roof. Protected from surface radiation, but requires heavy continuous nuclear power.',
    objectives: [
      { id: 'crew', text: 'Accommodate 8 crew members with dual habitat modules', check: (s) => s.totalCrewCapacity >= 8 },
      { id: 'nuclear', text: 'Deploy at least 1 Kilopower Fission Reactor for continuous baseline power', check: (s) => s.counts['kilo-nuc'] >= 1 },
      { id: 'thermal', text: 'Deploy thermal radiators to reject reactor waste heat', check: (s) => s.thermalMarginKw >= 0 },
      { id: 'food', text: 'Deploy Hydroponic module for supplemental food generation', check: (s) => s.counts['bio-hydro'] >= 1 },
      { id: 'eclss', text: 'Deploy ECLSS core for 95%+ closed-loop water/air recovery', check: (s) => s.counts['eclss-core'] >= 1 }
    ],
    initialModules: [
      { typeId: 'cmd-core', x: 4, y: 4 },
      { typeId: 'hab-dome', x: 4, y: 5 },
      { typeId: 'hab-dome', x: 5, y: 5 },
      { typeId: 'kilo-nuc', x: 2, y: 2 },
      { typeId: 'therm-rad', x: 2, y: 4 }
    ]
  },
  isru_industrial: {
    id: 'isru_industrial',
    name: 'Scenario 03: Shackleton ISRU Refinery',
    location: 'Amundsen-Ganswindt Basin (80.5° S)',
    solarAvailability: 0.75,
    crewTarget: 12,
    budgetCredits: 12000000,
    description: 'Establish a self-sustaining industrial settlement refining lunar water ice and atmospheric oxygen to fuel the cis-lunar transit economy.',
    objectives: [
      { id: 'crew', text: 'House 12 crew members with high morale & life support', check: (s) => s.totalCrewCapacity >= 12 },
      { id: 'isru_h2o', text: 'Deploy 2+ Cryo-Regolith Water Extractors (>100 L/day)', check: (s) => s.counts['isru-ice'] >= 2 },
      { id: 'isru_o2', text: 'Deploy 2+ Molten Regolith O2 Electrolyzers (>40 kg/day O2)', check: (s) => s.counts['isru-o2'] >= 2 },
      { id: 'shielding', text: 'Surround living habitats with Sintered Regolith Arches', check: (s) => s.counts['reg-shield'] >= 4 },
      { id: 'power', text: 'Generate at least 80 kW continuous power output', check: (s) => s.totalPowerGenKw >= 80 }
    ],
    initialModules: [
      { typeId: 'cmd-core', x: 4, y: 4 },
      { typeId: 'hab-dome', x: 4, y: 5 },
      { typeId: 'hab-dome', x: 5, y: 5 },
      { typeId: 'hab-dome', x: 5, y: 4 },
      { typeId: 'kilo-nuc', x: 2, y: 2 },
      { typeId: 'pv-array', x: 6, y: 2 },
      { typeId: 'therm-rad', x: 2, y: 4 },
      { typeId: 'isru-ice', x: 6, y: 5 }
    ]
  },
  sandbox: {
    id: 'sandbox',
    name: 'Freeform Lunar Architect Sandbox',
    location: 'Custom Lunar Coordinate',
    solarAvailability: 0.85,
    crewTarget: 6,
    budgetCredits: 20000000,
    description: 'Unconstrained lunar engineering sandbox. Design custom modular habitats, experiment with power systems, and optimize ECLSS mass flow.',
    objectives: [
      { id: 'power', text: 'Maintain a stable power grid (Positive Margin)', check: (s) => s.powerMarginKw >= 0 },
      { id: 'life', text: 'Maintain breathable air and water for all onboard crew', check: (s) => s.netO2KgDay >= 0 && s.netH2OLDay >= 0 },
      { id: 'safe', text: 'Maintain radiation dosage below occupational limits (<25 mSv/yr)', check: (s) => s.avgRadiationDoseMsvYear <= 25.0 }
    ],
    initialModules: [
      { typeId: 'cmd-core', x: 4, y: 4 },
      { typeId: 'hab-dome', x: 5, y: 4 },
      { typeId: 'dust-lock', x: 6, y: 4 },
      { typeId: 'pv-array', x: 3, y: 3 }
    ]
  }
};

/**
 * Lunar Base Simulation Engine Class
 */
export class MoonbaseEngine {
  constructor(scenarioId = 'artemis') {
    this.gridWidth = 10;
    this.gridHeight = 10;
    this.grid = Array.from({ length: this.gridHeight }, () => Array(this.gridWidth).fill(null));
    
    this.scenario = PRESET_SCENARIOS[scenarioId] || PRESET_SCENARIOS.artemis;
    this.simulationTimeHours = 0.0;
    this.timeScale = 1.0;
    this.isPaused = false;

    this.batteryStoredKwh = 300.0;
    this.oxygenStorageKg = 250.0;
    this.waterStorageL = 1200.0;
    this.foodStorageKcal = 80000.0;

    this.history = [];
    this.eventLog = [];
    this.creditsSpent = 0;

    this.loadScenario(scenarioId);
  }

  loadScenario(scenarioId) {
    this.scenario = PRESET_SCENARIOS[scenarioId] || PRESET_SCENARIOS.artemis;
    this.grid = Array.from({ length: this.gridHeight }, () => Array(this.gridWidth).fill(null));
    this.simulationTimeHours = 0.0;
    this.creditsSpent = 0;
    this.eventLog = [];

    if (this.scenario.initialModules) {
      for (const m of this.scenario.initialModules) {
        this.placeModule(m.x, m.y, m.typeId, false);
      }
    }

    this.batteryStoredKwh = 400.0;
    this.oxygenStorageKg = 300.0;
    this.waterStorageL = 1500.0;
    this.foodStorageKcal = 100000.0;

    this.logEvent('System Initialized', `Loaded scenario: ${this.scenario.name} at ${this.scenario.location}`);
  }

  logEvent(title, detail, severity = 'info') {
    this.eventLog.unshift({
      timestamp: this.simulationTimeHours.toFixed(1),
      title,
      detail,
      severity,
      time: new Date().toISOString()
    });
    if (this.eventLog.length > 50) this.eventLog.pop();
  }

  placeModule(x, y, typeId, chargeCost = true) {
    if (x < 0 || x >= this.gridWidth || y < 0 || y >= this.gridHeight) return false;
    const def = MODULE_TYPES[typeId];
    if (!def) return false;

    if (this.grid[y][x] !== null) return false;

    this.grid[y][x] = {
      instanceId: `mod_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
      typeId,
      x,
      y,
      placedAtHour: this.simulationTimeHours,
      health: 100.0
    };

    if (chargeCost) {
      this.creditsSpent += def.costCredits;
      this.logEvent('Module Deployed', `Installed ${def.name} at coordinate (${x}, ${y})`, 'success');
    }
    return true;
  }

  removeModule(x, y) {
    if (x < 0 || x >= this.gridWidth || y < 0 || y >= this.gridHeight) return null;
    const existing = this.grid[y][x];
    if (!existing) return null;

    const def = MODULE_TYPES[existing.typeId];
    this.grid[y][x] = null;
    if (def) {
      this.creditsSpent = Math.max(0, this.creditsSpent - Math.round(def.costCredits * 0.75));
      this.logEvent('Module Reclaimed', `Dismantled ${def.name} at (${x}, ${y}) with 75% material salvage`, 'warning');
    }
    return existing;
  }

  getPlacedModules() {
    const list = [];
    for (let y = 0; y < this.gridHeight; y++) {
      for (let x = 0; x < this.gridWidth; x++) {
        if (this.grid[y][x]) list.push(this.grid[y][x]);
      }
    }
    return list;
  }

  getSolarIllumination(hour) {
    const cycleHour = (hour % LUNAR_CONSTANTS.DIURNAL_HOURS);
    const angleRad = (cycleHour / LUNAR_CONSTANTS.DIURNAL_HOURS) * 2 * Math.PI;
    const sunElevationSin = Math.sin(angleRad);

    if (sunElevationSin > 0) {
      return Math.max(0, sunElevationSin * this.scenario.solarAvailability);
    } else {
      const polarBonus = Math.max(0, (this.scenario.solarAvailability - 0.5) * 2.0);
      return Math.max(0, polarBonus * 0.4);
    }
  }

  calculateState() {
    const modules = this.getPlacedModules();
    const counts = {};
    for (const key of Object.keys(MODULE_TYPES)) counts[key] = 0;

    let totalMassKg = 0;
    let totalCrewCapacity = 0;
    let totalPowerReqKw = 0;
    let totalPowerGenKw = 0;
    let totalHeatGenKw = 0;
    let totalHeatDissipationKw = 0;
    let maxBatteryCapacityKwh = 0;
    let maxDischargeKw = 0;

    let o2GenKgHr = 0;
    let co2AbsorptionKgHr = 0;
    let h2oGenLDay = 0;
    let foodGenKcalDay = 0;

    const solarFactor = this.getSolarIllumination(this.simulationTimeHours);
    const isDay = solarFactor > 0.05;

    for (const m of modules) {
      const def = MODULE_TYPES[m.typeId];
      if (!def) continue;
      counts[m.typeId]++;
      totalMassKg += def.massKg;
      totalCrewCapacity += (def.crewCapacity || 0);

      if (def.basePowerKw < 0) {
        totalPowerGenKw += Math.abs(def.basePowerKw);
      } else {
        totalPowerReqKw += (def.basePowerKw || 0);
      }

      if (def.peakPowerKw) {
        totalPowerGenKw += def.peakPowerKw * solarFactor;
      }

      if (def.storageKwh) {
        maxBatteryCapacityKwh += def.storageKwh;
        maxDischargeKw += (def.maxDischargeKw || 30.0);
      }

      totalHeatGenKw += (def.heatKw || 0);
      if (def.heatDissipationKw) {
        totalHeatDissipationKw += def.heatDissipationKw;
      }

      if (def.o2ProductionKgHr) o2GenKgHr += def.o2ProductionKgHr;
      if (def.co2AbsorptionKgHr) co2AbsorptionKgHr += def.co2AbsorptionKgHr;
      if (def.waterProductionLDay) h2oGenLDay += def.waterProductionLDay;
      if (def.foodYieldKcalDay) foodGenKcalDay += def.foodYieldKcalDay;
    }

    totalHeatDissipationKw += 5.0;

    const activeCrew = Math.min(totalCrewCapacity, Math.max(1, this.scenario.crewTarget));
    const crewO2NeedKgHr = activeCrew * (0.84 / 24.0);
    const crewCO2GenKgHr = activeCrew * (1.00 / 24.0);
    const crewH2ONeedLDay = activeCrew * 2.5;
    const crewFoodNeedKcalDay = activeCrew * 2500;

    const rawPowerMargin = totalPowerGenKw - totalPowerReqKw;
    let powerMarginKw = rawPowerMargin;
    let batteryState = 'steady';

    if (rawPowerMargin >= 0) {
      if (maxBatteryCapacityKwh > 0) {
        batteryState = 'charging';
      }
    } else {
      const deficit = Math.abs(rawPowerMargin);
      if (this.batteryStoredKwh > 0) {
        batteryState = 'discharging';
        powerMarginKw = Math.max(-deficit + maxDischargeKw, -deficit);
      } else {
        batteryState = 'depleted';
      }
    }

    const thermalMarginKw = totalHeatDissipationKw - totalHeatGenKw;

    let totalShieldScore = 0;
    let evaluatedHabs = 0;

    for (const m of modules) {
      const def = MODULE_TYPES[m.typeId];
      if (def && (def.category === 'habitat' || def.category === 'command')) {
        evaluatedHabs++;
        let localShield = def.shieldingFactor || 0.2;
        const neighbors = [
          [m.x - 1, m.y], [m.x + 1, m.y], [m.x, m.y - 1], [m.x, m.y + 1]
        ];
        let shieldNeighbors = 0;
        for (const [nx, ny] of neighbors) {
          if (nx >= 0 && nx < this.gridWidth && ny >= 0 && ny < this.gridHeight) {
            const neighborMod = this.grid[ny][nx];
            if (neighborMod && neighborMod.typeId === 'reg-shield') {
              shieldNeighbors++;
            }
          }
        }
        localShield = Math.min(0.96, localShield + (shieldNeighbors * 0.25));
        totalShieldScore += localShield;
      }
    }

    const avgShieldFactor = evaluatedHabs > 0 ? (totalShieldScore / evaluatedHabs) : 0.2;
    const avgRadiationDoseMsvYear = Math.max(8.0, 700.0 * (1.0 - avgShieldFactor));

    const netO2KgDay = (o2GenKgHr - crewO2NeedKgHr) * 24.0;
    const netH2OLDay = h2oGenLDay - crewH2ONeedLDay;
    const netFoodKcalDay = foodGenKcalDay - crewFoodNeedKcalDay;

    let survivalScore = 100;
    if (powerMarginKw < 0) survivalScore -= 35;
    if (netO2KgDay < 0 && this.oxygenStorageKg < 10) survivalScore -= 40;
    if (netH2OLDay < 0 && this.waterStorageL < 20) survivalScore -= 30;
    if (thermalMarginKw < -10) survivalScore -= 20;
    if (avgRadiationDoseMsvYear > 50) survivalScore -= 15;
    survivalScore = Math.max(0, Math.min(100, survivalScore));

    const evaluatedObjectives = (this.scenario.objectives || []).map(obj => {
      const passed = obj.check({
        totalCrewCapacity,
        powerMarginKw,
        netO2KgDay,
        netH2OLDay,
        avgRadiationDoseMsvYear,
        thermalMarginKw,
        totalPowerGenKw,
        counts
      });
      return {
        id: obj.id,
        text: obj.text,
        passed
      };
    });

    const allObjectivesMet = evaluatedObjectives.length > 0 && evaluatedObjectives.every(o => o.passed);

    return {
      simulationTimeHours: this.simulationTimeHours,
      diurnalCycleHours: this.simulationTimeHours % LUNAR_CONSTANTS.DIURNAL_HOURS,
      solarFactor,
      isDay,
      moduleCount: modules.length,
      counts,
      activeCrew,
      totalCrewCapacity,
      totalMassKg,
      creditsSpent: this.creditsSpent,
      budgetRemaining: this.scenario.budgetCredits - this.creditsSpent,
      totalPowerGenKw,
      totalPowerReqKw,
      powerMarginKw,
      batteryStoredKwh: this.batteryStoredKwh,
      maxBatteryCapacityKwh,
      batteryState,
      totalHeatGenKw,
      totalHeatDissipationKw,
      thermalMarginKw,
      avgShieldFactor,
      avgRadiationDoseMsvYear,
      o2GenKgHr,
      crewO2NeedKgHr,
      netO2KgDay,
      oxygenStorageKg: this.oxygenStorageKg,
      netH2OLDay,
      waterStorageL: this.waterStorageL,
      netFoodKcalDay,
      foodStorageKcal: this.foodStorageKcal,
      survivalScore,
      evaluatedObjectives,
      allObjectivesMet
    };
  }

  step(deltaHours) {
    if (this.isPaused || deltaHours <= 0) return this.calculateState();

    const dt = deltaHours * this.timeScale;
    this.simulationTimeHours += dt;

    const state = this.calculateState();

    const rawPowerMargin = state.totalPowerGenKw - state.totalPowerReqKw;
    if (rawPowerMargin > 0) {
      const chargeEnergy = rawPowerMargin * dt * 0.85;
      this.batteryStoredKwh = Math.min(state.maxBatteryCapacityKwh, this.batteryStoredKwh + chargeEnergy);
    } else {
      const deficitEnergy = Math.abs(rawPowerMargin) * dt / 0.88;
      this.batteryStoredKwh = Math.max(0, this.batteryStoredKwh - deficitEnergy);
    }

    const dO2 = (state.netO2KgDay / 24.0) * dt;
    this.oxygenStorageKg = Math.max(0, Math.min(2000.0, this.oxygenStorageKg + dO2));

    const dH2O = (state.netH2OLDay / 24.0) * dt;
    this.waterStorageL = Math.max(0, Math.min(10000.0, this.waterStorageL + dH2O));

    const dFood = (state.netFoodKcalDay / 24.0) * dt;
    this.foodStorageKcal = Math.max(0, Math.min(500000.0, this.foodStorageKcal + dFood));

    if (this.history.length === 0 || (this.simulationTimeHours - this.history[this.history.length - 1].hour) >= 10.0) {
      this.history.push({
        hour: this.simulationTimeHours,
        powerGen: state.totalPowerGenKw,
        powerReq: state.totalPowerReqKw,
        battery: this.batteryStoredKwh,
        radiation: state.avgRadiationDoseMsvYear,
        score: state.survivalScore
      });
      if (this.history.length > 60) this.history.shift();
    }

    return this.calculateState();
  }

  exportDossier() {
    const state = this.calculateState();
    return {
      version: '0.1',
      title: 'Monad Education 001 — Moonbase Architect Manifest',
      generatedAt: new Date().toISOString(),
      scenario: this.scenario,
      simulationTimeHours: this.simulationTimeHours,
      metrics: {
        crewCapacity: state.totalCrewCapacity,
        activeCrew: state.activeCrew,
        powerGenKw: state.totalPowerGenKw.toFixed(1),
        powerReqKw: state.totalPowerReqKw.toFixed(1),
        batteryStoredKwh: state.batteryStoredKwh.toFixed(1),
        radiationDoseMsvYear: state.avgRadiationDoseMsvYear.toFixed(1),
        netO2KgDay: state.netO2KgDay.toFixed(2),
        netH2OLDay: state.netH2OLDay.toFixed(2),
        survivalScore: state.survivalScore,
        allObjectivesMet: state.allObjectivesMet
      },
      gridState: this.grid.map(row => row.map(cell => cell ? { typeId: cell.typeId, x: cell.x, y: cell.y } : null))
    };
  }

  importDossier(json) {
    if (!json || !json.gridState) return false;
    this.grid = Array.from({ length: this.gridHeight }, () => Array(this.gridWidth).fill(null));
    this.creditsSpent = 0;

    for (let y = 0; y < json.gridState.length && y < this.gridHeight; y++) {
      for (let x = 0; x < json.gridState[y].length && x < this.gridWidth; x++) {
        const item = json.gridState[y][x];
        if (item && MODULE_TYPES[item.typeId]) {
          this.placeModule(x, y, item.typeId, true);
        }
      }
    }
    this.logEvent('Dossier Imported', 'Restored base layout from external manifest', 'success');
    return true;
  }
}
