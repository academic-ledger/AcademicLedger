// Illustrative QaL math — shared by the seed (writes qal_records) and the UI.
//
// IMPORTANT: this is the POC stand-in. The real QaL is the calibrated posterior
// over eventual percentile from the Layer-B back-test (pipeline/calibrate.py),
// NOT a transform of the observed percentile. Until that back-test passes,
// everything here is labelled "illustrative pending calibration" (QaL_spec.md §10).

export const NOW = 2026;

export interface QalPoint {
  point: number;
  lo: number;
  hi: number;
}

// The exact formula the mocks use, kept identical so the app matches them:
// younger papers get a wider interval; it narrows as evidence accrues.
export function illustrativeQal(obs: number | null, year: number | null): QalPoint | null {
  if (obs == null) return null;
  const pt = Math.round(obs);
  const age = Math.max(1, NOW - (year ?? NOW) + 1);
  const hw = Math.min(19, Math.max(3, Math.round((1 - Math.min(age, 10) / 10) * 16 + 3)));
  return {
    point: pt,
    lo: Math.max(0, pt - hw),
    hi: Math.min(100, pt + Math.max(1, Math.round(hw / 3))),
  };
}

// Standard normal CDF (Abramowitz & Stegun 7.1.26 approximation).
function normCdf(x: number, mean: number, sd: number): number {
  if (sd <= 0) return x >= mean ? 1 : 0;
  const z = (x - mean) / (sd * Math.SQRT2);
  // erf approximation
  const t = 1 / (1 + 0.3275911 * Math.abs(z));
  const y =
    1 -
    ((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - 0.284496736) * t +
      0.254829592) *
      t *
      Math.exp(-z * z);
  const erf = z >= 0 ? y : -y;
  return 0.5 * (1 + erf);
}

// Cumulative class probabilities P(eventual >= k) for the NSF buckets,
// from a normal centered at the point with sd implied by the 90% interval.
export interface ClassProb {
  ge50: number;
  ge75: number;
  ge90: number;
  ge95: number;
  ge99: number;
}

export function classProb(q: QalPoint): ClassProb {
  const sd = Math.max(1.5, (q.hi - q.lo) / 3.2897); // 90% interval ≈ ±1.6449 sd
  const ge = (k: number) => {
    const p = 1 - normCdf(k, q.point, sd);
    return Math.round(p * 100) / 100;
  };
  return { ge50: ge(50), ge75: ge(75), ge90: ge(90), ge95: ge(95), ge99: ge(99) };
}

// Per-bucket masses for the hero chart (top 50/25/10/5/1 bands),
// derived from the cumulative class probabilities.
export interface Buckets {
  lt50: number;
  b50_75: number;
  b75_90: number;
  b90_95: number;
  b95_99: number;
  b99_100: number;
}

export function buckets(cp: ClassProb): Buckets {
  const clamp = (x: number) => Math.max(0, Math.round(x * 100));
  return {
    lt50: clamp(1 - cp.ge50),
    b50_75: clamp(cp.ge50 - cp.ge75),
    b75_90: clamp(cp.ge75 - cp.ge90),
    b90_95: clamp(cp.ge90 - cp.ge95),
    b95_99: clamp(cp.ge95 - cp.ge99),
    b99_100: clamp(cp.ge99),
  };
}
