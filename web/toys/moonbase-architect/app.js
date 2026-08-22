/**
 * Moonbase Architect v0.1
 * UI Controller & Interaction Orchestrator
 */

import { MoonbaseMathEngine, MISSIONS } from './engine.js';
import { MoonbaseCanvasRenderer } from './renderer.js';
import { MoonbaseAudio } from './sound.js';
import { MoonbaseTelemetry } from './telemetry.js';

class MoonbaseApp {
  constructor() {
    this.engine = new MoonbaseMathEngine();
    this.audio = new MoonbaseAudio();
    this.telemetry = new MoonbaseTelemetry();

    this.canvas = document.getElementById('lunarCanvas');
    this.renderer = new MoonbaseCanvasRenderer(this.canvas, this.engine);

    this.lastCelebratedRecord = false;

    this.initUI();
    this.bindEvents();
    this.renderLoop();
  }

  initUI() {
    this.renderMissionTabs();
    this.updateMissionBanner();
    this.updateControls();
    this.updateInstrumentPanel();
  }

  renderMissionTabs() {
    const ribbon = document.getElementById('missionRibbon');
    if (!ribbon) return;

    ribbon.innerHTML = MISSIONS.map((m, idx) => `
      <button class="mission-tab ${idx === this.engine.currentMissionIndex ? 'active' : ''}" data-mission-index="${idx}">
        ${m.title}
      </button>
    `).join('');
  }

  updateMissionBanner() {
    const m = this.engine.getCurrentMission();
    const titleEl = document.getElementById('promptTitle');
    const subEl = document.getElementById('promptSub');
    const badgeEl = document.getElementById('promptBadge');

    if (titleEl) titleEl.textContent = m.prompt;
    if (subEl) subEl.textContent = m.subtext;

    const calc = this.engine.getCalculations();
    if (badgeEl) {
      if (calc.isOptimalRecord) {
        badgeEl.textContent = '★ ENGINEERING RECORD!';
        badgeEl.hidden = false;
      } else if (calc.missionPassed) {
        badgeEl.textContent = '✓ SOLVED!';
        badgeEl.hidden = false;
      } else {
        badgeEl.hidden = true;
      }
    }
  }

  updateControls() {
    const wVal = document.getElementById('valWidth');
    const lVal = document.getElementById('valLength');
    const wSlider = document.getElementById('sliderWidth');
    const lSlider = document.getElementById('sliderLength');

    if (wVal) wVal.textContent = `${this.engine.width} m`;
    if (lVal) lVal.textContent = `${this.engine.length} m`;
    if (wSlider) wSlider.value = this.engine.width;
    if (lSlider) lSlider.value = this.engine.length;
  }

  updateInstrumentPanel(maraMessage = null) {
    const calc = this.engine.getCalculations();

    // 1. Width / Length
    const ipWidth = document.getElementById('ipWidth');
    const ipLength = document.getElementById('ipLength');
    if (ipWidth) ipWidth.textContent = `${calc.width} m`;
    if (ipLength) ipLength.textContent = `${calc.length} m`;

    // 2. Floor Tiles / Area
    const ipArea = document.getElementById('ipArea');
    const ipAreaFormula = document.getElementById('ipAreaFormula');
    if (ipArea) ipArea.textContent = `${calc.area} tiles`;
    if (ipAreaFormula) ipAreaFormula.textContent = `area = ${calc.width} × ${calc.length} = ${calc.area}`;

    // 3. Outside Wall / Perimeter
    const ipPerimeter = document.getElementById('ipPerimeter');
    const ipPerimeterFormula = document.getElementById('ipPerimeterFormula');
    if (ipPerimeter) ipPerimeter.textContent = `${calc.perimeter} m`;
    if (ipPerimeterFormula) ipPerimeterFormula.textContent = `perimeter = 2 × (${calc.width} + ${calc.length}) = ${calc.perimeter}`;

    // 4. Shielding Cost
    const ipCost = document.getElementById('ipCost');
    if (ipCost) ipCost.textContent = `$${calc.shieldingCost.toLocaleString()}`;

    // 5. MARA Assistant Feedback
    const maraSpeech = document.getElementById('maraSpeech');
    if (maraSpeech) {
      if (maraMessage) {
        maraSpeech.textContent = maraMessage;
      } else {
        maraSpeech.textContent = this.engine.evaluateMaraReaction(calc.width, calc.length);
      }
    }

    // 6. Factor Stamps Rack
    const stampsList = document.getElementById('stampsList');
    if (stampsList) {
      if (calc.discoveredPairs.length > 0) {
        stampsList.innerHTML = calc.discoveredPairs.map(p => `
          <div class="factor-stamp">${p} = 48</div>
        `).join('');
      } else {
        stampsList.innerHTML = '<span style="color:#6B7C93; font-size:10px;">Find solutions to unlock factor stamps!</span>';
      }
    }

    // Telemetry tracking
    this.telemetry.recordDimensionAttempt(calc.mission.id, calc.width, calc.length, calc.area, calc.perimeter);

    // Audio & Celebrations
    if (calc.isOptimalRecord && !this.lastCelebratedRecord) {
      this.audio.playRecordFanfare();
      this.renderer.triggerCelebration();
      this.telemetry.recordSolution(calc.mission.id, calc.width, calc.length, true);
      this.lastCelebratedRecord = true;
    } else if (calc.missionPassed && !this.lastCelebratedRecord) {
      this.audio.playSuccess();
      this.renderer.triggerCelebration();
      this.telemetry.recordSolution(calc.mission.id, calc.width, calc.length, false);
    } else if (!calc.missionPassed) {
      this.lastCelebratedRecord = false;
    }

    this.updateMissionBanner();
  }

  resetCurrentMission() {
    this.engine.width = 6;
    this.engine.length = 8;
    this.lastCelebratedRecord = false;
    this.renderer.notifyDimensionChange();
    this.telemetry.recordReset(this.engine.getCurrentMission().id);
    this.updateControls();
    this.updateInstrumentPanel('“Mission reset! Adjust the width and length to begin.”');
    this.audio.playClick();
  }

  bindEvents() {
    // 1. Mission Tab Switching
    const ribbon = document.getElementById('missionRibbon');
    if (ribbon) {
      ribbon.addEventListener('click', (e) => {
        const tab = e.target.closest('.mission-tab');
        if (!tab) return;
        const idx = parseInt(tab.getAttribute('data-mission-index'), 10);
        this.engine.currentMissionIndex = idx;
        this.telemetry.recordEvent('mission_selected', { missionId: MISSIONS[idx].id });
        this.renderMissionTabs();
        this.updateMissionBanner();
        this.updateInstrumentPanel();
        this.audio.playClick();
      });
    }

    // 2. Reset Mission Button
    const btnReset = document.getElementById('btnResetMission');
    if (btnReset) {
      btnReset.addEventListener('click', () => this.resetCurrentMission());
    }

    // 3. Width Stepper Buttons & Slider
    const btnWidthDec = document.getElementById('btnWidthDec');
    const btnWidthInc = document.getElementById('btnWidthInc');
    const sliderWidth = document.getElementById('sliderWidth');

    if (btnWidthDec) {
      btnWidthDec.addEventListener('click', () => {
        const res = this.engine.setWidth(this.engine.width - 1);
        if (res.changed) {
          this.audio.playStep();
          this.renderer.notifyDimensionChange();
          this.updateControls();
          this.updateInstrumentPanel(res.maraReaction);
        }
      });
    }

    if (btnWidthInc) {
      btnWidthInc.addEventListener('click', () => {
        const res = this.engine.setWidth(this.engine.width + 1);
        if (res.changed) {
          this.audio.playStep();
          this.renderer.notifyDimensionChange();
          this.updateControls();
          this.updateInstrumentPanel(res.maraReaction);
        }
      });
    }

    if (sliderWidth) {
      sliderWidth.addEventListener('input', (e) => {
        const val = parseInt(e.target.value, 10);
        const res = this.engine.setWidth(val);
        if (res.changed) {
          this.audio.playStep();
          this.renderer.notifyDimensionChange();
          this.updateControls();
          this.updateInstrumentPanel(res.maraReaction);
        }
      });
    }

    // 4. Length Stepper Buttons & Slider
    const btnLengthDec = document.getElementById('btnLengthDec');
    const btnLengthInc = document.getElementById('btnLengthInc');
    const sliderLength = document.getElementById('sliderLength');

    if (btnLengthDec) {
      btnLengthDec.addEventListener('click', () => {
        const res = this.engine.setLength(this.engine.length - 1);
        if (res.changed) {
          this.audio.playStep();
          this.renderer.notifyDimensionChange();
          this.updateControls();
          this.updateInstrumentPanel(res.maraReaction);
        }
      });
    }

    if (btnLengthInc) {
      btnLengthInc.addEventListener('click', () => {
        const res = this.engine.setLength(this.engine.length + 1);
        if (res.changed) {
          this.audio.playStep();
          this.renderer.notifyDimensionChange();
          this.updateControls();
          this.updateInstrumentPanel(res.maraReaction);
        }
      });
    }

    if (sliderLength) {
      sliderLength.addEventListener('input', (e) => {
        const val = parseInt(e.target.value, 10);
        const res = this.engine.setLength(val);
        if (res.changed) {
          this.audio.playStep();
          this.renderer.notifyDimensionChange();
          this.updateControls();
          this.updateInstrumentPanel(res.maraReaction);
        }
      });
    }

    // 5. Canvas Direct Touch/Mouse Drag Manipulation
    const canvas = this.canvas;

    const handlePointerDown = (clientX, clientY) => {
      const rect = canvas.getBoundingClientRect();
      const sx = clientX - rect.left;
      const sy = clientY - rect.top;

      const handles = this.renderer.getHandleBounds();
      const distCorner = Math.hypot(sx - handles.corner.x, sy - handles.corner.y);

      if (distCorner <= 28) {
        this.renderer.isDragging = true;
        this.renderer.dragTarget = 'handle-corner';
      }
    };

    const handlePointerMove = (clientX, clientY) => {
      if (!this.renderer.isDragging) return;

      const rect = canvas.getBoundingClientRect();
      const sx = clientX - rect.left;
      const sy = clientY - rect.top;

      const dims = this.renderer.screenToDimensions(sx, sy);
      const res = this.engine.setDimensions(dims.w, dims.l);
      if (res.changed) {
        this.audio.playStep();
        this.renderer.notifyDimensionChange();
        this.updateControls();
        this.updateInstrumentPanel(res.maraReaction);
      }
    };

    const handlePointerUp = () => {
      this.renderer.isDragging = false;
      this.renderer.dragTarget = null;
    };

    canvas.addEventListener('mousedown', (e) => handlePointerDown(e.clientX, e.clientY));
    window.addEventListener('mousemove', (e) => handlePointerMove(e.clientX, e.clientY));
    window.addEventListener('mouseup', handlePointerUp);

    canvas.addEventListener('touchstart', (e) => {
      if (e.touches.length > 0) {
        handlePointerDown(e.touches[0].clientX, e.touches[0].clientY);
      }
    }, { passive: true });

    window.addEventListener('touchmove', (e) => {
      if (e.touches.length > 0) {
        handlePointerMove(e.touches[0].clientX, e.touches[0].clientY);
      }
    }, { passive: true });

    window.addEventListener('touchend', handlePointerUp);

    // 6. Sound Toggle
    const btnMute = document.getElementById('btnMute');
    if (btnMute) {
      btnMute.addEventListener('click', () => {
        this.audio.isMuted = !this.audio.isMuted;
        btnMute.textContent = this.audio.isMuted ? '🔇 Sound Off' : '🔊 Sound On';
      });
    }

    // 7. Telemetry Inspector Modal
    const btnTelemetry = document.getElementById('btnTelemetry');
    if (btnTelemetry) {
      btnTelemetry.addEventListener('click', () => this.openTelemetryModal());
    }

    document.addEventListener('click', (e) => {
      if (e.target.matches('.modal-close') || e.target.matches('.modal-backdrop')) {
        document.querySelectorAll('.modal-backdrop').forEach(m => m.remove());
      }
    });
  }

  openTelemetryModal() {
    const logs = this.telemetry.getLogs();
    const jsonStr = JSON.stringify(logs, null, 2);

    const modal = document.createElement('div');
    modal.className = 'modal-backdrop';
    modal.innerHTML = `
      <div class="modal-card" style="width: min(700px, 94vw); background: #0E1626; border: 1px solid #1E2C42; border-radius: 10px; padding: 20px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 12px;">
          <h3 style="font-family:'Oswald',sans-serif; color:#F6C76D; text-transform:uppercase;">Local Test Instrumentation Logs</h3>
          <button class="btn modal-close">✕</button>
        </div>
        <p style="font-size:11px; color:#8A9BB4; margin-bottom:8px;">Lightweight interaction telemetry stored in browser localStorage:</p>
        <textarea style="width:100%; height:260px; background:#070D18; border:1px solid #1E2C42; color:#4FD1C5; font-family:'JetBrains Mono',monospace; font-size:10.5px; padding:10px; border-radius:6px;" readonly>${jsonStr}</textarea>
        <div style="display:flex; justify-content:space-between; margin-top:14px;">
          <button class="btn danger" id="btnClearTelemetry">Clear Logs</button>
          <button class="btn primary modal-close">Close</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    const clearBtn = modal.querySelector('#btnClearTelemetry');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        this.telemetry.clearLogs();
        modal.remove();
      });
    }
  }

  renderLoop(timestamp = performance.now()) {
    this.renderer.render(timestamp);
    requestAnimationFrame((t) => this.renderLoop(t));
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.moonbaseApp = new MoonbaseApp();
});
