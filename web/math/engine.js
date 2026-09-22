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
  ,{ id: 6, title: '6 · Field → Coil', type: 'electromagnetism', prompt: 'From field to coil: make the electromagnetic system visible.', subtext: 'Predict the bench experiment before the equation explains it.' }
];

export const EM_STAGES = [
  { id: 'field', label: '01 · Field', title: 'A field is a value assigned throughout space', body: 'A scalar field assigns a scalar to every point, T(x,y,z). A vector field assigns a vector, F(x,y,z). In the ordinary laboratory frame, we use two 3-vector fields to describe electromagnetism:', formula: 'E(x,y,z,t)    B(x,y,z,t)', note: 'E = electric field. B = magnetic field. They are not ultimately independent pieces of nature; E/B is a useful frame-dependent decomposition.', prompt: 'At one position and one instant, how many scalar components specify E and B together?', answer: '6', explanation: 'E has 3 components and B has 3: six scalar components total.' },
  { id: 'electric', label: '02 · E', title: 'What E means operationally', body: 'Use a positive test charge as a probe. The operational definition is:', formula: 'F = qE       therefore       E = F/q', note: 'E exists as the field description at the point. The test charge is a hypothetical probe used to characterize it.', prompt: 'If q doubles while E remains unchanged, what happens to F?', answer: 'doubles', explanation: 'F = qE, so doubling q doubles the force. Reversing q reverses the force direction.' },
  { id: 'current', label: '03 · I → B', title: 'Current and the right-hand rule', body: 'Use conventional current for equations and right-hand rules: conventional current is motion of positive charge; electron drift in ordinary metal is opposite.', formula: 'thumb = I        curled fingers = B', note: 'For a straight wire, magnetic field lines circulate around the wire. Looking along a wire with conventional current coming directly toward you, B circulates counterclockwise.', prompt: 'Current toward you: clockwise or counterclockwise magnetic field?', answer: 'counterclockwise', explanation: 'Right-hand thumb points toward you; fingers curl counterclockwise as seen by you.' },
  { id: 'bjt', label: '04 · BJT', title: 'The 2N2222 as two PN junctions — a testing model', body: 'For the tested 2N2222, flat face toward you and leads downward: left = E, middle = B, right = C. Its material structure is:', formula: 'E       B       C\nN       P       N', note: 'On diode-test, B-E and B-C behave like silicon PN diodes, both with P at the base. Expect roughly 0.6–0.7 V forward, with device/test-current variation; reverse orientation is open at meter voltage. This is a testing/intuition model, not two independent discrete diodes: all three terminals participating produce transistor action.', prompt: 'For an NPN transistor, which terminal is the shared P region?', answer: 'base', explanation: 'The base is the shared P region in the N-P-N structure.' },
  { id: 'switch', label: '05 · Switch', title: 'A BJT lets a small control current command a separate load', body: 'The bench circuit uses GP15 to control a 2N2222. The load current comes from the 5 V supply, not directly from the GPIO.', formula: '+5 V → 510 Ω → LED → C\n                         2N2222\nGP15 → 1 kΩ → B       E → GND', note: 'RP2040 ground and 5 V load-supply ground are common. LED anode points toward +5 V; cathode toward the collector. The fundamental LED condition is V_anode > V_cathode — do not turn the N-type/cathode coincidence into a universal rule.', prompt: 'Why does the GPIO not need to source the LED load current directly?', answer: 'transistor', explanation: 'The GPIO controls the transistor; the transistor controls current from the separate load supply.' },
  { id: 'pwm', label: '06 · PWM', title: 'Fast switching becomes controllable apparent brightness', body: 'Define duty cycle as the fraction of each cycle spent ON:', formula: 'D = time ON / cycle time', note: 'D = 0 is always off; 0.25 is on one quarter; 0.50 is on half; 1 is always on. The LED appears continuous at sufficiently high frequency because visual perception integrates rapid changes. Perceived brightness is not perfectly linear with duty cycle.', prompt: 'Why does a high-frequency PWM-driven LED appear continuously lit?', answer: 'perception', explanation: 'Human visual perception integrates the rapid ON/OFF changes.' },
  { id: 'coil', label: '07 · Coil', title: 'The apparatus: a real coil with a real scale', body: 'The two-piece printed bobbin has 25 mm flange OD, 2 mm flanges, 15 mm barrel OD, 15 mm clear winding length, 12 mm bore, and a 1 mm / 15.4 mm counterbore engagement. Wind approximately 0.3 mm enamelled magnet wire, initially 300–500 turns. The approximately 10 mm × 5 mm neodymium magnet passes through or near the bore.', formula: 'N ≈ 300–500 turns', note: 'The bore is intentionally generous enough for the magnet to pass through or very near the center of the coil. This is a physical instrument, not a decorative component illustration.', prompt: 'Why use hundreds of turns instead of one?', answer: 'turns', explanation: 'Each comparable turn contributes to the total induced EMF; Faraday’s law makes the voltage scale approximately with N.' },
  { id: 'faraday', label: '08 · Faraday', title: 'Predict the motion experiment before seeing the law', body: 'The coil responds to changing magnetic flux, not merely to a strong static field. Work through the actual sequence: stationary far away; push toward/through; stop inside; pull out; repeat faster; flip the magnet.', formula: 'emf = −N dΦ_B/dt', note: 'emf is induced voltage; N is turns; Φ_B is magnetic flux through one turn; d/dt is rate of change; the minus sign is Lenz’s law: the induced response opposes the change producing it.', prompt: 'Magnet stopped inside a strong-field coil: induced voltage large or approximately zero?', answer: 'approximately zero', explanation: 'When the magnet is stationary, flux may be strong but dΦ_B/dt is approximately zero. Motion creates the pulse; faster motion creates a larger pulse; pulling out reverses polarity.' },
  { id: 'flux', label: '09 · Flux', title: 'Flux counts field passing through the loop', body: 'Do not treat magnetic flux as a mystical substance. For a flat loop:', formula: 'Φ_B = ∫ B · dA        and, if uniform,        Φ_B ≈ BA', note: 'The dot product matters: field passing THROUGH the loop matters, not merely field existing nearby. Turning the loop changes the effective area component.', prompt: 'If one turn produces 2 mV under some motion, what would 400 equivalent turns ideally produce?', answer: '0.8 V', explanation: '400 × 2 mV = 800 mV = 0.8 V. Real geometry means turns do not all experience exactly identical flux.' },
  { id: 'drive', label: '10 · Drive', title: 'Reciprocity: drive the coil and make B', body: 'Reverse the experiment: current → coil → magnetic field. The same coil is a reusable electromagnetic transducer.', formula: 'U = ½LI²', note: 'A coil has inductance. Energy is stored in its magnetic field. When current is abruptly interrupted, the inductor attempts to keep current flowing and its voltage can rise dramatically.', prompt: 'What changes when a transistor suddenly interrupts coil current?', answer: 'voltage', explanation: 'The collapsing magnetic field changes flux and produces an induced voltage that tries to preserve current.' },
  { id: 'flyback', label: '11 · Flyback', title: 'The diode gives the collapsing field a safe path', body: 'Use the canonical low-side inductive-load circuit. During normal operation the diode is reverse-biased. When the transistor turns OFF, the collapsing field drives the coil voltage the other way, forward-biasing the diode.', formula: '+V → COIL → C\n       ┌─|<|─┐\n       └─────┘\n              E → GND', note: 'The flyback diode is not primarily there to make the coil work. It protects the switching device from the inductive voltage spike by providing a safe current-decay path. That spike is another manifestation of changing magnetic flux producing EMF.', prompt: 'Why is the flyback diode present?', answer: 'protect', explanation: 'It protects the BJT by giving inductive current somewhere safe to decay when the switch opens.' },
  { id: 'synthesis', label: '12 · Synthesis', title: 'One electromagnetic system, many laboratory handles', body: 'Electric and magnetic fields, charges and currents, coils, flux, induced voltage, and switching transients are not unrelated tricks. They are different observations of one coupled system.', formula: 'E + B → charge/current interaction → coil field\n          → changing flux → induced voltage', note: 'Strong static flux can produce zero induced EMF. Rapid motion makes dΦ_B/dt nonzero. The same chain explains both the magnet experiment and the flyback spike.', prompt: 'A magnet sits motionless inside a 400-turn coil. Is induced voltage necessarily large?', answer: 'no', explanation: 'No. emf = −N dΦ_B/dt. Strong static flux is not enough; the rate of change must be nonzero.' }
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
        { prompt: 'At x = 1, is f(x) = x² rising, flat, or falling?', answer: 'rising', options: ['rising', 'flat', 'falling'], explanation: 'The slope is 2x, so at x = 1 it is positive—not flat. Distinguish value from slope.' },
        { prompt: 'If radius doubles, what happens to a point-charge field?', answer: 'quarter', options: ['double', 'half', 'quarter'], explanation: 'E ∝ 1/r². Doubling distance makes the field one quarter as strong.' },
        { prompt: 'Does an integral track rate or accumulated change?', answer: 'accumulation', options: ['rate', 'accumulation'], explanation: 'The integrand is the rate; the integral accumulates signed change.' }
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
    } else if (mission.type === 'electromagnetism') {
      const stage = EM_STAGES[Math.min(EM_STAGES.length - 1, Math.max(0, Math.round(Math.abs(x))))];
      const stageNumber = EM_STAGES.indexOf(stage);
      c = { stateLabel: 'LAB STAGE', stateFormula: `${stageNumber + 1} / ${EM_STAGES.length}`, functionLabel: stage.label, functionFormula: stage.formula.split('\n')[0], functionValue: stage.title, functionSub: stage.note, derivativeLabel: 'PREDICTION', derivativeFormula: 'before → experiment → explanation', derivativeValue: stage.prompt, derivativeSub: 'answer is revealed after you commit', check: stage.answer.toUpperCase(), checkSub: stage.explanation, missionPassed: false, assessment: true, probe: { ...stage, options: [stage.answer, stage.answer === 'no' ? 'yes' : 'not sure'] }, emStage: stage, emStageNumber: stageNumber };
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
    if (c.mission.type === 'electromagnetism') return `“Commit to a prediction before you ask the equation to rescue you. The bench decides.”`;
    return `“Gauss’s law is not a magic sphere. Check the symmetry and ask what charge is actually enclosed.”`;
  }
}
