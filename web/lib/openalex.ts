// Live OpenAlex work fetch for the paper page (QaL_spec §11 cheap-path). Keeps the displayed
// metadata current — title, byline, citations — so stored snapshots can't go stale. Cached
// via Next fetch revalidation so repeat views don't re-hit the API.

const MAILTO = process.env.OPENALEX_MAILTO || "ktulrich@gmail.com";
const API_KEY = process.env.OPENALEX_API_KEY || ""; // premium key: lifts the daily list budget
const AUTH = `&mailto=${encodeURIComponent(MAILTO)}${API_KEY ? `&api_key=${encodeURIComponent(API_KEY)}` : ""}`;
const REVALIDATE = 60 * 60 * 24; // 1 day

export interface Work {
  oaid: string;
  doi: string | null;
  title: string | null;
  year: number | null;
  authors: string | null; // §12: all co-authors when < 11, else "First author et al."
  venue: string | null;
  sid: string | null; // primary subfield id
  subfield: string | null; // primary subfield label
  field: string | null; // primary field label
  cites: number;
  is_oa: boolean;
  is_retracted: boolean;
  n_refs: number;
  biblio: { volume?: string | null; issue?: string | null; first_page?: string | null; last_page?: string | null } | null;
}

function byline(authorships: any[]): string | null {
  const names = (authorships || [])
    .map((a) => a?.author?.display_name)
    .filter(Boolean) as string[];
  if (!names.length) return null;
  return names.length < 11 ? names.join(", ") : `${names[0]} et al.`;
}

function mapWork(w: any, fallbackId = ""): Work {
  const pt = w.primary_topic || {};
  const sub = pt.subfield || {};
  return {
    oaid: (w.id || "").split("/").pop() || fallbackId,
    doi: w.doi || null,
    title: w.title || null,
    year: w.publication_year ?? null,
    authors: byline(w.authorships),
    venue: w.primary_location?.source?.display_name ?? null,
    sid: (sub.id || "").split("/").pop() || null,
    subfield: sub.display_name ?? null,
    field: pt.field?.display_name ?? null,
    cites: w.cited_by_count ?? 0,
    is_oa: !!w.open_access?.is_oa,
    is_retracted: !!w.is_retracted,
    n_refs: (w.referenced_works || []).length,
    biblio: w.biblio || null,
  };
}

export async function fetchWork(oaid: string): Promise<Work | null> {
  const select =
    "id,doi,title,publication_year,primary_topic,primary_location,authorships," +
    "cited_by_count,biblio,open_access,is_retracted,referenced_works";
  const url =
    `https://api.openalex.org/works/${encodeURIComponent(oaid)}` +
    `?select=${select}${AUTH}`;
  let r: Response;
  try {
    r = await fetch(url, {
      headers: { "User-Agent": `al-web/1.0 (${MAILTO})` },
      next: { revalidate: REVALIDATE },
    });
  } catch {
    return null;
  }
  if (!r.ok) return null;
  return mapWork(await r.json(), oaid);
}

// Live discovery for explore (backlog U8): when the indexed set has no match, search OpenAlex
// directly so famous authors / papers outside our sampled cohorts are still found. Runs a title
// search AND an author-name search and merges (the explore box is "title OR author"). Subfield is
// filtered client-side on the mapped result (robust to OpenAlex topic-filter syntax quirks); the
// `since` vintage uses the documented from_publication_date filter. Quota note: the /works LIST
// endpoint shares OpenAlex's daily list quota (unlike single-entity fetch), so results are cached
// via Next fetch revalidation. Returns [] on any error / rate-limit so the page still renders.
const SEARCH_REVALIDATE = 60 * 60; // 1 hour
const SEARCH_PER = 25;

async function searchOne(filter: string): Promise<any[]> {
  const select =
    "id,doi,title,publication_year,primary_topic,primary_location,authorships," +
    "cited_by_count,open_access,is_retracted";
  const url =
    `https://api.openalex.org/works?filter=${filter}&select=${select}` +
    `&per-page=${SEARCH_PER}&sort=cited_by_count:desc${AUTH}`;
  try {
    const r = await fetch(url, {
      headers: { "User-Agent": `al-web/1.0 (${MAILTO})` },
      next: { revalidate: SEARCH_REVALIDATE },
    });
    if (!r.ok) return [];
    const j: any = await r.json();
    return j.results || [];
  } catch {
    return [];
  }
}

export async function searchWorks(
  q: string,
  opts: { since?: number | null } = {}
): Promise<Work[]> {
  const term = q.trim();
  if (!term) return [];
  const enc = encodeURIComponent(term);
  const base: string[] = [];
  if (opts.since) base.push(`from_publication_date:${opts.since}-01-01`);
  const filters = [
    [...base, `raw_author_name.search:${enc}`].join(","),
    [...base, `title.search:${enc}`].join(","),
  ];
  const merged = new Map<string, Work>();
  for (const f of filters) {
    for (const raw of await searchOne(f)) {
      const w = mapWork(raw);
      if (w.oaid && !merged.has(w.oaid)) merged.set(w.oaid, w);
    }
  }
  return [...merged.values()].sort((a, b) => b.cites - a.cites);
}
