/**
 * Cameron Lab: a small deterministic remediation engine.
 * Each lab makes one prerequisite visible before asking for abstraction.
 */

export const MISSIONS = [
  { id: 0, title: '0 · Calibration', type: 'assessment', prompt: 'Let’s find the edges of your current intuition.', subtext: 'Predict first. Then move the state and let the live model answer.' },
  { id: 1, title: '1 · Slope', type: 'derivative', prompt: 'Recover the derivative by watching a curve move.', subtext: 'Start with f(x) = x³ − 3x. Find where the tangent goes flat.' },
  { id: 2, title: '2 · Accumulation', type: 'integral', prompt: 'See an integral as accumulated change.', subtext: 'Move through g(t) = sin(t). Watch signed area build and cancel.' },
  { id: 3, title: '3 · Electric Field', type: 'electrostatics', prompt: 'Reconnect electric field, potential, and force.', subtext: 'A point charge is simple enough to inspect—and unforgiving about signs.' },
  { id: 4, title: '4 · Maxwell Check', type: 'gauss', prompt: 'Use symmetry before reaching for a formula.', subtext: 'A Gaussian sphere only tells the truth when the assumptions fit.' }
  ,{ id: 5, title: '5 · Fourier', type: 'fourier', prompt: 'Watch a waveform reveal its hidden frequencies.', subtext: 'Turn a signal into rotating components and feel what the transform is doing.' }
];

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const fmt = (v) => Number(v).toFixed(2).replace(/\.00$/, '');

export class MoonbaseMathEngine {
  constructor() {
    this.width = 1;
    this.length = 1;
    this.currentMissionIndex = 0;
    this.insights = new Set();
    this.lastCalculation = null;
  }

  getCurrentMission() { return MISSIONS[this.currentMissionIndex]; }

  setDimensions(primary, secondary) {
    const before = [this.width, this.length];
    this.width = clamp(Math.round(Number(primary) * 10) / 10, -30, 30);
    this.length = clamp(Math.round(Number(secondary) * 10) / 10, -10, 10);
    const calc = this.getCalculations();
    return { changed: before[0] !== this.width || before[1] !== this.length, state: calc, maraReaction: this.evaluateMaraReaction(calc) };
  }

  setWidth(v) { return this.setDimensions(v, this.length); }
  setLength(v) { return this.setDimensions(this.width, v); }

  getCalculations() {
    const x = this.width;
    const q = this.length;
    const mission = this.getCurrentMission();
    let c;

    if (mission.type === 'assessment') {
      const probes = [
        { prompt: 'At x = 1, is f(x) = x² rising, flat, or falling?', answer: 'flat', explanation: 'The slope is 2x, so at x = 1 it is positive—not flat. This probe is intentionally baited: distinguish value from slope.' },
        { prompt: 'If radius doubles, what happens to a point-charge field?', answer: 'quarter', explanation: 'E ∝ 1/r². Doubling distance makes the field one quarter as strong.' },
        { prompt: 'Does an integral track rate or accumulated change?', answer: 'accumulation', explanation: 'The integrand is the rate; the integral accumulates signed change.' }
      ];
      const probe = probes[Math.min(probes.length - 1, Math.max(0, Math.round(Math.abs(x))))];
      c = { stateLabel: 'PROBE', stateFormula: `probe ${Math.min(probes.length, Math.round(Math.abs(x)) + 1)} / ${probes.length}`, functionLabel: 'QUESTION', functionFormula: 'predict before reveal', functionValue: probe.prompt, functionSub: 'use the live toy, not recall alone', derivativeLabel: 'INSTRUMENT', derivativeFormula: 'current controls are live', derivativeValue: `q = ${fmt(q)}`, derivativeSub: 'change the state after choosing', check: 'PREDICT', checkSub: probe.explanation, missionPassed: false, assessment: true, probe };
    } else if (mission.type === 'derivative') {
      const y = x ** 3 - 3 * x;
      const slope = 3 * x ** 2 - 3;
      const curvature = 6 * x;
      c = { stateLabel: 'POSITION x', stateFormula: `x = ${fmt(x)}`, functionLabel: 'FUNCTION', functionFormula: 'f(x) = x³ − 3x', functionValue: `f(x) = ${fmt(y)}`, functionSub: 'height of the curve', derivativeLabel: 'DERIVATIVE', derivativeFormula: 'f′(x) = 3x² − 3', derivativeValue: `f′(x) = ${fmt(slope)}`, derivativeSub: `tangent slope · curvature ${fmt(curvature)}`, check: Math.abs(slope) < 0.06 ? 'STATIONARY POINT' : (slope > 0 ? 'RISING' : 'FALLING'), checkSub: 'a horizontal tangent has derivative 0', missionPassed: Math.abs(slope) < 0.06 };
    } else if (mission.type === 'integral') {
      const area = 1 - Math.cos(x);
      const rate = Math.sin(x);
      c = { stateLabel: 'TIME t', stateFormula: `t = ${fmt(x)}`, functionLabel: 'RATE', functionFormula: 'g(t) = sin(t)', functionValue: `g(t) = ${fmt(rate)}`, functionSub: 'instantaneous accumulation rate', derivativeLabel: 'INTEGRAL', derivativeFormula: 'G(t) = ∫₀ᵗ sin(u) du', derivativeValue: `G(t) = ${fmt(area)}`, derivativeSub: 'signed area since t = 0', check: Math.abs(area - 1) < 0.06 ? 'AREA = 1' : (rate > 0 ? 'ACCUMULATING' : 'GIVING BACK'), checkSub: 'the integral remembers the whole path', missionPassed: Math.abs(area - 1) < 0.06 };
    } else if (mission.type === 'electrostatics') {
      const r = Math.max(0.4, Math.abs(x));
      const charge = q === 0 ? 0.1 : q;
      const field = charge / (r ** 2);
      const potential = charge / r;
      c = { stateLabel: 'RADIUS r', stateFormula: `r = ${fmt(r)}`, functionLabel: 'CHARGE q', functionFormula: 'q in normalized units', functionValue: `q = ${fmt(charge)}`, functionSub: 'positive points outward; negative inward', derivativeLabel: 'FIELD / POTENTIAL', derivativeFormula: 'E = q/r² · V = q/r', derivativeValue: `E = ${fmt(field)} · V = ${fmt(potential)}`, derivativeSub: 'E = −dV/dr (sign is the lesson)', check: Math.abs(r - 1) < 0.06 ? 'REFERENCE RADIUS' : (field > 0 ? 'OUTWARD FIELD' : 'INWARD FIELD'), checkSub: 'double r: quarter E, half V', missionPassed: Math.abs(r - 2) < 0.06 && charge > 0 };
    } else if (mission.type === 'gauss') {
      const radius = Math.max(0.4, Math.abs(x));
      const enclosed = q;
      const flux = enclosed;
      c = { stateLabel: 'GAUSSIAN RADIUS', stateFormula: `R = ${fmt(radius)}`, functionLabel: 'ENCLOSED CHARGE', functionFormula: 'Qenc', functionValue: `Qenc = ${fmt(enclosed)}`, functionSub: 'uniform spherical symmetry assumed', derivativeLabel: 'GAUSS CHECK', derivativeFormula: 'ΦE = Qenc / ε₀', derivativeValue: `ΦE ∝ ${fmt(flux)}`, derivativeSub: 'radius disappears from total flux', check: Math.abs(enclosed) > 0.1 ? 'SYMMETRY APPLIES' : 'NO CHARGE ENCLOSED', checkSub: 'flux depends on what is inside', missionPassed: Math.abs(radius - 2) < 0.06 && Math.abs(enclosed - 1) < 0.06 };
    } else {
      const f1 = 1.5;
      const f2 = Math.max(0.2, Math.abs(q));
      const sample = Math.sin(f1 * x) + 0.6 * Math.sin(f2 * x);
      c = { stateLabel: 'TIME τ', stateFormula: `τ = ${fmt(x)}`, functionLabel: 'SIGNAL', functionFormula: `s(τ) = sin(${f1}τ) + 0.6sin(${fmt(f2)}τ)`, functionValue: `s(τ) = ${fmt(sample)}`, functionSub: 'two rotating components interfere', derivativeLabel: 'SPECTRUM', derivativeFormula: 'Fourier: time ↔ frequency', derivativeValue: `peaks near ${f1} and ${fmt(f2)}`, derivativeSub: 'change q to tune the second component', check: Math.abs(f2 - f1) < 0.06 ? 'FREQUENCIES COLLIDE' : 'TWO COMPONENTS VISIBLE', checkSub: 'the transform makes hidden structure inspectable', missionPassed: Math.abs(f2 - 3) < 0.06 };
    }

    c.width = this.width; c.length = this.length; c.mission = mission;
    c.insights = Array.from(this.insights);
    this.lastCalculation = c;
    return c;
  }

  evaluateMaraReaction(c) {
    if (c.missionPassed) {
      const key = `${c.mission.id}:${c.check}`;
      this.insights.add(key);
      return `“Good. Say the reason out loud: ${c.check.toLowerCase()}. Now perturb the state and see what survives.”`;
    }
    if (c.mission.type === 'derivative') return `“Before moving again: predict whether the tangent rises or falls. The sign of f′ is the whole first move.”`;
    if (c.mission.type === 'integral') return `“Rate is not total change. Watch the signed area accumulate, then ask what cancellation means.”`;
    if (c.mission.type === 'electrostatics') return `“Do not memorize the inverse square in isolation. Compare E and V after doubling r.”`;
    return `“Gauss’s law is not a magic sphere. Check the symmetry and ask what charge is actually enclosed.”`;
  }
}
