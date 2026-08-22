/**
 * Monad Education 001 — Moonbase Architect v0.1
 * Application Controller & UI Orchestration
 */

import { MoonbaseEngine, MODULE_TYPES, PRESET_SCENARIOS, LUNAR_CONSTANTS } from './engine.js';
import { MoonbaseRenderer } from './renderer.js';
import { MoonbaseAudio } from './sound.js';

class MoonbaseApp {
  constructor() {
    this.engine = new MoonbaseEngine('artemis');
    this.audio = new MoonbaseAudio();

    this.canvas = document.getElementById('lunarCanvas');
    this.renderer = new MoonbaseRenderer(this.canvas, this.engine);

    this.lastTime = performance.now();
    this.selectedTool = 'hab-dome';
    this.renderer.selectedTool = this.selectedTool;

    this.initUI();
    this.bindEvents();
    this.renderLoop();
  }

  initUI() {
    this.renderToolPalette();
    this.renderScenarioOptions();
    this.updateHUD();
  }

  renderScenarioOptions() {
    const sel = document.getElementById('scenarioSelect');
    if (!sel) return;
    sel.innerHTML = Object.values(PRESET_SCENARIOS)
      .map(sc => `<option value="${sc.id}">${sc.name}</option>`)
      .join('');
    sel.value = this.engine.scenario.id;
    this.updateScenarioDetails();
  }

  updateScenarioDetails() {
    const sc = this.engine.scenario;
    const locEl = document.getElementById('scenarioLocation');
    if (locEl) locEl.textContent = `${sc.location} · Solar Avail: ${(sc.solarAvailability * 100).toFixed(0)}%`;
  }

  renderToolPalette() {
    const container = document.getElementById('toolList');
    if (!container) return;

    let html = '';
    for (const [id, def] of Object.entries(MODULE_TYPES)) {
      const activeClass = this.selectedTool === id ? 'active' : '';
      const costStr = (def.costCredits / 1000).toFixed(0) + 'k Cr';
      html += `
        <div class="tool-item ${activeClass}" data-tool-id="${id}">
          <div class="tool-icon">${def.icon}</div>
          <div class="tool-info">
            <div class="tool-name">${def.name}</div>
            <div class="tool-sub">${def.category.toUpperCase()} · ${def.massKg.toLocaleString()} kg</div>
          </div>
          <div class="tool-cost">${costStr}</div>
        </div>
      `;
    }
    container.innerHTML = html;
  }

  bindEvents() {
    // 1. Tool Selection
    const toolList = document.getElementById('toolList');
    if (toolList) {
      toolList.addEventListener('click', (e) => {
        const item = e.target.closest('.tool-item');
        if (!item) return;
        const toolId = item.getAttribute('data-tool-id');
        this.selectTool(toolId);
        this.audio.playClick();
      });
    }

    // Demolish Tool
    const demoBtn = document.getElementById('btnDemolish');
    if (demoBtn) {
      demoBtn.addEventListener('click', () => {
        this.selectTool('demolish');
        this.audio.playClick();
      });
    }

    // Inspect Tool
    const inspectBtn = document.getElementById('btnInspect');
    if (inspectBtn) {
      inspectBtn.addEventListener('click', () => {
        this.selectTool('inspect');
        this.audio.playClick();
      });
    }

    // 2. Scenario Switcher
    const scenarioSel = document.getElementById('scenarioSelect');
    if (scenarioSel) {
      scenarioSel.addEventListener('change', (e) => {
        this.engine.loadScenario(e.target.value);
        this.updateScenarioDetails();
        this.audio.playClick();
      });
    }

    // 3. Time Controls
    const pauseBtn = document.getElementById('btnPause');
    if (pauseBtn) {
      pauseBtn.addEventListener('click', () => {
        this.engine.isPaused = !this.engine.isPaused;
        pauseBtn.textContent = this.engine.isPaused ? '▶ Resume' : '⏸ Pause';
        pauseBtn.classList.toggle('active', this.engine.isPaused);
        this.audio.playClick();
      });
    }

    const timeBtns = document.querySelectorAll('.time-btn[data-scale]');
    timeBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        timeBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.engine.timeScale = parseFloat(btn.getAttribute('data-scale'));
        this.audio.playClick();
      });
    });

    // 4. Layer Overlays
    const layerBtns = document.querySelectorAll('.layer-btn[data-layer]');
    layerBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        layerBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.renderer.overlayMode = btn.getAttribute('data-layer');
        this.audio.playClick();
      });
    });

    // 5. Canvas Interactions
    this.canvas.addEventListener('mousemove', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const clientX = e.clientX - rect.left;
      const clientY = e.clientY - rect.top;
      this.renderer.hoverCell = this.renderer.screenToGrid(clientX, clientY);
    });

    this.canvas.addEventListener('mouseleave', () => {
      this.renderer.hoverCell = null;
    });

    this.canvas.addEventListener('click', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const clientX = e.clientX - rect.left;
      const clientY = e.clientY - rect.top;
      const cell = this.renderer.screenToGrid(clientX, clientY);
      if (!cell) return;

      if (this.selectedTool === 'demolish') {
        const removed = this.engine.removeModule(cell.x, cell.y);
        if (removed) this.audio.playDemolish();
      } else if (this.selectedTool === 'inspect') {
        this.renderer.selectedCell = cell;
        this.openInspectorModal(cell.x, cell.y);
        this.audio.playClick();
      } else if (MODULE_TYPES[this.selectedTool]) {
        const success = this.engine.placeModule(cell.x, cell.y, this.selectedTool, true);
        if (success) {
          this.audio.playPlace();
        } else {
          // If already occupied, select cell for inspection
          this.renderer.selectedCell = cell;
          this.openInspectorModal(cell.x, cell.y);
        }
      }
      this.updateHUD();
    });

    // 6. Audio Mute Toggle
    const muteBtn = document.getElementById('btnMute');
    if (muteBtn) {
      muteBtn.addEventListener('click', () => {
        this.audio.isMuted = !this.audio.isMuted;
        muteBtn.textContent = this.audio.isMuted ? '🔇 Muted' : '🔊 Sound: On';
      });
    }

    // 7. Modals: Physics Formulas Drawer, Dossier Export, Reset
    const btnFormulas = document.getElementById('btnFormulas');
    if (btnFormulas) {
      btnFormulas.addEventListener('click', () => this.openFormulasModal());
    }

    const btnExport = document.getElementById('btnExport');
    if (btnExport) {
      btnExport.addEventListener('click', () => this.openExportModal());
    }

    const btnReset = document.getElementById('btnReset');
    if (btnReset) {
      btnReset.addEventListener('click', () => {
        if (confirm('Reset current lunar base layout?')) {
          this.engine.loadScenario(this.engine.scenario.id);
          this.updateHUD();
          this.audio.playAlert();
        }
      });
    }

    // Generic modal closer
    document.addEventListener('click', (e) => {
      if (e.target.matches('.modal-close') || e.target.matches('.modal-backdrop')) {
        document.querySelectorAll('.modal-backdrop').forEach(m => m.remove());
      }
    });
  }

  selectTool(toolId) {
    this.selectedTool = toolId;
    this.renderer.selectedTool = toolId;

    document.querySelectorAll('.tool-item').forEach(item => {
      item.classList.toggle('active', item.getAttribute('data-tool-id') === toolId);
    });

    const demoBtn = document.getElementById('btnDemolish');
    if (demoBtn) demoBtn.classList.toggle('active', toolId === 'demolish');

    const inspectBtn = document.getElementById('btnInspect');
    if (inspectBtn) inspectBtn.classList.toggle('active', toolId === 'inspect');
  }

  updateHUD() {
    const state = this.engine.calculateState();

    // Clock
    const dayHours = state.simulationTimeHours;
    const diurnalPercent = ((state.diurnalCycleHours / LUNAR_CONSTANTS.DIURNAL_HOURS) * 100).toFixed(0);
    const clockEl = document.getElementById('simClock');
    if (clockEl) {
      clockEl.textContent = `T+${dayHours.toFixed(1)}h (${diurnalPercent}% Diurnal)`;
    }

    // Budget
    const budgetEl = document.getElementById('hudBudget');
    if (budgetEl) {
      const remainingK = (state.budgetRemaining / 1000).toFixed(0);
      budgetEl.textContent = `${remainingK}k Cr`;
      budgetEl.className = state.budgetRemaining >= 0 ? 'budget-badge' : 'budget-badge danger';
    }

    // Power Metric
    const powerValEl = document.getElementById('hudPowerVal');
    const powerBarEl = document.getElementById('hudPowerBar');
    const powerSubEl = document.getElementById('hudPowerSub');
    if (powerValEl && powerBarEl && powerSubEl) {
      const margin = state.powerMarginKw;
      powerValEl.textContent = `${margin >= 0 ? '+' : ''}${margin.toFixed(1)} kW`;
      powerValEl.className = margin >= 0 ? 'mc-value green' : 'mc-value red';

      const powerPct = Math.min(100, Math.max(0, (state.totalPowerGenKw / Math.max(1, state.totalPowerReqKw)) * 100));
      powerBarEl.style.width = `${powerPct}%`;
      powerBarEl.className = margin >= 0 ? 'mc-fill' : 'mc-fill red';

      powerSubEl.innerHTML = `
        <span>Gen: <strong>${state.totalPowerGenKw.toFixed(1)} kW</strong></span>
        <span>Req: <strong>${state.totalPowerReqKw.toFixed(1)} kW</strong></span>
        <span>Batt: <strong>${state.batteryStoredKwh.toFixed(0)} kWh</strong></span>
      `;
    }

    // Life Support Metric (O2 & Water)
    const eclssValEl = document.getElementById('hudEclssVal');
    const eclssBarEl = document.getElementById('hudEclssBar');
    const eclssSubEl = document.getElementById('hudEclssSub');
    if (eclssValEl && eclssBarEl && eclssSubEl) {
      const o2Status = state.netO2KgDay >= 0 ? 'Surplus' : 'Deficit';
      eclssValEl.textContent = `O2: ${state.netO2KgDay.toFixed(2)} kg/d (${o2Status})`;
      eclssValEl.className = state.netO2KgDay >= 0 ? 'mc-value green' : 'mc-value red';

      const o2Pct = Math.min(100, Math.max(0, (state.oxygenStorageKg / 500.0) * 100));
      eclssBarEl.style.width = `${o2Pct}%`;
      eclssBarEl.className = state.netO2KgDay >= 0 ? 'mc-fill' : 'mc-fill amber';

      eclssSubEl.innerHTML = `
        <span>O2 Stored: <strong>${state.oxygenStorageKg.toFixed(1)} kg</strong></span>
        <span>H2O: <strong>${state.waterStorageL.toFixed(0)} L</strong></span>
        <span>Crew: <strong>${state.activeCrew}/${state.totalCrewCapacity}</strong></span>
      `;
    }

    // Radiation & Environmental Shielding
    const radValEl = document.getElementById('hudRadVal');
    const radBarEl = document.getElementById('hudRadBar');
    const radSubEl = document.getElementById('hudRadSub');
    if (radValEl && radBarEl && radSubEl) {
      const dose = state.avgRadiationDoseMsvYear;
      radValEl.textContent = `${dose.toFixed(1)} mSv/yr`;
      radValEl.className = dose <= 25.0 ? 'mc-value green' : (dose <= 60.0 ? 'mc-value amber' : 'mc-value red');

      const radSafetyPct = Math.min(100, Math.max(0, (1.0 - (dose / 700.0)) * 100));
      radBarEl.style.width = `${radSafetyPct}%`;
      radBarEl.className = dose <= 25.0 ? 'mc-fill' : (dose <= 60.0 ? 'mc-fill amber' : 'mc-fill red');

      radSubEl.innerHTML = `
        <span>Shielding: <strong>${(state.avgShieldFactor * 100).toFixed(0)}%</strong></span>
        <span>Unshielded Ref: <strong>700 mSv/yr</strong></span>
      `;
    }

    // Thermal Margin
    const thermValEl = document.getElementById('hudThermVal');
    const thermBarEl = document.getElementById('hudThermBar');
    const thermSubEl = document.getElementById('hudThermSub');
    if (thermValEl && thermBarEl && thermSubEl) {
      const thermMargin = state.thermalMarginKw;
      thermValEl.textContent = `${thermMargin >= 0 ? '+' : ''}${thermMargin.toFixed(1)} kW Dispersal`;
      thermValEl.className = thermMargin >= 0 ? 'mc-value green' : 'mc-value red';

      const thermPct = Math.min(100, Math.max(0, (state.totalHeatDissipationKw / Math.max(1, state.totalHeatGenKw)) * 100));
      thermBarEl.style.width = `${thermPct}%`;
      thermBarEl.className = thermMargin >= 0 ? 'mc-fill' : 'mc-fill red';

      thermSubEl.innerHTML = `
        <span>Dissipated: <strong>${state.totalHeatDissipationKw.toFixed(1)} kW</strong></span>
        <span>Internal Heat: <strong>${state.totalHeatGenKw.toFixed(1)} kW</strong></span>
      `;
    }

    // Scenario Objectives Checklist
    const objListEl = document.getElementById('objectivesList');
    if (objListEl) {
      objListEl.innerHTML = state.evaluatedObjectives.map(obj => `
        <div class="obj-item ${obj.passed ? 'passed' : 'failed'}">
          <div class="obj-check">${obj.passed ? '✓' : '○'}</div>
          <div>${obj.text}</div>
        </div>
      `).join('');
    }

    // Base Viability Score
    const scoreValEl = document.getElementById('survivalScoreVal');
    if (scoreValEl) {
      scoreValEl.textContent = `${state.survivalScore}%`;
      scoreValEl.className = state.survivalScore >= 80 ? 'mc-value green' : (state.survivalScore >= 50 ? 'mc-value amber' : 'mc-value red');
    }
  }

  openInspectorModal(x, y) {
    const existingModal = document.querySelector('.modal-backdrop');
    if (existingModal) existingModal.remove();

    const cell = this.engine.grid[y][x];
    if (!cell) {
      this.openEmptyCellModal(x, y);
      return;
    }

    const def = MODULE_TYPES[cell.typeId];
    if (!def) return;

    const modal = document.createElement('div');
    modal.className = 'modal-backdrop';
    modal.innerHTML = `
      <div class="modal-card">
        <div class="modal-head">
          <h3>${def.icon} ${def.name} (Grid ${x}, ${y})</h3>
          <button class="btn modal-close">✕ Close</button>
        </div>
        <div class="modal-body">
          <p style="color: #9AACBF; margin-bottom: 14px;">${def.description}</p>
          
          <div class="cutaway-diagram">
            <div style="font-size: 10px; color: #4FD1C5; text-transform: uppercase; margin-bottom: 6px;">
              Architectural Cutaway & Pressure Envelope
            </div>
            <svg class="cutaway-svg" viewBox="0 0 500 160">
              <!-- Lunar Surface Bed -->
              <rect x="0" y="110" width="500" height="50" fill="#172233" />
              <line x1="0" y1="110" x2="500" y2="110" stroke="#1E2C42" stroke-width="2" />
              
              <!-- Sintered Regolith Overburden / Arch -->
              <path d="M 120 110 Q 250 10 380 110" fill="none" stroke="#78716C" stroke-width="24" opacity="0.6" />
              
              <!-- Pressure Vessel Dome / Cylinder -->
              <path d="M 140 110 Q 250 25 360 110" fill="#142838" stroke="#4FD1C5" stroke-width="3" />
              
              <!-- Internal Floor & ECLSS Subfloor Plenums -->
              <line x1="150" y1="95" x2="350" y2="95" stroke="#60A5FA" stroke-width="2" stroke-dasharray="4,4" />
              <line x1="160" y1="80" x2="340" y2="80" stroke="#E8A33D" stroke-width="2" />
              
              <!-- Labels -->
              <text x="250" y="20" fill="#E8A33D" font-size="10" text-anchor="middle" font-family="'Oswald', sans-serif">2.5m SINTERED BASALT REGOLITH ARCH</text>
              <text x="250" y="65" fill="#DCE6F2" font-size="11" text-anchor="middle" font-family="'JetBrains Mono', monospace">101.3 kPa HABITAT VOLUME</text>
              <text x="250" y="105" fill="#6B7C93" font-size="9" text-anchor="middle">ECLSS PLENUM & CONDUITS</text>
              <text x="250" y="135" fill="#4B5563" font-size="10" text-anchor="middle">LUNAR REGOLITH SUBSTRATE</text>
            </svg>
          </div>

          <div class="spec-grid">
            <div class="spec-box"><div class="spec-k">Category</div><div class="spec-v">${def.category.toUpperCase()}</div></div>
            <div class="spec-box"><div class="spec-k">Launch Mass</div><div class="spec-v">${def.massKg.toLocaleString()} kg</div></div>
            <div class="spec-box"><div class="spec-k">Power Profile</div><div class="spec-v">${def.basePowerKw < 0 ? `Generates ${Math.abs(def.basePowerKw)} kW` : `Consumes ${def.basePowerKw || 0} kW`}</div></div>
            <div class="spec-box"><div class="spec-k">Thermal Output</div><div class="spec-v">${def.heatKw || 0} kW Heat</div></div>
            <div class="spec-box"><div class="spec-k">Crew Capacity</div><div class="spec-v">${def.crewCapacity || 0} Astronauts</div></div>
            <div class="spec-box"><div class="spec-k">Shielding Factor</div><div class="spec-v">${((def.shieldingFactor || 0) * 100).toFixed(0)}% GCR Protection</div></div>
          </div>

          <div style="margin-top: 14px; background: #0B1220; border: 1px solid #1E2C42; border-radius: 6px; padding: 10px 14px;">
            <div style="font-size: 10px; color: #E8A33D; text-transform: uppercase; margin-bottom: 4px;">Engineering Specifications</div>
            <ul style="padding-left: 18px; color: #8A9BB4; font-size: 11px;">
              ${Object.entries(def.specs || {}).map(([k, v]) => `<li><strong style="color:#DCE6F2">${k}:</strong> ${v}</li>`).join('')}
            </ul>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn danger" id="btnInspectDismantle">Dismantle Module (75% Salvage)</button>
          <button class="btn primary modal-close">Close Inspector</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    const dismantleBtn = modal.querySelector('#btnInspectDismantle');
    if (dismantleBtn) {
      dismantleBtn.addEventListener('click', () => {
        this.engine.removeModule(x, y);
        this.audio.playDemolish();
        this.updateHUD();
        modal.remove();
      });
    }
  }

  openEmptyCellModal(x, y) {
    const modal = document.createElement('div');
    modal.className = 'modal-backdrop';
    modal.innerHTML = `
      <div class="modal-card" style="width: 440px;">
        <div class="modal-head">
          <h3>Unoccupied Plot (${x}, ${y})</h3>
          <button class="btn modal-close">✕</button>
        </div>
        <div class="modal-body">
          <p style="color: #9AACBF;">This sector is clear regolith terrain. Select a module from the left palette to begin construction.</p>
        </div>
        <div class="modal-foot">
          <button class="btn primary modal-close">OK</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  }

  openFormulasModal() {
    const modal = document.createElement('div');
    modal.className = 'modal-backdrop';
    modal.innerHTML = `
      <div class="modal-card">
        <div class="modal-head">
          <h3>Lunar Physics & Engineering Derivations</h3>
          <button class="btn modal-close">✕ Close</button>
        </div>
        <div class="modal-body">
          <p style="color:#9AACBF; margin-bottom: 12px;">The Moonbase Architect physical simulation engine evaluates the following mathematical relations at every step:</p>
          
          <div class="math-block">
            <div class="formula-title">01 · Solar Irradiance & Diurnal Angle</div>
            <code>P_solar(t) = A_pv · η · S_0 · sin(θ_elevation(t))</code>
            <p style="font-size: 10px; color: #8A9BB4; margin-top: 4px;">Where S_0 = 1361 W/m² (Solar constant), η ≈ 34.2% (GaAs efficiency), and θ is the sun elevation over the 708.7h lunar day.</p>
          </div>

          <div class="math-block">
            <div class="formula-title">02 · Radiation Attenuation Through Regolith</div>
            <code>I(x) = I_0 · exp(-μ / ρ · ρ · x)</code>
            <p style="font-size: 10px; color: #8A9BB4; margin-top: 4px;">Unshielded lunar cosmic ray dose I_0 ≈ 700 mSv/yr. A 2.5m sintered regolith arch (ρ = 1.85 g/cm³) attenuates dose down to < 20 mSv/yr.</p>
          </div>

          <div class="math-block">
            <div class="formula-title">03 · Radiative Waste Heat Rejection (Stefan-Boltzmann)</div>
            <code>Q_rad = ε · σ · A_rad · (T_rad⁴ - T_sink⁴)</code>
            <p style="font-size: 10px; color: #8A9BB4; margin-top: 4px;">Rejecting internal electronics and fission reactor heat against the deep space radiation sink (T_sink ≈ 3 K).</p>
          </div>

          <div class="math-block">
            <div class="formula-title">04 · ECLSS Closed-Loop Mass Balance (Sabatier & Electrolysis)</div>
            <code>CO2 + 4H2 -> CH4 + 2H2O  (Sabatier Reduction)</code><br>
            <code>2H2O -> 2H2 + O2          (Water Electrolysis)</code>
            <p style="font-size: 10px; color: #8A9BB4; margin-top: 4px;">Human crew consumes 0.84 kg O2/day and exhales 1.00 kg CO2/day.</p>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn primary modal-close">Understood</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  }

  openExportModal() {
    const dossier = this.engine.exportDossier();
    const jsonStr = JSON.stringify(dossier, null, 2);

    const modal = document.createElement('div');
    modal.className = 'modal-backdrop';
    modal.innerHTML = `
      <div class="modal-card">
        <div class="modal-head">
          <h3>Moonbase Engineering Dossier Export</h3>
          <button class="btn modal-close">✕ Close</button>
        </div>
        <div class="modal-body">
          <p style="color:#9AACBF; margin-bottom: 8px;">Dossier manifest is verified and ready for export:</p>
          <textarea id="dossierJsonText" style="width: 100%; height: 200px; background: #070D18; border: 1px solid #1E2C42; color: #4FD1C5; font-family: 'JetBrains Mono', monospace; font-size: 11px; padding: 8px; border-radius: 6px;" readonly>${jsonStr}</textarea>
        </div>
        <div class="modal-foot">
          <button class="btn" id="btnCopyDossier">📋 Copy to Clipboard</button>
          <button class="btn primary modal-close">Done</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    const copyBtn = modal.querySelector('#btnCopyDossier');
    if (copyBtn) {
      copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(jsonStr).then(() => {
          copyBtn.textContent = '✓ Copied!';
          setTimeout(() => copyBtn.textContent = '📋 Copy to Clipboard', 2000);
        });
      });
    }
  }

  renderLoop(currentTime = performance.now()) {
    const deltaSeconds = (currentTime - this.lastTime) / 1000.0;
    this.lastTime = currentTime;

    // Convert seconds to simulation hours: 1 real second = 0.5 simulation hour
    const deltaSimHours = deltaSeconds * 0.5;
    this.engine.step(deltaSimHours);

    this.renderer.render(currentTime);
    this.updateHUD();

    requestAnimationFrame((t) => this.renderLoop(t));
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.moonbaseApp = new MoonbaseApp();
});
