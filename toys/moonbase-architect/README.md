# Monad Education 001 — Cameron Lab v0.3

**Audience**: Cameron (diagnostic, self-consumption)  
**Subject**: Calculus and classical electromagnetism  
**Focus**: derivatives, integrals, fields, potential, flux, and physical intuition;
now extended with a first-principles electromagnetism bench lesson.

## Core Principle

The learner manipulates a mathematical world directly rather than answering worksheets.
The laboratory starts with a small prompt, watches the reasoning, and increases the
pressure when the answer is too easy. It is deliberately personal: a refresher that
can expose a rusty derivative, a missing sign, or an unexamined physical assumption.

## User Experience

- Instant lab environment (no login, onboarding sequence, or curriculum picker).
- Direct manipulation via sliders and the plotted state.
- Instant calculation updates on the Field Instrument Panel:
  - `STATE`
  - `FUNCTION / FIELD`
  - `DERIVATIVE / POTENTIAL`
  - `INVARIANT / CHECK`

## Labs

1. **Slope / derivative**: move along $f(x)=x^3-3x$ and recover the tangent slope, stationary points, and local behavior.
2. **Accumulation / integral**: explore $g(t)=\sin(t)$ and compare instantaneous rate with accumulated signed area.
3. **Electrostatics**: vary charge and radius for a point charge; connect $E(r)$, $V(r)$, force, and energy without losing the sign.
4. **Maxwell check**: inspect a spherical Gaussian surface and see when flux, enclosed charge, and symmetry actually agree.
5. **Fourier**: decompose a live waveform into two rotating components and watch time become frequency.
6. **Field → Coil**: move from E/B as vector fields through conventional current,
   the tested 2N2222 switch and PWM, into the 300–500 turn coil, Faraday induction,
   reciprocity, inductance, and the flyback diode. Each stage asks for a prediction
   before revealing the explanation.

## MARA (Mathematical & Reality Assistant)

Deterministic, state-aware responses triggered by actual behavior to guide observation
rather than revealing answers. This is for Cameron specifically: advanced in some
directions, rusty in others, and never flattened into a school-grade category.
