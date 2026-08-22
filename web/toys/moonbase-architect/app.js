/**
 * Moonbase Architect v0.1
 * UI Controller & Interaction Controller
 */

import { MoonbaseMathEngine, MISSIONS } from './engine.js';
import { MoonbaseCanvasRenderer } from './renderer.js';
import { MoonbaseAudio } from './sound.js';

class MoonbaseApp {
  constructor() {
    this.engine = new MoonbaseMathEngine();
    this.audio = new MoonbaseAudio();

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
        badgeEl.textContent = '★ RECORD!';
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
    if (ipAreaFormula) ipAreaFormula.textContent = `${calc.width} × ${calc.length} = ${calc.area}`;

    // 3. Outside Wall / Perimeter
    const ipPerimeter = document.getElementById('ipPerimeter');
    const ipPerimeterFormula = document.getElementById('ipPerimeterFormula');
    if (ipPerimeter) ipPerimeter.textContent = `${calc.perimeter} m`;
    if (ipPerimeterFormula) ipPerimeterFormula.textContent = `2(${calc.width} + ${calc.length})`;

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
        stampsList.innerHTML = '<span style="color:#6B7C93; font-size:10px;">Find solutions to unlock stamps!</span>';
      }
    }

    // Sound & Celebrations
    if (calc.isOptimalRecord && !this.lastCelebratedRecord) {
      this.audio.playRecordFanfare();
      this.renderer.triggerCelebration();
      this.lastCelebratedRecord = true;
    } else if (calc.missionPassed && !this.lastCelebratedRecord) {
      this.audio.playSuccess();
      this.renderer.triggerCelebration();
    } else if (!calc.missionPassed) {
      this.lastCelebratedRecord = false;
    }

    this.updateMissionBanner();
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
        this.renderMissionTabs();
        this.updateMissionBanner();
        this.updateInstrumentPanel();
        this.audio.playClick();
      });
    }

    // 2. Width Stepper Buttons & Slider
    const btnWidthDec = document.getElementById('btnWidthDec');
    const btnWidthInc = document.getElementById('btnWidthInc');
    const sliderWidth = document.getElementById('sliderWidth');

    if (btnWidthDec) {
      btnWidthDec.addEventListener('click', () => {
        const res = this.engine.setWidth(this.engine.width - 1);
        if (res.changed) {
          this.audio.playStep();
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
          this.updateControls();
          this.updateInstrumentPanel(res.maraReaction);
        }
      });
    }

    // 3. Length Stepper Buttons & Slider
    const btnLengthDec = document.getElementById('btnLengthDec');
    const btnLengthInc = document.getElementById('btnLengthInc');
    const sliderLength = document.getElementById('sliderLength');

    if (btnLengthDec) {
      btnLengthDec.addEventListener('click', () => {
        const res = this.engine.setLength(this.engine.length - 1);
        if (res.changed) {
          this.audio.playStep();
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
          this.updateControls();
          this.updateInstrumentPanel(res.maraReaction);
        }
      });
    }

    // 4. Direct Canvas Manipulation / Drag Handle
    const canvas = this.canvas;

    const handlePointerDown = (clientX, clientY) => {
      const rect = canvas.getBoundingClientRect();
      const sx = clientX - rect.left;
      const sy = clientY - rect.top;

      const handles = this.renderer.getHandleBounds();
      const distCorner = Math.hypot(sx - handles.corner.x, sy - handles.corner.y);

      if (distCorner <= 24) {
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
        this.updateControls();
        this.updateInstrumentPanel(res.maraReaction);
      }
    };

    const handlePointerUp = () => {
      this.renderer.isDragging = false;
      this.renderer.dragTarget = null;
    };

    // Mouse Events
    canvas.addEventListener('mousedown', (e) => handlePointerDown(e.clientX, e.clientY));
    window.addEventListener('mousemove', (e) => handlePointerMove(e.clientX, e.clientY));
    window.addEventListener('mouseup', handlePointerUp);

    // Touch Events
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

    // 5. Sound Toggle
    const btnMute = document.getElementById('btnMute');
    if (btnMute) {
      btnMute.addEventListener('click', () => {
        this.audio.isMuted = !this.audio.isMuted;
        btnMute.textContent = this.audio.isMuted ? '🔇 Sound Off' : '🔊 Sound On';
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
