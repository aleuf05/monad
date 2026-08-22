/**
 * Monad Education 001 — Moonbase Architect v0.1
 * Tactical Canvas & Surface Rendering Engine
 */

import { MODULE_TYPES, LUNAR_CONSTANTS } from './engine.js';

export class MoonbaseRenderer {
  constructor(canvas, engine) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.engine = engine;

    this.overlayMode = 'tactical'; // 'tactical' | 'radiation' | 'thermal' | 'power' | 'stress'
    this.selectedCell = null;
    this.hoverCell = null;
    this.selectedTool = null;

    this.animationPhase = 0.0;
    this.cellSize = 48;
    this.offsetX = 0;
    this.offsetY = 0;

    this.initCanvas();
  }

  initCanvas() {
    this.resize();
    window.addEventListener('resize', () => this.resize());
  }

  resize() {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = rect.width * dpr;
    this.canvas.height = Math.max(480, Math.min(650, window.innerHeight * 0.58)) * dpr;
    this.canvas.style.width = `${rect.width}px`;
    this.canvas.style.height = `${this.canvas.height / dpr}px`;
    this.ctx.scale(dpr, dpr);

    this.width = rect.width;
    this.height = this.canvas.height / dpr;

    // Center grid
    const totalGridWidth = this.engine.gridWidth * this.cellSize;
    const totalGridHeight = this.engine.gridHeight * this.cellSize;
    this.offsetX = Math.max(20, (this.width - totalGridWidth) / 2);
    this.offsetY = Math.max(20, (this.height - totalGridHeight) / 2);
  }

  screenToGrid(screenX, screenY) {
    const gx = Math.floor((screenX - this.offsetX) / this.cellSize);
    const gy = Math.floor((screenY - this.offsetY) / this.cellSize);
    if (gx >= 0 && gx < this.engine.gridWidth && gy >= 0 && gy < this.engine.gridHeight) {
      return { x: gx, y: gy };
    }
    return null;
  }

  render(timestamp) {
    this.animationPhase = (timestamp / 1000.0);
    const ctx = this.ctx;
    const w = this.width;
    const h = this.height;

    const state = this.engine.calculateState();
    const solarFactor = state.solarFactor;
    const isDay = state.isDay;

    // 1. Render Sky & Stars
    ctx.clearRect(0, 0, w, h);
    this.drawSky(ctx, w, h, solarFactor);

    // 2. Render Lunar Terrain Background
    this.drawLunarTerrain(ctx, w, h, solarFactor);

    // 3. Render Grid & Base Foundations
    this.drawGrid(ctx, solarFactor);

    // 4. Render Power Conduits & Resource Lines
    this.drawResourceConduits(ctx);

    // 5. Render Placed Modules
    this.drawModules(ctx, solarFactor);

    // 6. Render Overlays (Radiation, Thermal, Power, Stress)
    if (this.overlayMode !== 'tactical') {
      this.drawOverlays(ctx, state);
    }

    // 7. Render Placement Cursor & Selection Highlights
    this.drawInteractiveHighlights(ctx);

    // 8. Render Tactical HUD Compass & Lighting Indicator
    this.drawTacticalLightingIndicator(ctx, solarFactor, isDay);
  }

  drawSky(ctx, w, h, solarFactor) {
    // Sky background gradient
    const skyGrad = ctx.createLinearGradient(0, 0, 0, h);
    if (solarFactor > 0.1) {
      skyGrad.addColorStop(0, '#030712');
      skyGrad.addColorStop(0.6, '#0B1322');
      skyGrad.addColorStop(1, '#111D30');
    } else {
      skyGrad.addColorStop(0, '#010307');
      skyGrad.addColorStop(1, '#050A14');
    }
    ctx.fillStyle = skyGrad;
    ctx.fillRect(0, 0, w, h);

    // Static crisp stars
    ctx.fillStyle = '#FFFFFF';
    const starCount = 45;
    for (let i = 0; i < starCount; i++) {
      const sx = ((i * 137.5) % w);
      const sy = ((i * 79.3) % (h * 0.45));
      const size = (i % 3 === 0) ? 1.5 : 1.0;
      const alpha = (0.3 + 0.7 * Math.sin(this.animationPhase * 1.5 + i));
      ctx.globalAlpha = alpha;
      ctx.fillRect(sx, sy, size, size);
    }
    ctx.globalAlpha = 1.0;

    // Earth in the sky (Crescent / Blue Marble)
    const earthX = w - 60;
    const earthY = 45;
    const earthRadius = 18;

    const earthGrad = ctx.createRadialGradient(earthX - 4, earthY - 4, 3, earthX, earthY, earthRadius);
    earthGrad.addColorStop(0, '#60A5FA');
    earthGrad.addColorStop(0.7, '#1E40AF');
    earthGrad.addColorStop(1, '#0F172A');

    ctx.save();
    ctx.beginPath();
    ctx.arc(earthX, earthY, earthRadius, 0, Math.PI * 2);
    ctx.fillStyle = earthGrad;
    ctx.fill();

    // Atmosphere halo
    ctx.strokeStyle = 'rgba(96, 165, 250, 0.4)';
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.restore();
  }

  drawLunarTerrain(ctx, w, h, solarFactor) {
    const gw = this.engine.gridWidth * this.cellSize;
    const gh = this.engine.gridHeight * this.cellSize;
    const gx = this.offsetX;
    const gy = this.offsetY;

    // Regolith field base
    ctx.save();
    const terrainGrad = ctx.createLinearGradient(gx, gy, gx, gy + gh);
    const dayLum = Math.floor(35 + solarFactor * 45);
    const nightLum = 18;
    const currentLum = isNaN(dayLum) ? nightLum : dayLum;

    terrainGrad.addColorStop(0, `rgb(${currentLum}, ${currentLum + 4}, ${currentLum + 10})`);
    terrainGrad.addColorStop(1, `rgb(${currentLum - 10}, ${currentLum - 7}, ${currentLum})`);

    ctx.fillStyle = terrainGrad;
    ctx.beginPath();
    ctx.roundRect(gx - 12, gy - 12, gw + 24, gh + 24, 12);
    ctx.fill();
    ctx.strokeStyle = '#1E2C42';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Crater textures & ridges
    ctx.fillStyle = 'rgba(0, 0, 0, 0.25)';
    const craters = [
      { x: gx + 35, y: gy + 45, r: 18 },
      { x: gx + gw - 40, y: gy + 60, r: 24 },
      { x: gx + 50, y: gy + gh - 40, r: 28 },
      { x: gx + gw - 65, y: gy + gh - 45, r: 16 }
    ];

    for (const c of craters) {
      ctx.beginPath();
      ctx.ellipse(c.x, c.y, c.r, c.r * 0.65, 0, 0, Math.PI * 2);
      ctx.fill();
      // Sunlit rim highlight
      if (solarFactor > 0.1) {
        ctx.strokeStyle = `rgba(220, 230, 242, ${0.15 + solarFactor * 0.25})`;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(c.x, c.y, c.r, Math.PI * 1.1, Math.PI * 1.9);
        ctx.stroke();
      }
    }
    ctx.restore();
  }

  drawGrid(ctx, solarFactor) {
    const gw = this.engine.gridWidth * this.cellSize;
    const gh = this.engine.gridHeight * this.cellSize;
    const gx = this.offsetX;
    const gy = this.offsetY;

    ctx.save();
    ctx.strokeStyle = 'rgba(79, 209, 197, 0.12)';
    ctx.lineWidth = 1;

    for (let x = 0; x <= this.engine.gridWidth; x++) {
      const px = gx + x * this.cellSize;
      ctx.beginPath();
      ctx.moveTo(px, gy);
      ctx.lineTo(px, gy + gh);
      ctx.stroke();
    }

    for (let y = 0; y <= this.engine.gridHeight; y++) {
      const py = gy + y * this.cellSize;
      ctx.beginPath();
      ctx.moveTo(gx, py);
      ctx.lineTo(gx + gw, py);
      ctx.stroke();
    }
    ctx.restore();
  }

  drawResourceConduits(ctx) {
    const modules = this.engine.getPlacedModules();
    if (modules.length < 2) return;

    ctx.save();
    // Connect adjacent modules with animated energy flow
    const pulseOffset = (this.animationPhase * 24) % 12;

    for (let i = 0; i < modules.length; i++) {
      for (let j = i + 1; j < modules.length; j++) {
        const m1 = modules[i];
        const m2 = modules[j];
        const dx = Math.abs(m1.x - m2.x);
        const dy = Math.abs(m1.y - m2.y);

        if ((dx === 1 && dy === 0) || (dx === 0 && dy === 1)) {
          const x1 = this.offsetX + (m1.x + 0.5) * this.cellSize;
          const y1 = this.offsetY + (m1.y + 0.5) * this.cellSize;
          const x2 = this.offsetX + (m2.x + 0.5) * this.cellSize;
          const y2 = this.offsetY + (m2.y + 0.5) * this.cellSize;

          // Conduit backing
          ctx.strokeStyle = '#1E2C42';
          ctx.lineWidth = 4;
          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.stroke();

          // Active glowing core
          ctx.strokeStyle = '#4FD1C5';
          ctx.lineWidth = 1.5;
          ctx.setLineDash([4, 8]);
          ctx.lineDashOffset = -pulseOffset;
          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.stroke();
        }
      }
    }
    ctx.restore();
  }

  drawModules(ctx, solarFactor) {
    const modules = this.engine.getPlacedModules();

    for (const m of modules) {
      const def = MODULE_TYPES[m.typeId];
      if (!def) continue;

      const cx = this.offsetX + m.x * this.cellSize;
      const cy = this.offsetY + m.y * this.cellSize;
      const pad = 4;
      const size = this.cellSize - pad * 2;

      ctx.save();

      // Shadow cast by module
      if (solarFactor > 0.05) {
        const shadowLen = (1.0 - Math.min(1.0, solarFactor)) * 12 + 4;
        ctx.fillStyle = 'rgba(5, 10, 20, 0.6)';
        ctx.beginPath();
        ctx.ellipse(cx + size / 2 + shadowLen, cy + size / 2 + shadowLen * 0.5, size * 0.45, size * 0.3, 0, 0, Math.PI * 2);
        ctx.fill();
      }

      // Module background tile
      let bgColor = '#111A2B';
      let borderColor = '#1E2C42';

      switch (def.category) {
        case 'command':
          bgColor = '#142838';
          borderColor = '#4FD1C5';
          break;
        case 'habitat':
          bgColor = '#1A2740';
          borderColor = '#60A5FA';
          break;
        case 'life-support':
          bgColor = '#132C26';
          borderColor = '#34D399';
          break;
        case 'power':
          bgColor = '#2B2312';
          borderColor = '#F59E0B';
          break;
        case 'shielding':
          bgColor = '#292524';
          borderColor = '#78716C';
          break;
        case 'isru':
          bgColor = '#1E1B4B';
          borderColor = '#818CF8';
          break;
        case 'thermal':
          bgColor = '#2A1728';
          borderColor = '#F472B6';
          break;
        case 'utility':
          bgColor = '#172554';
          borderColor = '#38BDF8';
          break;
      }

      ctx.fillStyle = bgColor;
      ctx.beginPath();
      ctx.roundRect(cx + pad, cy + pad, size, size, 6);
      ctx.fill();

      ctx.strokeStyle = borderColor;
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Module Emoji Icon & Label
      ctx.font = '18px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(def.icon || '📦', cx + this.cellSize / 2, cy + this.cellSize / 2 - 2);

      // Micro status badge
      ctx.font = '8px "Oswald", sans-serif';
      ctx.fillStyle = borderColor;
      ctx.fillText(def.id.toUpperCase().split('-')[0], cx + this.cellSize / 2, cy + this.cellSize - 7);

      ctx.restore();
    }
  }

  drawOverlays(ctx, state) {
    const modules = this.engine.getPlacedModules();

    for (const m of modules) {
      const def = MODULE_TYPES[m.typeId];
      if (!def) continue;

      const cx = this.offsetX + m.x * this.cellSize;
      const cy = this.offsetY + m.y * this.cellSize;
      const size = this.cellSize;

      ctx.save();
      ctx.globalAlpha = 0.55;

      if (this.overlayMode === 'radiation') {
        // High dose = Red, Shielded = Green/Blue
        const isShielded = def.category === 'shielding' || def.shieldingFactor > 0.8;
        ctx.fillStyle = isShielded ? 'rgba(52, 211, 153, 0.4)' : 'rgba(239, 68, 68, 0.5)';
        ctx.fillRect(cx, cy, size, size);
      } else if (this.overlayMode === 'thermal') {
        // Hot = Orange/Red, Cool = Cyan
        const isHot = (def.heatKw || 0) > 10;
        const isCooler = def.category === 'thermal';
        ctx.fillStyle = isCooler ? 'rgba(56, 189, 248, 0.5)' : (isHot ? 'rgba(249, 115, 22, 0.5)' : 'rgba(168, 85, 247, 0.3)');
        ctx.fillRect(cx, cy, size, size);
      } else if (this.overlayMode === 'power') {
        // Generator = Gold, Consumer = Teal
        const isGen = (def.basePowerKw < 0) || def.peakPowerKw;
        ctx.fillStyle = isGen ? 'rgba(245, 158, 11, 0.5)' : 'rgba(45, 212, 191, 0.4)';
        ctx.fillRect(cx, cy, size, size);
      } else if (this.overlayMode === 'stress') {
        // Pressure vessel stress factor
        const isPressurized = def.pressureKpa > 0;
        ctx.fillStyle = isPressurized ? 'rgba(96, 165, 250, 0.4)' : 'rgba(107, 114, 128, 0.3)';
        ctx.fillRect(cx, cy, size, size);
      }

      ctx.restore();
    }
  }

  drawInteractiveHighlights(ctx) {
    const gx = this.offsetX;
    const gy = this.offsetY;

    // 1. Hover Cell / Tool Preview
    if (this.hoverCell) {
      const hx = gx + this.hoverCell.x * this.cellSize;
      const hy = gy + this.hoverCell.y * this.cellSize;

      ctx.save();
      if (this.selectedTool === 'demolish') {
        ctx.strokeStyle = '#EF4444';
        ctx.fillStyle = 'rgba(239, 68, 68, 0.2)';
      } else if (this.selectedTool && MODULE_TYPES[this.selectedTool]) {
        ctx.strokeStyle = '#4FD1C5';
        ctx.fillStyle = 'rgba(79, 209, 197, 0.18)';
      } else {
        ctx.strokeStyle = 'rgba(220, 230, 242, 0.4)';
        ctx.fillStyle = 'rgba(255, 255, 255, 0.05)';
      }

      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.roundRect(hx + 2, hy + 2, this.cellSize - 4, this.cellSize - 4, 4);
      ctx.fill();
      ctx.stroke();

      // If placing a tool, render transparent ghost icon
      if (this.selectedTool && MODULE_TYPES[this.selectedTool]) {
        const def = MODULE_TYPES[this.selectedTool];
        ctx.font = '16px "JetBrains Mono", monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(def.icon, hx + this.cellSize / 2, hy + this.cellSize / 2);
      }
      ctx.restore();
    }

    // 2. Selected Cell (for Inspection)
    if (this.selectedCell) {
      const sx = gx + this.selectedCell.x * this.cellSize;
      const sy = gy + this.selectedCell.y * this.cellSize;

      ctx.save();
      ctx.strokeStyle = '#E8A33D';
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.roundRect(sx + 1, sy + 1, this.cellSize - 2, this.cellSize - 2, 6);
      ctx.stroke();

      // Corner accent markers
      const sz = 6;
      ctx.fillStyle = '#E8A33D';
      ctx.fillRect(sx, sy, sz, 2);
      ctx.fillRect(sx, sy, 2, sz);
      ctx.fillRect(sx + this.cellSize - sz, sy, sz, 2);
      ctx.fillRect(sx + this.cellSize - 2, sy, 2, sz);
      ctx.fillRect(sx, sy + this.cellSize - 2, sz, 2);
      ctx.fillRect(sx, sy + this.cellSize - sz, 2, sz);
      ctx.fillRect(sx + this.cellSize - sz, sy + this.cellSize - 2, sz, 2);
      ctx.fillRect(sx + this.cellSize - 2, sy + this.cellSize - sz, 2, sz);
      ctx.restore();
    }
  }

  drawTacticalLightingIndicator(ctx, solarFactor, isDay) {
    ctx.save();
    const cx = 35;
    const cy = 35;
    const radius = 16;

    // Sun / Moon status circle
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.fillStyle = isDay ? 'rgba(245, 158, 11, 0.2)' : 'rgba(59, 130, 246, 0.2)';
    ctx.fill();
    ctx.strokeStyle = isDay ? '#F59E0B' : '#3B82F6';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    ctx.font = '12px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(isDay ? '☀️' : '🌑', cx, cy);

    // Diurnal percentage readout
    ctx.font = '10px "Oswald", sans-serif';
    ctx.fillStyle = '#DCE6F2';
    ctx.textAlign = 'left';
    ctx.fillText(isDay ? 'LUNAR DAY' : 'LUNAR NIGHT', cx + radius + 8, cy - 3);

    ctx.font = '9px "JetBrains Mono", monospace';
    ctx.fillStyle = '#6B7C93';
    ctx.fillText(`FLUX: ${(solarFactor * 100).toFixed(0)}%`, cx + radius + 8, cy + 9);
    ctx.restore();
  }
}
