export function validate(mi, mf, re) {
  if (![mi, mf, re].every(Number.isFinite) || mf <= 0 || mi <= mf || re <= 0) {
    throw new RangeError("Require mi > mf > 0 and Re > 0.");
  }
}

export function stateAt(mi, mf, re, fraction) {
  validate(mi, mf, re);
  const f = Math.max(0, Math.min(1, fraction));
  const m = mi - (mi - mf) * f;
  const constantVe = Math.sqrt(2 * re);
  const k = Math.sqrt(2 * re * mi * mf);
  return {
    fraction: f,
    mass: m,
    constantVe,
    optimalVe: k / m,
    constantDv: constantVe * Math.log(mi / m),
    optimalDv: k * (1 / m - 1 / mi),
  };
}

export function finalState(mi, mf, re) {
  return stateAt(mi, mf, re, 1);
}

export function gainFactor(mi, mf) {
  validate(mi, mf, 1);
  const r = mi / mf;
  return (r - 1) / (Math.sqrt(r) * Math.log(r));
}

export function series(mi, mf, re, count = 121) {
  return Array.from({ length: count }, (_, index) =>
    stateAt(mi, mf, re, index / (count - 1)));
}
