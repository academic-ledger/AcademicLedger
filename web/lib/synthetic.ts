// On-the-fly synthetic field — the OFFICIAL reference class (QaL_spec §5), computed live for ANY
// paper and cached. This is the REFERENCE-BASED stage: a paper's true intellectual community is
// the recency-weighted subfield mixture of its bibliography, which corrects OpenAlex's single
// (often wrong) primary-subfield label. The full spec also migrates toward the co-citation
// neighborhood as citations accrue (λ = c/(c+k)); that scan is expensive and matters mainly for
// old, heavily-cited papers, so the live path uses reference-only (exact for young papers, a good
// approximation otherwise) and we cache the result. Percentiles come from our precomputed
// cohort_percentiles tables where available, else an exact live count query — so it is fully
// general, not limited to pre-tabulated subfields.

import { query } from "./db";
import { buckets, classProb, type ClassProb, type QalPoint } from "./qal";

const OA = "https://api.openalex.org";
const MAILTO = process.env.OPENALEX_MAILTO || "ktulrich@gmail.com";
const API_KEY = process.env.OPENALEX_API_KEY || "";
const AUTH = `&mailto=${encodeURIComponent(MAILTO)}${API_KEY ? `&api_key=${encodeURIComponent(API_KEY)}` : ""}`;
const TAU = 6 / Math.log(2); // recency decay timescale (H_HALFLIFE = 6)
const REVALIDATE = 60 * 60 * 24 * 7; // cache OpenAlex sub-fetches a week
const NOW = 2026;
const MIN_REFS = 5;

export interface SynthResult {
  obs: number; // blended observed percentile (0–100)
  weights: { sid: string; weight: number }[]; // top community weights
  dominant: string | null; // dominant subfield id
  vintage: number;
  n_refs: number;
}

type Cdf = { cites: number; pct: number }[];

function cdfLookup(cdf: Cdf | null, cites: number): number | null {
  if (!cdf || !cdf.length) return null;
  let pct = 0;
  for (const bp of cdf) {
    if (bp.cites <= cites) pct = bp.pct;
    else break;
  }
  return pct;
}

async function oaGet(pathWithQuery: string): Promise<any | null> {
  // light retry so a single transient blip on a cold (uncached) compute doesn't drop the paper to
  // calibration-pending; successful responses are HTTP-cached (revalidate) so repeats are free.
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const r = await fetch(`${OA}${pathWithQuery}${AUTH}`, {
        headers: { "User-Agent": `al-web/1.0 (${MAILTO})` },
        next: { revalidate: REVALIDATE },
      });
      if (r.ok) return await r.json();
      if (r.status !== 429 && r.status < 500) return null; // hard error, don't retry
    } catch {
      /* network blip — retry */
    }
    await new Promise((res) => setTimeout(res, 300 * (attempt + 1)));
  }
  return null;
}

// {oaid: [subfield, year]} for a list of works, batched 100/call.
async function worksSubYear(oaids: string[]): Promise<Map<string, [string | null, number | null]>> {
  const out = new Map<string, [string | null, number | null]>();
  for (let i = 0; i < oaids.length; i += 100) {
    const chunk = oaids.slice(i, i + 100);
    const d = await oaGet(
      `/works?filter=ids.openalex:${chunk.join("|")}&select=id,publication_year,primary_topic&per-page=100`
    );
    for (const w of d?.results ?? []) {
      const sid = ((w.primary_topic?.subfield?.id || "") as string).split("/").pop() || null;
      out.set((w.id || "").split("/").pop(), [sid, w.publication_year ?? null]);
    }
  }
  return out;
}

// Focal's exact full-population mid-rank percentile (0–100) in the (subfield, year) cohort. Uses
// the precomputed cohort_percentiles table when present (0 OpenAlex calls), else an exact live
// count query (QaL_spec §5: full population, uncited atom at mid-rank 100·p0/2).
async function pctInCohort(sid: string, year: number, cites: number): Promise<number | null> {
  const rows = await query<{ cdf: Cdf }>(
    `select cdf from cohort_percentiles where subfield=$1 and publication_year=$2
       order by snapshot desc limit 1`,
    [sid, year]
  );
  if (rows.length) return cdfLookup(rows[0].cdf, cites);

  const base = `primary_topic.subfield.id:subfields/${sid},publication_year:${year}`;
  const total = (await oaGet(`/works?filter=${base}&per-page=1`))?.meta?.count ?? 0;
  if (!total) return null;
  if (cites <= 0) {
    const zero = (await oaGet(`/works?filter=${base},cited_by_count:0&per-page=1`))?.meta?.count ?? 0;
    return (100 * (zero / total)) / 2; // uncited atom mid-rank
  }
  const above = (await oaGet(`/works?filter=${base},cited_by_count:>${cites}&per-page=1`))?.meta?.count ?? 0;
  const at = (await oaGet(`/works?filter=${base},cited_by_count:${cites}&per-page=1`))?.meta?.count ?? 0;
  const below = total - above - at;
  return (100 * (below + at / 2)) / total;
}

export async function syntheticField(oaid: string): Promise<SynthResult | null> {
  const focal = await oaGet(
    `/works/${encodeURIComponent(oaid)}?select=id,referenced_works,publication_year,cited_by_count`
  );
  if (!focal) return null;
  const v: number = focal.publication_year ?? NOW;
  const cites: number = focal.cited_by_count ?? 0;
  const refs: string[] = (focal.referenced_works || []).map((r: string) => r.split("/").pop());
  if (refs.length < MIN_REFS) return null; // too few references for a reference-based mixture

  // recency-weighted subfield mixture of the bibliography
  const subYear = await worksSubYear(refs);
  const w: Record<string, number> = {};
  for (const [sid, y] of subYear.values()) {
    if (!sid) continue;
    const g = Math.exp(-Math.max(0, v - (y ?? v)) / TAU);
    w[sid] = (w[sid] || 0) + g;
  }
  const tot = Object.values(w).reduce((a, b) => a + b, 0);
  if (!tot) return null;
  const weights = Object.entries(w)
    .map(([sid, x]) => ({ sid, weight: x / tot }))
    .sort((a, b) => b.weight - a.weight);

  // rank the focal against the weight-blended cohort distribution (subfields carrying >=2%)
  const keep = weights.filter((x) => x.weight >= 0.02);
  let r = 0;
  let wused = 0;
  for (const { sid, weight } of keep) {
    const pct = await pctInCohort(sid, v, cites);
    if (pct == null) continue;
    r += weight * pct;
    wused += weight;
  }
  if (wused < 0.5) return null; // most weight had no rankable cohort -> abstain

  return {
    obs: Math.round((r / wused) * 100) / 100,
    weights: weights.slice(0, 8),
    dominant: weights[0]?.sid ?? null,
    vintage: v,
    n_refs: refs.length,
  };
}

const H = 10;

// The gate-passed calibration cell for a community at (age, observed pct), linearly interpolated
// between the bracketing grid points — only for a community whose calibration is gate-passed.
async function gatePassedCell(community: string, age: number, obs: number) {
  const rows = await query<any>(
    `select obs_pct_bin, eventual_median, ci_lo, ci_hi, p_ge50, p_ge75, p_ge90, p_ge95, p_ge99
       from calibration_models
      where community=$1 and age_years=$2 and model_version='qal-0.1' and confidence='gate-passed'
      order by obs_pct_bin`,
    [community, age]
  );
  if (!rows.length) return null;
  const gs = rows.map((r) => Number(r.obs_pct_bin));
  const mk = (r: any) => ({
    median: +r.eventual_median, q5: +r.ci_lo, q95: +r.ci_hi,
    ge50: +r.p_ge50, ge75: +r.p_ge75, ge90: +r.p_ge90, ge95: +r.p_ge95, ge99: +r.p_ge99,
  });
  if (obs <= gs[0]) return mk(rows[0]);
  if (obs >= gs[gs.length - 1]) return mk(rows[rows.length - 1]);
  const i = gs.findIndex((g) => g > obs);
  const c0 = mk(rows[i - 1]);
  const c1 = mk(rows[i]);
  const t = (obs - gs[i - 1]) / (gs[i] - gs[i - 1]);
  const lerp = (a: number, b: number) => a * (1 - t) + b * t;
  return {
    median: lerp(c0.median, c1.median), q5: lerp(c0.q5, c1.q5), q95: lerp(c0.q95, c1.q95),
    ge50: lerp(c0.ge50, c1.ge50), ge75: lerp(c0.ge75, c1.ge75), ge90: lerp(c0.ge90, c1.ge90),
    ge95: lerp(c0.ge95, c1.ge95), ge99: lerp(c0.ge99, c1.ge99),
  };
}

export interface SyntheticQal {
  obs: number;
  weights: { sid: string; weight: number }[];
  dominant: string | null;
  vintage: number;
  calibrated: boolean;
  coverage: "gate-passed" | "mature" | "observed";
  qal: { point: number; ci90: [number, number]; class_prob: ClassProb; buckets: ReturnType<typeof buckets> } | null;
}

// Full served synthetic-field QaL for a paper, on the fly: rank against the true community, then
// attribute the calibration to that community when it's gate-passed; else the maturity rule for a
// decided paper; else observed-only (calibration-pending).
export async function syntheticQal(oaid: string): Promise<SyntheticQal | null> {
  const sf = await syntheticField(oaid);
  if (!sf) return null;
  const obs = sf.obs;
  const rawAge = NOW - sf.vintage;
  const age = Math.max(1, Math.min(H - 1, rawAge));
  const base = { obs, weights: sf.weights, dominant: sf.dominant, vintage: sf.vintage };

  // (1) gate-passed forecast via the dominant true community
  const cell = sf.dominant ? await gatePassedCell(sf.dominant, age, obs) : null;
  if (cell) {
    const cp: ClassProb = { ge50: cell.ge50, ge75: cell.ge75, ge90: cell.ge90, ge95: cell.ge95, ge99: cell.ge99 };
    return {
      ...base, calibrated: true, coverage: "gate-passed",
      qal: { point: Math.round(cell.median), ci90: [Math.round(cell.q5), Math.round(cell.q95)], class_prob: cp, buckets: buckets(cp) },
    };
  }
  // (2) maturity rule — decided paper, QaL = observed standing
  if (rawAge >= H) {
    const q: QalPoint = { point: Math.round(obs), lo: Math.max(0, obs - 2.5), hi: Math.min(100, obs + 2.5) };
    const cp = classProb(q);
    return {
      ...base, calibrated: true, coverage: "mature",
      qal: { point: q.point, ci90: [Math.round(q.lo), Math.round(q.hi)], class_prob: cp, buckets: buckets(cp) },
    };
  }
  // (3) observed-only — correct reference class, but no gate-passed calibration yet
  return { ...base, calibrated: false, coverage: "observed", qal: null };
}
