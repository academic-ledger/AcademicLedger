import { query } from "./db";

// User-data side of the community-layer overlay. These tables are SEPARATE from the metric/data
// tables (works, cohort_percentiles, calibration_models, qal_records, synthetic_field) and are
// never joined into or written alongside them here. No password is ever stored.
//
// The public ORCID API (no member scope, no auth) gives us a member's public works keyed by their
// iD; sandbox vs prod via ORCID_API_BASE (set alongside ORCID_ISSUER).
const ORCID_API_BASE = process.env.ORCID_API_BASE ?? "https://pub.sandbox.orcid.org";

// Lazy provisioning (CREATE TABLE IF NOT EXISTS), mirroring synthetic_cache. The numbered migration
// db/migrations/007_users.sql is the source of record; this lets the surface come up on first login
// without a separate migration run (this network can't reach Neon to run one).
let _ready = false;
async function ensureTables(): Promise<void> {
  if (_ready) return;
  await query(`create table if not exists users (
    id            serial primary key,
    orcid_id      text unique not null,
    display_name  text,
    created_at    timestamptz not null default now(),
    last_login_at timestamptz not null default now()
  )`);
  await query(`create table if not exists orcid_works (
    user_id    integer not null references users(id) on delete cascade,
    put_code   text not null,
    doi        text,
    title      text,
    fetched_at timestamptz not null default now(),
    primary key (user_id, put_code)
  )`);
  _ready = true;
}

interface OrcidWork {
  put_code: string;
  doi: string | null;
  title: string | null;
}

// Read the member's PUBLIC works from the ORCID API (DOIs + ORCID put-codes), for C2/C3 to use
// later. Best-effort: any failure returns [] so login is never blocked.
async function fetchOrcidWorks(orcid: string): Promise<OrcidWork[]> {
  try {
    const r = await fetch(`${ORCID_API_BASE}/v3.0/${orcid}/works`, {
      headers: { Accept: "application/json" },
    });
    if (!r.ok) return [];
    const data: any = await r.json();
    const out: OrcidWork[] = [];
    for (const g of data.group ?? []) {
      const s = (g["work-summary"] ?? [])[0];
      if (!s || s["put-code"] == null) continue;
      let doi: string | null = null;
      for (const e of s["external-ids"]?.["external-id"] ?? []) {
        if (String(e["external-id-type"] || "").toLowerCase() === "doi") {
          doi = String(e["external-id-value"] || "").toLowerCase();
          break;
        }
      }
      out.push({
        put_code: String(s["put-code"]),
        doi,
        title: s.title?.title?.value ?? null,
      });
    }
    return out;
  } catch {
    return [];
  }
}

// ── TEMPORARY C1 auth-error capture (remove before merge) ────────────────────────────────────
// Vercel function logs are awkward to read, so the NextAuth logger also records errors here and
// /api/auth-debug reads them back. Best-effort; never throws.
export async function recordAuthError(message: string, detail: string | null): Promise<void> {
  try {
    await query(`create table if not exists _auth_debug (
      id serial primary key, at timestamptz not null default now(), message text, detail text
    )`);
    await query(`insert into _auth_debug (message, detail) values ($1, $2)`, [
      (message ?? "").slice(0, 2000),
      (detail ?? "")?.slice(0, 6000) || null,
    ]);
  } catch {
    /* best-effort */
  }
}
export async function recentAuthErrors(): Promise<any[]> {
  try {
    return await query(`select at, message, detail from _auth_debug order by id desc limit 5`);
  } catch {
    return [];
  }
}

// On login: upsert the user (keyed by ORCID iD) and refresh their cached works. Touches only
// `users` and `orcid_works`.
export async function upsertUserAndCacheWorks(orcid: string, name: string | null): Promise<void> {
  await ensureTables();
  const rows = await query<{ id: number }>(
    `insert into users (orcid_id, display_name, last_login_at)
       values ($1, $2, now())
     on conflict (orcid_id) do update
       set display_name  = coalesce(excluded.display_name, users.display_name),
           last_login_at = now()
     returning id`,
    [orcid, name]
  );
  const userId = rows[0].id;

  const works = await fetchOrcidWorks(orcid);
  if (!works.length) return; // ORCID returned nothing -> keep any prior cache, don't wipe it
  await query(`delete from orcid_works where user_id = $1`, [userId]);
  for (const w of works) {
    await query(
      `insert into orcid_works (user_id, put_code, doi, title)
         values ($1, $2, $3, $4)
       on conflict (user_id, put_code) do nothing`,
      [userId, w.put_code, w.doi, w.title]
    );
  }
}
