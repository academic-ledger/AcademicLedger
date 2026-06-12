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
const MAX_CITERS = 200; // cap the co-citation scan (the fallback fires for few-citer papers anyway)
const NEIGH = 100; // top co-cited works kept for the community mixture
const MAX_AUTHORS = 5; // cap the author-prior fan-out (one OpenAlex call per author)
const AUTHOR_WORKS = 50; // recent works per author used to build the prior
const TOPIC_ALPHA = 0.55; // blend weight on the paper's OWN topics vs the author prior

export interface SynthResult {
  obs: number; // blended observed percentile (0–100)
  weights: { sid: string; weight: number }[]; // topic mixture (for the composition display)
  parts: { sid: string; weight: number; pct: number }[]; // used cohorts: weight (renormalized over
  // used) + the focal's percentile IN that subfield — the inputs to the blend-weighted calibration
  vintage: number;
  n_refs: number;
  basis: "references" | "co-citation" | "author-prior"; // how the community was inferred
}

// Co-citation fallback: when a paper has no bibliography in OpenAlex (common for SSRN/working
// papers), infer its community from the works that CITE it and what those citers co-reference.
// Returns a subfield -> co-citation-count mixture. Cheap because the fallback only fires for
// few-citer papers (papers with many citers usually have a reference list).
async function cocitationWeights(oaid: string): Promise<Record<string, number> | null> {
  const focalUrl = `https://openalex.org/${oaid}`;
  const counts: Record<string, number> = {}; // co-cited oaid -> times co-cited with the focal
  let cursor: string | null = "*";
  let nCiters = 0;
  while (cursor && nCiters < MAX_CITERS) {
    const d: any = await oaGet(
      `/works?filter=cites:${oaid}&select=id,referenced_works&per-page=200&cursor=${encodeURIComponent(cursor)}`
    );
    const results = d?.results ?? [];
    if (!results.length) break;
    for (const w of results) {
      nCiters++;
      for (const r of w.referenced_works || []) {
        if (r !== focalUrl) {
          const id = (r as string).split("/").pop() as string;
          counts[id] = (counts[id] || 0) + 1;
        }
      }
    }
    cursor = d?.meta?.next_cursor ?? null;
  }
  if (!nCiters) return null;
  const top = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, NEIGH).map(([id]) => id);
  if (!top.length) return null;
  const subYear = await worksSubYear(top);
  const w: Record<string, number> = {};
  for (const id of top) {
    const sy = subYear.get(id);
    if (sy && sy[0]) w[sy[0]] = (w[sy[0]] || 0) + counts[id];
  }
  return Object.keys(w).length ? w : null;
}

function normMix(o: Record<string, number>): Record<string, number> {
  const s = Object.values(o).reduce((a, b) => a + b, 0);
  return s ? Object.fromEntries(Object.entries(o).map(([k, x]) => [k, x / s])) : {};
}

// Author-prior fallback: the weakest stage of the signal chain (QaL_spec §5), fired only when a
// paper has neither a usable bibliography NOR citers — a brand-new SSRN/working paper. We infer the
// community from CONTENT + AUTHORS: blend the paper's own OpenAlex topic mixture (about THIS paper)
// with the recency-weighted bodies of work of its authors (a backstop that supplies breadth). Each
// author is normalized to unit mass first, so a prolific co-author doesn't swamp the others.
async function authorPriorWeights(focal: any): Promise<Record<string, number> | null> {
  const v: number = focal.publication_year ?? NOW;

  // (a) content signal: the paper's own OpenAlex topics -> subfield distribution, weighted by score
  const topicMix: Record<string, number> = {};
  for (const t of focal.topics || []) {
    const sid = ((t.subfield?.id || "") as string).split("/").pop();
    if (sid) topicMix[sid] = (topicMix[sid] || 0) + (t.score ?? 0);
  }

  // (b) author prior: each author's recency-weighted subfield mixture, one OpenAlex call per author
  const authorIds: string[] = (focal.authorships || [])
    .map((a: any) => ((a.author?.id || "") as string).split("/").pop())
    .filter(Boolean)
    .slice(0, MAX_AUTHORS);
  const authorMix: Record<string, number> = {};
  for (const aid of authorIds) {
    const d = await oaGet(
      `/works?filter=author.id:${aid}&select=primary_topic,publication_year&per-page=${AUTHOR_WORKS}&sort=publication_year:desc`
    );
    const per: Record<string, number> = {};
    for (const wk of d?.results ?? []) {
      const sid = ((wk.primary_topic?.subfield?.id || "") as string).split("/").pop();
      if (!sid) continue;
      const g = Math.exp(-Math.max(0, v - (wk.publication_year ?? v)) / TAU);
      per[sid] = (per[sid] || 0) + g;
    }
    const np = normMix(per); // unit mass per author
    for (const sid in np) authorMix[sid] = (authorMix[sid] || 0) + np[sid];
  }

  const tm = normMix(topicMix);
  const am = normMix(authorMix);
  const hasT = Object.keys(tm).length > 0;
  const hasA = Object.keys(am).length > 0;
  if (!hasT && !hasA) return null;
  const a = hasT && hasA ? TOPIC_ALPHA : hasT ? 1 : 0; // lean fully on whichever side exists
  const out: Record<string, number> = {};
  for (const sid in tm) out[sid] = (out[sid] || 0) + a * tm[sid];
  for (const sid in am) out[sid] = (out[sid] || 0) + (1 - a) * am[sid];
  return Object.keys(out).length ? out : null;
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
      const url = `${OA}${pathWithQuery}${AUTH}`;
      const init = {
        headers: { "User-Agent": `al-web/1.0 (${MAILTO})` },
        next: { revalidate: REVALIDATE },
      };
      let r = await fetch(url, init);
      // Premium budget is shared with the batch pipeline; on a 429 "Insufficient budget" fall back
      // to the free polite pool (key stripped) so paper pages keep computing the synthetic field.
      if (r.status === 429 && API_KEY && url.includes(`api_key=${encodeURIComponent(API_KEY)}`)) {
        r = await fetch(url.replace(`&api_key=${encodeURIComponent(API_KEY)}`, ""), init);
      }
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
    `/works/${encodeURIComponent(oaid)}?select=id,referenced_works,publication_year,cited_by_count,authorships,topics`
  );
  if (!focal) return null;
  const v: number = focal.publication_year ?? NOW;
  const cites: number = focal.cited_by_count ?? 0;
  const refs: string[] = (focal.referenced_works || []).map((r: string) => r.split("/").pop());

  // Community mixture: the recency-weighted subfields of the bibliography (reference stage); but
  // when OpenAlex has no/too-few references (SSRN/working papers), fall back to the co-citation
  // stage — infer the community from the works that cite it.
  let w: Record<string, number> = {};
  let basis: "references" | "co-citation" | "author-prior" = "references";
  if (refs.length >= MIN_REFS) {
    const subYear = await worksSubYear(refs);
    for (const [sid, y] of subYear.values()) {
      if (!sid) continue;
      const g = Math.exp(-Math.max(0, v - (y ?? v)) / TAU);
      w[sid] = (w[sid] || 0) + g;
    }
  } else {
    const cc = await cocitationWeights(oaid);
    if (cc) {
      w = cc;
      basis = "co-citation";
    } else {
      // last resort: infer the community from the paper's own topics + its authors' bodies of work
      const ap = await authorPriorWeights(focal);
      if (!ap) return null; // no references, no citers, no topics/authors -> can't place it
      w = ap;
      basis = "author-prior";
    }
  }
  const tot = Object.values(w).reduce((a, b) => a + b, 0);
  if (!tot) return null;
  const weights = Object.entries(w)
    .map(([sid, x]) => ({ sid, weight: x / tot }))
    .sort((a, b) => b.weight - a.weight);

  // rank the focal against the weight-blended cohort distribution (subfields carrying >=2%),
  // keeping each used subfield's weight + the focal's percentile in it (for the calibration blend)
  const keep = weights.filter((x) => x.weight >= 0.02);
  const used: { sid: string; weight: number; pct: number }[] = [];
  let r = 0;
  let wused = 0;
  for (const { sid, weight } of keep) {
    const pct = await pctInCohort(sid, v, cites);
    if (pct == null) continue;
    used.push({ sid, weight, pct });
    r += weight * pct;
    wused += weight;
  }
  if (wused < 0.5) return null; // most weight had no rankable cohort -> abstain

  return {
    obs: Math.round((r / wused) * 100) / 100,
    weights: weights.slice(0, 8),
    parts: used.map((p) => ({ sid: p.sid, weight: p.weight / wused, pct: p.pct })),
    vintage: v,
    n_refs: refs.length,
    basis,
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
  basis: "references" | "co-citation" | "author-prior";
  gp_weight: number; // share of the reference class sitting in back-tested (gate-passed) subfields
  calibrated: boolean;
  coverage: "gate-passed" | "mature" | "observed";
  qal: { point: number; ci90: [number, number]; class_prob: ClassProb; buckets: ReturnType<typeof buckets> } | null;
}

// Minimum share of the reference class that must sit in back-tested subfields to show a forecast.
const GP_MIN = 0.5;

// Full served synthetic-field QaL for a paper, on the fly. BLEND-WEIGHTED calibration (not a
// single-label swap): apply EACH constituent subfield's calibration to the focal's percentile in
// THAT subfield, then blend the posteriors by the synthetic-field weights. Confidence is
// blend-weighted — gate-passed to the extent the weight sits in back-tested subfields; "pending"
// (observed-only) appears only when the bulk of the weight lands in subfields we haven't
// calibrated. The maturity rule still applies to decided papers.
export async function syntheticQal(oaid: string): Promise<SyntheticQal | null> {
  const sf = await syntheticField(oaid);
  if (!sf) return null;
  const obs = sf.obs;
  const rawAge = NOW - sf.vintage;
  const age = Math.max(1, Math.min(H - 1, rawAge));
  const base = {
    obs, weights: sf.weights, dominant: sf.parts[0]?.sid ?? null, vintage: sf.vintage, basis: sf.basis,
  };

  // blend each gate-passed subfield's posterior (its calibration applied to the focal's percentile
  // in that subfield), weighted by the synthetic-field weights; gpW = total gate-passed weight.
  let gpW = 0;
  let m = 0, q5 = 0, q95 = 0;
  const acc: ClassProb = { ge50: 0, ge75: 0, ge90: 0, ge95: 0, ge99: 0 };
  for (const { sid, weight, pct } of sf.parts) {
    const cell = await gatePassedCell(sid, age, pct);
    if (!cell) continue; // this subfield isn't back-tested -> its share contributes no forecast
    gpW += weight;
    m += weight * cell.median;
    q5 += weight * cell.q5;
    q95 += weight * cell.q95;
    acc.ge50 += weight * cell.ge50;
    acc.ge75 += weight * cell.ge75;
    acc.ge90 += weight * cell.ge90;
    acc.ge95 += weight * cell.ge95;
    acc.ge99 += weight * cell.ge99;
  }
  const gp_weight = Math.round(gpW * 100) / 100;

  // (1) enough of the reference class is back-tested -> blended gate-passed forecast
  if (gpW >= GP_MIN) {
    const n = (x: number) => x / gpW; // renormalize over the gate-passed weight
    const cp: ClassProb = {
      ge50: Math.round(n(acc.ge50) * 100) / 100, ge75: Math.round(n(acc.ge75) * 100) / 100,
      ge90: Math.round(n(acc.ge90) * 100) / 100, ge95: Math.round(n(acc.ge95) * 100) / 100,
      ge99: Math.round(n(acc.ge99) * 100) / 100,
    };
    return {
      ...base, gp_weight, calibrated: true, coverage: "gate-passed",
      qal: { point: Math.round(n(m)), ci90: [Math.round(n(q5)), Math.round(n(q95))], class_prob: cp, buckets: buckets(cp) },
    };
  }
  // (2) maturity rule — decided paper, QaL = observed standing
  if (rawAge >= H) {
    const q: QalPoint = { point: Math.round(obs), lo: Math.max(0, obs - 2.5), hi: Math.min(100, obs + 2.5) };
    const cp = classProb(q);
    return {
      ...base, gp_weight, calibrated: true, coverage: "mature",
      qal: { point: q.point, ci90: [Math.round(q.lo), Math.round(q.hi)], class_prob: cp, buckets: buckets(cp) },
    };
  }
  // (3) observed-only — correct reference class, but the bulk of its weight isn't calibrated yet
  return { ...base, gp_weight, calibrated: false, coverage: "observed", qal: null };
}
