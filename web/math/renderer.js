/**
 * Moonbase Architect v0.1
 * Tactical Lunar Canvas Renderer & Direct Manipulation System
 */

export class MoonbaseCanvasRenderer {
  constructor(canvas, mathEngine) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.engine = mathEngine;

    this.isDragging = false;
    this.dragTarget = null;

    this.particles = [];
    this.animationPhase = 0.0;
    this.lastWidth = mathEngine.width;
    this.lastLength = mathEngine.length;
    this.constructionGlow = 0.0;

    this.gridOriginX = 0;
    this.gridOriginY = 0;
    this.tileSize = 24;

    this.init();
  }

  init() {
    this.resize();
    window.addEventListener('resize', () => this.resize());
  }

  resize() {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const width = rect.width;
    const height = Math.max(420, Math.min(580, window.innerHeight * 0.52));

    this.canvas.width = width * dpr;
    this.canvas.height = height * dpr;
    this.canvas.style.width = `${width}px`;
    this.canvas.style.height = `${height}px`;
    this.ctx.scale(dpr, dpr);

    this.width = width;
    this.height = height;

    this.computeLayout();
  }

  computeLayout() {
    const maxDimension = 24;
    const availableW = this.width - 130;
    const availableH = this.height - 110;

    this.tileSize = Math.max(14, Math.min(32, Math.floor(Math.min(availableW / maxDimension, availableH / maxDimension))));
    
    const habitatPixelW = this.engine.width * this.tileSize;
    const habitatPixelH = this.engine.length * this.tileSize;

    this.gridOriginX = Math.round((this.width - habitatPixelW) / 2);
    this.gridOriginY = Math.round((this.height - habitatPixelH) / 2) + 12;
  }

  triggerCelebration() {
    this.particles = [];
    const colors = ['#4FD1C5', '#F6C76D', '#E8A33D', '#60A5FA', '#34D399', '#FFFFFF'];
    const cx = this.gridOriginX + (this.engine.width * this.tileSize) / 2;
    const cy = this.gridOriginY + (this.engine.length * this.tileSize) / 2;

    for (let i = 0; i < 85; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = 2.5 + Math.random() * 6.5;
      this.particles.push({
        x: cx,
        y: cy,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 1.8,
        color: colors[Math.floor(Math.random() * colors.length)],
        size: 3 + Math.random() * 4,
        alpha: 1.0,
        decay: 0.015 + Math.random() * 0.018
      });
    }
  }

  notifyDimensionChange() {
    this.constructionGlow = 1.0;
  }

  getHandleBounds() {
    const gx = this.gridOriginX;
    const gy = this.gridOriginY;
    const gw = this.engine.width * this.tileSize;
    const gh = this.engine.length * this.tileSize;
    const hs = 18;

    return {
      corner: { x: gx + gw, y: gy + gh, radius: hs }
    };
  }

  screenToDimensions(screenX, screenY) {
    const gx = this.gridOriginX;
    const gy = this.gridOriginY;

    const rawW = Math.round((screenX - gx) / this.tileSize);
    const rawL = Math.round((screenY - gy) / this.tileSize);

    return {
      w: Math.max(1, Math.min(24, rawW)),
      l: Math.max(1, Math.min(24, rawL))
    };
  }

  render(timestamp) {
    this.animationPhase = (timestamp / 1000.0);
    if (this.constructionGlow > 0) {
      this.constructionGlow = Math.max(0, this.constructionGlow - 0.04);
    }

    this.computeLayout();

    const ctx = this.ctx;
    const w = this.width;
    const h = this.height;

    // 1. Sky & Stars Backdrop
    this.drawBackdrop(ctx, w, h);

    // 2. Lunar Surface Bed with Terrain texture & Craters
    this.drawLunarBed(ctx, w, h);

    // 3. Habitat Floor Grid (Tiles)
    this.drawHabitatTiles(ctx);

    // 4. Glowing Meteor Shielding Exterior Wall
    this.drawExteriorWall(ctx);

    // 5. Dimension Callout Lines & Measurement Ticks
    this.drawDimensionCallouts(ctx);

    // 6. Interactive Drag Handles
    this.drawHandles(ctx);

    // 7. Tiny Astronaut & Rover
    this.drawAstronautAndRover(ctx);

    // 8. Celebration Particle System
    this.drawParticles(ctx);
  }

  drawBackdrop(ctx, w, h) {
    const skyGrad = ctx.createLinearGradient(0, 0, 0, h);
    skyGrad.addColorStop(0, '#030712');
    skyGrad.addColorStop(0.7, '#070E1A');
    skyGrad.addColorStop(1, '#0B1424');
    ctx.fillStyle = skyGrad;
    ctx.fillRect(0, 0, w, h);

    // Twinkling stars
    ctx.fillStyle = '#FFFFFF';
    for (let i = 0; i < 45; i++) {
      const sx = ((i * 187.3) % w);
      const sy = ((i * 97.1) % (h * 0.55));
      const size = (i % 3 === 0) ? 1.5 : 1.0;
      const alpha = 0.2 + 0.8 * Math.abs(Math.sin(this.animationPhase * 1.2 + i));
      ctx.globalAlpha = alpha;
      ctx.fillRect(sx, sy, size, size);
    }
    ctx.globalAlpha = 1.0;

    // Earth in the sky
    const earthX = w - 55;
    const earthY = 42;
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
    ctx.strokeStyle = 'rgba(96, 165, 250, 0.5)';
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.restore();
  }

  drawLunarBed(ctx, w, h) {
    ctx.save();
    // Subtle background grid
    ctx.strokeStyle = 'rgba(30, 44, 66, 0.35)';
    ctx.lineWidth = 1;
    const step = this.tileSize;

    const startX = (this.gridOriginX % step);
    const startY = (this.gridOriginY % step);

    for (let x = startX; x < w; x += step) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    for (let y = startY; y < h; y += step) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    // Lunar terrain ridges / craters
    ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
    ctx.beginPath();
    ctx.ellipse(60, h - 40, 50, 18, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.beginPath();
    ctx.ellipse(w - 70, h - 50, 65, 22, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }

  drawHabitatTiles(ctx) {
    const gx = this.gridOriginX;
    const gy = this.gridOriginY;
    const cols = this.engine.width;
    const rows = this.engine.length;
    const sz = this.tileSize;

    ctx.save();
    // Foundation shadow
    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
    ctx.fillRect(gx + 6, gy + 6, cols * sz, rows * sz);

    // Floor tiles
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const tx = gx + c * sz;
        const ty = gy + r * sz;
        const isChecker = (c + r) % 2 === 0;

        let tileBg = isChecker ? '#14273E' : '#0F1E32';
        if (this.constructionGlow > 0) {
          tileBg = isChecker ? '#1A3B5C' : '#14314E';
        }

        ctx.fillStyle = tileBg;
        ctx.fillRect(tx, ty, sz, sz);

        // Tile border
        ctx.strokeStyle = '#1E3552';
        ctx.lineWidth = 1;
        ctx.strokeRect(tx, ty, sz, sz);

        // Center tech dot
        if (sz >= 18) {
          ctx.fillStyle = 'rgba(79, 209, 197, 0.4)';
          ctx.fillRect(tx + sz / 2 - 1, ty + sz / 2 - 1, 2, 2);
        }
      }
    }
    ctx.restore();
  }

  drawExteriorWall(ctx) {
    const gx = this.gridOriginX;
    const gy = this.gridOriginY;
    const gw = this.engine.width * this.tileSize;
    const gh = this.engine.length * this.tileSize;

    ctx.save();
    const calc = this.engine.getCalculations();
    const glowColor = calc.missionPassed ? 'rgba(79, 209, 197, 0.85)' : 'rgba(232, 163, 61, 0.7)';
    const borderColor = calc.missionPassed ? '#4FD1C5' : '#E8A33D';

    ctx.shadowColor = glowColor;
    ctx.shadowBlur = 14;
    ctx.strokeStyle = borderColor;
    ctx.lineWidth = 4;
    ctx.strokeRect(gx, gy, gw, gh);

    ctx.shadowBlur = 0;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.35)';
    ctx.lineWidth = 1;
    ctx.strokeRect(gx + 2, gy + 2, gw - 4, gh - 4);
    ctx.restore();
  }

  drawDimensionCallouts(ctx) {
    const gx = this.gridOriginX;
    const gy = this.gridOriginY;
    const gw = this.engine.width * this.tileSize;
    const gh = this.engine.length * this.tileSize;

    ctx.save();
    ctx.font = '700 12px "Oswald", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    // 1. Top Width Bar
    const topY = gy - 20;
    ctx.strokeStyle = '#4FD1C5';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(gx, topY);
    ctx.lineTo(gx + gw, topY);
    ctx.moveTo(gx, topY - 5);
    ctx.lineTo(gx, topY + 5);
    ctx.moveTo(gx + gw, topY - 5);
    ctx.lineTo(gx + gw, topY + 5);
    ctx.stroke();

    ctx.fillStyle = '#0B1220';
    ctx.fillRect(gx + gw / 2 - 48, topY - 10, 96, 20);
    ctx.strokeStyle = '#4FD1C5';
    ctx.strokeRect(gx + gw / 2 - 48, topY - 10, 96, 20);
    ctx.fillStyle = '#4FD1C5';
    ctx.fillText(`WIDTH: ${this.engine.width} m`, gx + gw / 2, topY);

    // 2. Left Length Bar
    const leftX = gx - 24;
    ctx.beginPath();
    ctx.moveTo(leftX, gy);
    ctx.lineTo(leftX, gy + gh);
    ctx.moveTo(leftX - 5, gy);
    ctx.lineTo(leftX + 5, gy);
    ctx.moveTo(leftX - 5, gy + gh);
    ctx.lineTo(leftX + 5, gy + gh);
    ctx.stroke();

    ctx.save();
    ctx.translate(leftX, gy + gh / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillStyle = '#0B1220';
    ctx.fillRect(-48, -10, 96, 20);
    ctx.strokeStyle = '#4FD1C5';
    ctx.strokeRect(-48, -10, 96, 20);
    ctx.fillStyle = '#4FD1C5';
    ctx.fillText(`LENGTH: ${this.engine.length} m`, 0, 0);
    ctx.restore();

    // 3. Center Area Readout
    ctx.font = '700 18px "Oswald", sans-serif';
    ctx.fillStyle = '#F6C76D';
    const area = this.engine.width * this.engine.length;
    const cx = gx + gw / 2;
    const cy = gy + gh / 2;

    ctx.fillStyle = 'rgba(11, 18, 32, 0.8)';
    ctx.beginPath();
    ctx.roundRect(cx - 55, cy - 14, 110, 28, 6);
    ctx.fill();
    ctx.strokeStyle = '#1E2C42';
    ctx.stroke();

    ctx.fillStyle = '#F6C76D';
    ctx.fillText(`${area} TILES`, cx, cy);

    ctx.restore();
  }

  drawHandles(ctx) {
    const handles = this.getHandleBounds();

    ctx.save();
    ctx.fillStyle = '#E8A33D';
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineWidth = 2;

    ctx.beginPath();
    ctx.arc(handles.corner.x, handles.corner.y, 9, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    ctx.strokeStyle = '#0B1220';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(handles.corner.x - 4, handles.corner.y);
    ctx.lineTo(handles.corner.x + 4, handles.corner.y);
    ctx.moveTo(handles.corner.x, handles.corner.y - 4);
    ctx.lineTo(handles.corner.x, handles.corner.y + 4);
    ctx.stroke();

    ctx.restore();
  }

  drawAstronautAndRover(ctx) {
    const gx = this.gridOriginX;
    const gy = this.gridOriginY;
    const gw = this.engine.width * this.tileSize;
    const gh = this.engine.length * this.tileSize;
    const sz = this.tileSize;

    ctx.save();
    // 1. Tiny Astronaut inside room (tile 0,0)
    const ax = gx + sz * 0.5;
    const ay = gy + sz * 0.5;
    ctx.font = `${Math.max(14, sz * 0.85)}px monospace`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('👨‍🚀', ax, ay);

    // 2. Tiny Rover outside on the lunar soil (bottom right of canvas)
    const rx = Math.min(this.width - 45, gx + gw + 35);
    const ry = Math.min(this.height - 35, gy + gh + 15);
    ctx.font = '20px monospace';
    ctx.fillText('🚜', rx, ry);

    // Blinking rover antenna light
    const isBlink = Math.sin(this.animationPhase * 4) > 0;
    if (isBlink) {
      ctx.fillStyle = '#EF4444';
      ctx.beginPath();
      ctx.arc(rx - 4, ry - 14, 2.5, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.restore();
  }

  drawParticles(ctx) {
    if (this.particles.length === 0) return;

    ctx.save();
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.x += p.vx;
      p.y += p.vy;
      p.vy += 0.1;
      p.alpha -= p.decay;

      if (p.alpha <= 0) {
        this.particles.splice(i, 1);
        continue;
      }

      ctx.fillStyle = p.color;
      ctx.globalAlpha = p.alpha;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }
}
