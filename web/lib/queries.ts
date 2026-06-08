import { query } from "./db";
import type { AuthorPayload, Metrics, MetricView, RecordItem } from "./types";
import { buckets, classProb, type QalPoint } from "./qal";

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

const RECORD_SELECT = `
  select w.oaid,
         w.title,
         w.doi,
         w.publication_year as year,
         w.primary_subfield as sid,
         w.primary_field    as field,
         w.cited_by_count   as cites,
         w.is_oa            as oa,
         w.is_retracted     as retracted,
         w.raw->>'authors'        as authors,
         w.raw->>'venue'          as venue,
         w.raw->>'subfield_label' as subfield,
         q.obs_percentile   as obs,
         q.calibrated       as calibrated,
         q.qal_point        as qal_point,
         q.qal_ci_lo        as qal_ci_lo,
         q.qal_ci_hi        as qal_ci_hi,
         q.reference_class  as reference_class,
         q.class_prob       as class_prob,
         q.metrics          as metrics
  from works w
  left join qal_records q on q.oaid = w.oaid
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
    where.push(`w.primary_subfield = $${args.length}`);
  }
  if (p.since) {
    args.push(p.since);
    where.push(`w.publication_year >= $${args.length}`);
  }
  if (p.q) {
    args.push(`%${p.q.toLowerCase()}%`);
    where.push(`(lower(w.title) like $${args.length} or lower(w.raw->>'authors') like $${args.length})`);
  }
  if (p.calibrated_only) {
    where.push(`q.calibrated is true`);
  }
  const order =
    p.sort === "cites"
      ? "w.cited_by_count desc nulls last"
      : p.sort === "year"
      ? "w.publication_year desc nulls last"
      : "q.qal_point desc nulls last, w.cited_by_count desc nulls last";
  const limit = Math.min(Math.max(p.limit ?? 200, 1), 1000);
  args.push(limit);
  const sql =
    RECORD_SELECT +
    (where.length ? ` where ${where.join(" and ")}` : "") +
    ` order by ${order} limit $${args.length}`;
  const rows = await query(sql, args);
  return rows.map(mapRow);
}

// Contract shape for GET /api/qal/:oaid
export async function getQalRecord(oaid: string) {
  const rows = await query(RECORD_SELECT + ` where w.oaid = $1`, [oaid]);
  if (!rows.length) return null;
  const rec = mapRow(rows[0]);
  const raw = rows[0];

  const reference_class = raw.reference_class ?? {
    field: rec.sid ? `subfields/${rec.sid}` : null,
    field_label: rec.subfield,
    vintage_year: rec.year,
    n: null,
  };

  const base = {
    oaid: rec.oaid,
    doi: rec.doi,
    title: rec.title,
    authors: rec.authors,
    year: rec.year,
    venue: rec.venue,
    subfield: rec.subfield,
    field: rec.field,
    reference_class,
    obs_percentile: rec.obs,
    calibrated: rec.calibrated,
    evidence: {
      cited_by_count: rec.cites,
      is_oa: rec.oa,
      is_retracted: rec.retracted,
    },
    method_version: "qal-0.1",
    data_snapshot: "openalex-2026-05",
  };

  if (!rec.calibrated || !rec.qal) {
    // calibration-pending: surface observed standing only, omit qal
    return { ...base, status: "calibration-pending" as const };
  }

  // Prefer the real calibration masses stored by compute_qal; fall back to the
  // normal-approximation only when they're absent (e.g. demo-seeded rows).
  const cp = raw.class_prob ?? classProb(rec.qal);
  return {
    ...base,
    qal: {
      point: rec.qal.point,
      ci90: [rec.qal.lo, rec.qal.hi] as [number, number],
      class_prob: cp,
      buckets: buckets(cp),
    },
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
      ` join author_works aw on aw.work_oaid = w.oaid
        where aw.author_oaid = $1
        order by w.cited_by_count desc nulls last`,
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
