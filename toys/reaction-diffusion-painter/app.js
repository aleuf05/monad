(function () {
  "use strict";

  const PRESETS = {
    coral: { label: "Coral", feed: 0.0545, kill: 0.0620, seedScale: 1.05 },
    mitosis: { label: "Mitosis", feed: 0.0367, kill: 0.0649, seedScale: 0.8 },
    worms: { label: "Worms", feed: 0.0780, kill: 0.0610, seedScale: 1.15 },
    labyrinth: { label: "Labyrinth", feed: 0.0290, kill: 0.0570, seedScale: 0.95 }
  };

  const DIFF_A = 1.0;
  const DIFF_B = 0.5;
  const DT = 1.0;
  const DPR_LIMIT = 2;

  const els = {
    wrap: document.getElementById("canvasWrap"),
    canvas: document.getElementById("fieldCanvas"),
    cursor: document.getElementById("brushCursor"),
    pause: document.getElementById("pauseButton"),
    reset: document.getElementById("resetButton"),
    random: document.getElementById("randomButton"),
    preset: document.getElementById("presetSelect"),
    feed: document.getElementById("feedSlider"),
    kill: document.getElementById("killSlider"),
    brush: document.getElementById("brushSlider"),
    speed: document.getElementById("speedSlider"),
    feedValue: document.getElementById("feedValue"),
    killValue: document.getElementById("killValue"),
    brushValue: document.getElementById("brushValue"),
    speedValue: document.getElementById("speedValue")
  };

  const ctx = els.canvas.getContext("2d", { alpha: false });
  const paint = {
    active: false,
    pointerId: null,
    x: 0,
    y: 0,
    hadIntentionalPause: false
  };

  const state = {
    paused: false,
    feed: Number(els.feed.value),
    kill: Number(els.kill.value),
    brush: Number(els.brush.value),
    speed: Number(els.speed.value),
    presetKey: els.preset.value,
    visualWidth: 1,
    visualHeight: 1,
    dpr: 1
  };

  class Simulation {
    constructor(width, height) {
      this.resize(width, height);
    }

    resize(width, height) {
      this.width = Math.max(24, Math.floor(width));
      this.height = Math.max(24, Math.floor(height));
      this.size = this.width * this.height;
      this.a = new Float32Array(this.size);
      this.b = new Float32Array(this.size);
      this.nextA = new Float32Array(this.size);
      this.nextB = new Float32Array(this.size);
      this.imageData = new ImageData(this.width, this.height);
      this.bufferCanvas = document.createElement("canvas");
      this.bufferCanvas.width = this.width;
      this.bufferCanvas.height = this.height;
      this.bufferCtx = this.bufferCanvas.getContext("2d", { alpha: false });
      this.seed();
    }

    seed() {
      this.a.fill(1);
      this.b.fill(0);
      const count = Math.max(7, Math.round((this.width * this.height) / 9500));
      for (let i = 0; i < count; i += 1) {
        const cx = rand(0.12, 0.88) * this.width;
        const cy = rand(0.12, 0.88) * this.height;
        const radius = rand(7, 18) * PRESETS[state.presetKey].seedScale;
        this.seedBlob(cx, cy, radius, 0.82 + Math.random() * 0.16);
      }
      this.seedBlob(this.width * 0.5, this.height * 0.5, Math.min(this.width, this.height) * 0.07, 0.95);
      this.addNoise();
    }

    randomize() {
      this.seed();
    }

    addNoise() {
      for (let i = 0; i < this.size; i += 1) {
        this.a[i] = clamp01(this.a[i] + rand(-0.015, 0.008));
        this.b[i] = clamp01(this.b[i] + Math.max(0, rand(-0.008, 0.012)));
      }
    }

    seedBlob(cx, cy, radius, strength) {
      const minX = Math.max(0, Math.floor(cx - radius * 1.35));
      const maxX = Math.min(this.width - 1, Math.ceil(cx + radius * 1.35));
      const minY = Math.max(0, Math.floor(cy - radius * 1.35));
      const maxY = Math.min(this.height - 1, Math.ceil(cy + radius * 1.35));
      for (let y = minY; y <= maxY; y += 1) {
        for (let x = minX; x <= maxX; x += 1) {
          const dx = x - cx;
          const dy = y - cy;
          const jitter = 0.82 + noise2(x, y) * 0.36;
          const d = Math.sqrt(dx * dx + dy * dy);
          if (d < radius * jitter) {
            const idx = y * this.width + x;
            const edge = 1 - d / (radius * jitter);
            const amount = strength * Math.pow(edge, 0.45);
            this.b[idx] = Math.max(this.b[idx], clamp01(amount));
            this.a[idx] = Math.min(this.a[idx], 1 - amount * 0.55);
          }
        }
      }
    }

    applyBrush(gridX, gridY, radius) {
      const r = Math.max(1, radius);
      const r2 = r * r;
      const minX = Math.max(0, Math.floor(gridX - r));
      const maxX = Math.min(this.width - 1, Math.ceil(gridX + r));
      const minY = Math.max(0, Math.floor(gridY - r));
      const maxY = Math.min(this.height - 1, Math.ceil(gridY + r));
      for (let y = minY; y <= maxY; y += 1) {
        const row = y * this.width;
        for (let x = minX; x <= maxX; x += 1) {
          const dx = x - gridX;
          const dy = y - gridY;
          const d2 = dx * dx + dy * dy;
          if (d2 <= r2) {
            const idx = row + x;
            const falloff = 1 - Math.sqrt(d2) / r;
            this.b[idx] = clamp01(this.b[idx] + 0.72 * falloff + 0.18);
            this.a[idx] = clamp01(this.a[idx] - 0.52 * falloff);
          }
        }
      }
    }

    step(feed, kill) {
      const w = this.width;
      const h = this.height;
      const a = this.a;
      const b = this.b;
      const na = this.nextA;
      const nb = this.nextB;

      // Toroidal indexing keeps edge cells stable without special visual borders.
      for (let y = 0; y < h; y += 1) {
        const ym = y === 0 ? h - 1 : y - 1;
        const yp = y === h - 1 ? 0 : y + 1;
        const row = y * w;
        const rowM = ym * w;
        const rowP = yp * w;

        for (let x = 0; x < w; x += 1) {
          const xm = x === 0 ? w - 1 : x - 1;
          const xp = x === w - 1 ? 0 : x + 1;
          const i = row + x;
          const av = a[i];
          const bv = b[i];

          const lapA = -av
            + 0.2 * (a[row + xm] + a[row + xp] + a[rowM + x] + a[rowP + x])
            + 0.05 * (a[rowM + xm] + a[rowM + xp] + a[rowP + xm] + a[rowP + xp]);
          const lapB = -bv
            + 0.2 * (b[row + xm] + b[row + xp] + b[rowM + x] + b[rowP + x])
            + 0.05 * (b[rowM + xm] + b[rowM + xp] + b[rowP + xm] + b[rowP + xp]);

          const reaction = av * bv * bv;
          na[i] = clamp01(av + (DIFF_A * lapA - reaction + feed * (1 - av)) * DT);
          nb[i] = clamp01(bv + (DIFF_B * lapB + reaction - (kill + feed) * bv) * DT);
        }
      }

      this.a = na;
      this.b = nb;
      this.nextA = a;
      this.nextB = b;
    }

    render(targetCtx, targetWidth, targetHeight) {
      const pixels = this.imageData.data;
      for (let i = 0, p = 0; i < this.size; i += 1, p += 4) {
        const value = clamp01((this.b[i] * 2.25 + (1 - this.a[i]) * 0.45) - 0.04);
        const c = palette(value);
        pixels[p] = c[0];
        pixels[p + 1] = c[1];
        pixels[p + 2] = c[2];
        pixels[p + 3] = 255;
      }
      this.bufferCtx.putImageData(this.imageData, 0, 0);
      targetCtx.imageSmoothingEnabled = true;
      targetCtx.imageSmoothingQuality = "high";
      targetCtx.drawImage(this.bufferCanvas, 0, 0, targetWidth, targetHeight);
    }
  }

  let sim = new Simulation(220, 140);

  function palette(t) {
    const stops = [
      [0.00, [2, 5, 9]],
      [0.18, [7, 18, 30]],
      [0.38, [12, 68, 82]],
      [0.62, [55, 180, 174]],
      [0.82, [184, 235, 221]],
      [1.00, [246, 205, 124]]
    ];
    for (let i = 1; i < stops.length; i += 1) {
      if (t <= stops[i][0]) {
        const prev = stops[i - 1];
        const next = stops[i];
        const local = smoothstep((t - prev[0]) / (next[0] - prev[0]));
        return [
          lerp(prev[1][0], next[1][0], local),
          lerp(prev[1][1], next[1][1], local),
          lerp(prev[1][2], next[1][2], local)
        ];
      }
    }
    return stops[stops.length - 1][1];
  }

  function resize() {
    const rect = els.wrap.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) {
      return;
    }
    state.visualWidth = Math.floor(rect.width);
    state.visualHeight = Math.floor(rect.height);
    state.dpr = Math.min(window.devicePixelRatio || 1, DPR_LIMIT);
    els.canvas.width = Math.floor(state.visualWidth * state.dpr);
    els.canvas.height = Math.floor(state.visualHeight * state.dpr);
    ctx.setTransform(state.dpr, 0, 0, state.dpr, 0, 0);

    const targetAcross = state.visualWidth < 560 ? 170 : state.visualWidth < 920 ? 220 : 280;
    const aspect = state.visualHeight / Math.max(1, state.visualWidth);
    const nextW = Math.round(targetAcross);
    const nextH = Math.max(90, Math.round(targetAcross * aspect));
    if (Math.abs(nextW - sim.width) > 12 || Math.abs(nextH - sim.height) > 12) {
      sim.resize(nextW, nextH);
    }
    updateCursorSize();
  }

  function setPaused(paused) {
    state.paused = paused;
    els.pause.textContent = paused ? "Resume" : "Pause";
    els.pause.setAttribute("aria-pressed", String(paused));
  }

  function syncSliderLabels() {
    els.feedValue.textContent = state.feed.toFixed(4);
    els.killValue.textContent = state.kill.toFixed(4);
    els.brushValue.textContent = String(state.brush);
    els.speedValue.textContent = String(state.speed);
  }

  function applyPreset(key) {
    const preset = PRESETS[key];
    state.presetKey = key;
    state.feed = preset.feed;
    state.kill = preset.kill;
    els.feed.value = preset.feed;
    els.kill.value = preset.kill;
    syncSliderLabels();
    sim.seed();
    setPaused(false);
  }

  function pointerToGrid(event) {
    const rect = els.canvas.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * sim.width;
    const y = ((event.clientY - rect.top) / rect.height) * sim.height;
    return { x, y, rect };
  }

  function paintAt(event) {
    const point = pointerToGrid(event);
    sim.applyBrush(point.x, point.y, state.brush);
    paint.x = event.clientX - point.rect.left;
    paint.y = event.clientY - point.rect.top;
    moveCursor(paint.x, paint.y);
  }

  function updateCursorSize() {
    const px = (state.brush / sim.width) * state.visualWidth * 2;
    els.cursor.style.width = `${Math.max(8, px)}px`;
    els.cursor.style.height = `${Math.max(8, px)}px`;
  }

  function moveCursor(x, y) {
    els.cursor.style.transform = `translate(${x}px, ${y}px) translate(-50%, -50%)`;
  }

  function loop() {
    if (!state.paused) {
      for (let i = 0; i < state.speed; i += 1) {
        sim.step(state.feed, state.kill);
      }
    }
    sim.render(ctx, state.visualWidth, state.visualHeight);
    requestAnimationFrame(loop);
  }

  function rand(min, max) {
    return min + Math.random() * (max - min);
  }

  function clamp01(value) {
    return value < 0 ? 0 : value > 1 ? 1 : value;
  }

  function lerp(a, b, t) {
    return Math.round(a + (b - a) * t);
  }

  function smoothstep(t) {
    const x = clamp01(t);
    return x * x * (3 - 2 * x);
  }

  function noise2(x, y) {
    const n = Math.sin(x * 12.9898 + y * 78.233) * 43758.5453;
    return n - Math.floor(n);
  }

  els.pause.addEventListener("click", () => {
    paint.hadIntentionalPause = !state.paused;
    setPaused(!state.paused);
  });

  els.reset.addEventListener("click", () => {
    sim.seed();
    if (!paint.hadIntentionalPause) {
      setPaused(false);
    }
  });

  els.random.addEventListener("click", () => {
    sim.randomize();
  });

  els.preset.addEventListener("change", () => {
    applyPreset(els.preset.value);
  });

  els.feed.addEventListener("input", () => {
    state.feed = Number(els.feed.value);
    els.feedValue.textContent = state.feed.toFixed(4);
  });

  els.kill.addEventListener("input", () => {
    state.kill = Number(els.kill.value);
    els.killValue.textContent = state.kill.toFixed(4);
  });

  els.brush.addEventListener("input", () => {
    state.brush = Number(els.brush.value);
    els.brushValue.textContent = String(state.brush);
    updateCursorSize();
  });

  els.speed.addEventListener("input", () => {
    state.speed = Number(els.speed.value);
    els.speedValue.textContent = String(state.speed);
  });

  els.canvas.addEventListener("pointerdown", (event) => {
    if (event.pointerType !== "mouse" && event.isPrimary === false) {
      return;
    }
    event.preventDefault();
    paint.active = true;
    paint.pointerId = event.pointerId;
    els.canvas.setPointerCapture(event.pointerId);
    paintAt(event);
  });

  els.canvas.addEventListener("pointermove", (event) => {
    const point = pointerToGrid(event);
    if (event.pointerType === "mouse") {
      els.cursor.style.display = "block";
      moveCursor(event.clientX - point.rect.left, event.clientY - point.rect.top);
    }
    if (paint.active && event.pointerId === paint.pointerId) {
      event.preventDefault();
      sim.applyBrush(point.x, point.y, state.brush);
    }
  });

  function endPointer(event) {
    if (event.pointerId === paint.pointerId) {
      paint.active = false;
      paint.pointerId = null;
    }
  }

  els.canvas.addEventListener("pointerup", endPointer);
  els.canvas.addEventListener("pointercancel", endPointer);
  els.canvas.addEventListener("lostpointercapture", endPointer);
  els.canvas.addEventListener("pointerleave", () => {
    els.cursor.style.display = "none";
  });

  window.addEventListener("resize", resize);
  window.addEventListener("orientationchange", () => setTimeout(resize, 150));
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      resize();
    }
  });

  syncSliderLabels();
  resize();
  requestAnimationFrame(loop);
})();
