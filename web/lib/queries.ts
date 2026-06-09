import { query } from "./db";
import type { AuthorPayload, Metrics, MetricView, RecordItem } from "./types";
import { buckets, classProb, type QalPoint } from "./qal";
import { fetchWork } from "./openalex";

const SEED = new Set(["1800", "1802", "1803"]);
const H = 10;
const AS_OF = 2026;

// Full-population mid-rank percentile of `cites` within a (subfield, year) cohort, read from
// the precomputed cohort_percentiles CDF (already mid-rank). Floor lookup; no API call.
async function cohortPercentile(sid: string, year: number, cites: number): Promise<number | null> {
  const rows = await query<{ cdf: { cites: number; pct: number }[] }>(
    `select cdf from cohort_percentiles where subfield=$1 and publication_year=$2
       order by snapshot desc limit 1`,
    [sid, year]
  );
  const cdf = rows.length ? rows[0].cdf : null;
  if (!cdf || !cdf.length) return null;
  let pct = 0;
  for (const bp of cdf) {
    if (bp.cites <= cites) pct = bp.pct;
    else break;
  }
  return Math.round(pct * 100) / 100;
}

function toMetric(m: any): MetricView | null {
  if (!m) return null;
  return {
    obs: Number(m.obs),
    calibrated: !!m.calibrated,
    n: m.n != null ? Number(m.n) : undefined,
    qal: m.point != null ? { point: Number(m.point), lo: Number(m.ci_lo), hi: Number(m.ci_hi) } : null,
  };
}

function toMetrics(raw: any): Metrics | null {
  if (!raw) return null;
  return {
    field: toMetric(raw.field),
    synthetic: toMetric(raw.synthetic),
    official: raw.official === "synthetic" ? "synthetic" : "field",
  };
}

// The seed subfields covering the OID department (QaL_spec.md §5).
export const SEED_SUBFIELDS = ["1803", "1802", "1800"];

// Served entirely from qal_records (the cache); display fields are folded into q.display, so
// serving no longer reads the raw works snapshot (caching_architecture.md).
const RECORD_SELECT = `
  select q.oaid,
         q.display->>'title'                as title,
         q.display->>'doi'                  as doi,
         (q.display->>'year')::int          as year,
         q.display->>'sid'                  as sid,
         q.display->>'field'                as field,
         (q.display->>'cites')::int         as cites,
         (q.display->>'oa')::boolean        as oa,
         (q.display->>'retracted')::boolean as retracted,
         q.display->>'authors'              as authors,
         q.display->>'venue'                as venue,
         q.display->>'subfield'             as subfield,
         q.obs_percentile   as obs,
         q.calibrated       as calibrated,
         q.qal_point        as qal_point,
         q.qal_ci_lo        as qal_ci_lo,
         q.qal_ci_hi        as qal_ci_hi,
         q.reference_class  as reference_class,
         q.class_prob       as class_prob,
         q.metrics          as metrics
  from qal_records q
`;

function mapRow(r: any): RecordItem {
  const qal: QalPoint | null =
    r.qal_point != null
      ? { point: Number(r.qal_point), lo: Number(r.qal_ci_lo), hi: Number(r.qal_ci_hi) }
      : null;
  return {
    oaid: r.oaid,
    title: r.title,
    authors: r.authors ?? null,
    venue: r.venue ?? null,
    year: r.year ?? null,
    cites: r.cites ?? 0,
    sid: r.sid ?? null,
    subfield: r.subfield ?? null,
    field: r.field ?? null,
    oa: !!r.oa,
    doi: r.doi ?? null,
    retracted: !!r.retracted,
    obs: r.obs != null ? Number(r.obs) : null,
    calibrated: !!r.calibrated,
    qal,
    metrics: toMetrics(r.metrics),
  };
}

export interface ExploreParams {
  field?: string; // subfield id
  since?: number;
  q?: string;
  calibrated_only?: boolean;
  sort?: "qal" | "cites" | "year";
  limit?: number;
}

export async function getExplore(p: ExploreParams): Promise<RecordItem[]> {
  const where: string[] = [];
  const args: any[] = [];
  if (p.field) {
    args.push(p.field);
    where.push(`q.display->>'sid' = $${args.length}`);
  }
  if (p.since) {
    args.push(p.since);
    where.push(`(q.display->>'year')::int >= $${args.length}`);
  }
  if (p.q) {
    args.push(`%${p.q.toLowerCase()}%`);
    where.push(`(lower(q.display->>'title') like $${args.length} or lower(q.display->>'authors') like $${args.length})`);
  }
  if (p.calibrated_only) {
    where.push(`q.calibrated is true`);
  }
  const order =
    p.sort === "cites"
      ? "(q.display->>'cites')::int desc nulls last"
      : p.sort === "year"
      ? "(q.display->>'year')::int desc nulls last"
      : "q.qal_point desc nulls last, (q.display->>'cites')::int desc nulls last";
  const limit = Math.min(Math.max(p.limit ?? 200, 1), 1000);
  args.push(limit);
  const sql =
    RECORD_SELECT +
    (where.length ? ` where ${where.join(" and ")}` : "") +
    ` order by ${order} limit $${args.length}`;
  const rows = await query(sql, args);
  return rows.map(mapRow);
}

// Synthetic-field composition (U3): the paper's reference-class blend as ranked
// {subfield, name, weight}, names resolved from the `subfields` table (queried fresh —
// small — so taxonomy fills picked up without a redeploy).
async function getComposition(oaid: string) {
  const rows = await query<{ weights: Record<string, number> | null }>(
    `select weights from synthetic_field where oaid = $1`,
    [oaid]
  );
  const w = rows.length ? rows[0].weights : null;
  if (!w) return null;
  const names = await query<{ id: string; name: string }>(`select id, name from subfields`);
  const nameMap = new Map(names.map((r) => [r.id, r.name]));
  return Object.entries(w)
    .map(([sid, weight]) => ({ sid, name: nameMap.get(sid) ?? `Subfield ${sid}`, weight: Number(weight) }))
    .sort((a, b) => b.weight - a.weight)
    .slice(0, 8);
}

// GET /api/qal/:oaid + the paper page — constructed ON THE FLY (paper_page_construction.md):
// display is fetched LIVE from OpenAlex (never stale), QaL numbers come from the cached
// qal_records (batch-computed, monthly refresh), composition from the synthetic_field cache.
// Uncomputed papers get the universal layer (observed field percentile) + calibration-pending.
// Fall back to the stored snapshot when the live fetch fails (OpenAlex down / rate-limited /
// unknown id) so the page always renders — live when possible, cached otherwise.
async function storedWork(oaid: string) {
  const rows = await query<any>(`select display from qal_records where oaid = $1`, [oaid]);
  const d = rows.length ? rows[0].display : null;
  if (!d) return null;
  return {
    oaid, doi: d.doi ?? null, title: d.title ?? null, year: d.year ?? null,
    authors: d.authors ?? null, venue: d.venue ?? null, sid: d.sid ?? null,
    subfield: d.subfield ?? null, field: d.field ?? null, cites: d.cites ?? 0,
    is_oa: !!d.oa, is_retracted: !!d.retracted, n_refs: 0, biblio: null,
  };
}

export async function getPaperRecord(oaid: string) {
  const work = (await fetchWork(oaid)) ?? (await storedWork(oaid));
  if (!work) return null;

  const cached = await query<any>(
    `select obs_percentile, calibrated, qal_point, qal_ci_lo, qal_ci_hi,
            class_prob, reference_class, metrics
       from qal_records where oaid = $1`,
    [oaid]
  );
  const c = cached.length ? cached[0] : null;
  const composition = await getComposition(oaid);

  const base = {
    oaid: work.oaid,
    doi: work.doi,
    title: work.title,
    authors: work.authors, // live, §12-correct byline
    year: work.year,
    venue: work.venue,
    subfield: work.subfield, // live OpenAlex labels
    field: work.field,
    biblio: work.biblio,
    composition,
    evidence: {
      cited_by_count: work.cites, // live
      is_oa: work.is_oa,
      is_retracted: work.is_retracted,
    },
    method_version: "qal-0.1",
    data_snapshot: "openalex (live display + cached QaL)",
  };

  // Calibrated: serve the cached posterior; display is the live work.
  if (c && c.calibrated && c.qal_point != null) {
    const qal: QalPoint = { point: Number(c.qal_point), lo: Number(c.qal_ci_lo), hi: Number(c.qal_ci_hi) };
    const cp = c.class_prob ?? classProb(qal);
    const ref = c.reference_class ?? {};
    return {
      ...base,
      reference_class: {
        ...ref,
        field_label: ref.field_label ?? work.subfield,
      },
      obs_percentile: c.obs_percentile != null ? Number(c.obs_percentile) : null,
      calibrated: true,
      qal: { point: qal.point, ci90: [qal.lo, qal.hi] as [number, number], class_prob: cp, buckets: buckets(cp) },
    };
  }

  // Universal layer: observed field percentile on the fly, calibration-pending.
  let obs: number | null = c && c.obs_percentile != null ? Number(c.obs_percentile) : null;
  if (obs == null && work.sid && work.year != null) {
    obs = await cohortPercentile(work.sid, work.year, work.cites);
  }
  const ref = (c && c.reference_class) || {
    field: work.sid ? `subfields/${work.sid}` : null,
    field_label: work.subfield,
    kind: "field",
    vintage_year: work.year,
  };
  return {
    ...base,
    reference_class: { ...ref, field_label: ref.field_label ?? work.subfield },
    obs_percentile: obs,
    calibrated: false,
    status: "calibration-pending" as const,
  };
}

// Contract shape for GET /api/author/:oaid
export async function getAuthor(oaid: string): Promise<AuthorPayload | null> {
  const headers = await query(
    `select oaid, display_name, affiliation, orcid, works_count, cited_by_count, seed
       from authors where oaid = $1`,
    [oaid]
  );
  if (!headers.length) return null;
  const h = headers[0];
  const works = await query(
    RECORD_SELECT +
      ` join author_works aw on aw.work_oaid = q.oaid
        where aw.author_oaid = $1
        order by (q.display->>'cites')::int desc nulls last`,
    [oaid]
  );
  return {
    author: {
      name: h.display_name,
      aff: h.affiliation,
      orcid: h.orcid,
      oaid: h.oaid,
      works_count: h.works_count,
      cites: h.cited_by_count,
      seed: h.seed ?? SEED_SUBFIELDS,
    },
    works: works.map(mapRow),
  };
}

// A reasonable default author for the /author landing (the project initiator).
export async function getDefaultAuthorId(): Promise<string | null> {
  const rows = await query(`select oaid from authors order by cited_by_count desc limit 1`);
  return rows.length ? rows[0].oaid : null;
}
