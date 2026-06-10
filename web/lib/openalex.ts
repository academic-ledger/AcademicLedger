// Live OpenAlex work fetch for the paper page (QaL_spec §11 cheap-path). Keeps the displayed
// metadata current — title, byline, citations — so stored snapshots can't go stale. Cached
// via Next fetch revalidation so repeat views don't re-hit the API.

import type { Authorship } from "./types";

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
  authorships: Authorship[]; // per-author identity (id + orcid) for clickable bylines
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

function mapAuthorships(raw: any[]): Authorship[] {
  return (raw || [])
    .map((a) => ({
      name: a?.author?.display_name as string,
      oaid: ((a?.author?.id || "").split("/").pop() as string) || null,
      orcid: a?.author?.orcid || null,
    }))
    .filter((a) => a.name);
}

// §12 display rule: all co-authors when < 11, else "First author et al."
function bylineStr(ships: Authorship[]): string | null {
  if (!ships.length) return null;
  return ships.length < 11 ? ships.map((s) => s.name).join(", ") : `${ships[0].name} et al.`;
}

function mapWork(w: any, fallbackId = ""): Work {
  const pt = w.primary_topic || {};
  const sub = pt.subfield || {};
  const ships = mapAuthorships(w.authorships);
  return {
    oaid: (w.id || "").split("/").pop() || fallbackId,
    doi: w.doi || null,
    title: w.title || null,
    year: w.publication_year ?? null,
    authors: bylineStr(ships),
    authorships: ships,
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

// ---- Author entity (for the on-the-fly author page; QaL_spec §11 "Author view") -------------

export interface AuthorEntity {
  oaid: string;
  name: string | null;
  affiliation: string | null;
  orcid: string | null;
  works_count: number | null;
  cited_by_count: number | null;
}

export async function fetchAuthor(oaid: string): Promise<AuthorEntity | null> {
  const select = "id,display_name,orcid,last_known_institutions,works_count,cited_by_count";
  const url =
    `https://api.openalex.org/authors/${encodeURIComponent(oaid)}?select=${select}${AUTH}`;
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
  const a: any = await r.json();
  const inst = (a.last_known_institutions || [])[0];
  return {
    oaid: (a.id || "").split("/").pop() || oaid,
    name: a.display_name ?? null,
    affiliation: inst?.display_name ?? null,
    orcid: a.orcid ?? null,
    works_count: a.works_count ?? null,
    cited_by_count: a.cited_by_count ?? null,
  };
}

// Author typeahead for the author-search box. OpenAlex's purpose-built autocomplete endpoint
// returns, per keystroke, the display name + `hint` (the author's institution) + counts.
export interface AuthorSuggestion {
  oaid: string;
  name: string;
  institution: string | null; // OpenAlex `hint`
  works_count: number | null;
  cited_by_count: number | null;
  orcid: string | null;
}

async function _authorsList(url: string, map: (x: any) => AuthorSuggestion): Promise<AuthorSuggestion[]> {
  try {
    const r = await fetch(url, {
      headers: { "User-Agent": `al-web/1.0 (${MAILTO})` },
      next: { revalidate: SEARCH_REVALIDATE },
    });
    if (!r.ok) return [];
    const j: any = await r.json();
    return ((j.results || []) as any[]).map(map).filter((s) => s.oaid && s.name);
  } catch {
    return [];
  }
}

// Hybrid typeahead. The `/authors?search=` endpoint has the recall and citation ranking (it
// surfaces e.g. Gérard Cachon, whom autocomplete misses) but only matches COMPLETE name tokens;
// `/autocomplete/authors` matches prefixes (good while still typing) but ranks sparse clusters
// oddly. Query both, merge by id (search wins, it carries the institution), citation-sort, top 8.
export async function autocompleteAuthors(q: string): Promise<AuthorSuggestion[]> {
  const term = q.trim();
  if (term.length < 2) return [];
  const enc = encodeURIComponent(term);
  const [search, ac] = await Promise.all([
    _authorsList(
      `https://api.openalex.org/authors?search=${enc}&sort=cited_by_count:desc&per-page=8` +
        `&select=id,display_name,cited_by_count,works_count,last_known_institutions,orcid${AUTH}`,
      (a) => ({
        oaid: (a.id || "").split("/").pop() || "",
        name: a.display_name ?? "",
        institution: (a.last_known_institutions || [])[0]?.display_name ?? null,
        works_count: a.works_count ?? null,
        cited_by_count: a.cited_by_count ?? null,
        orcid: a.orcid ?? null,
      })
    ),
    _authorsList(`https://api.openalex.org/autocomplete/authors?q=${enc}${AUTH}`, (x) => ({
      oaid: (x.id || "").split("/").pop() || "",
      name: x.display_name ?? "",
      institution: x.hint ?? null,
      works_count: x.works_count ?? null,
      cited_by_count: x.cited_by_count ?? null,
      orcid: x.external_id ?? null,
    })),
  ]);
  const merged = new Map<string, AuthorSuggestion>();
  for (const s of [...search, ...ac]) if (s.oaid && !merged.has(s.oaid)) merged.set(s.oaid, s);
  return [...merged.values()]
    .sort((a, b) => (b.cited_by_count ?? 0) - (a.cited_by_count ?? 0))
    .slice(0, 8);
}

// The author's works, most-cited first, mapped like any other work (so each carries its own
// byline, fields, and citations). Capped — an author page shows a portfolio, not everything.
export async function fetchAuthorWorks(oaid: string, limit = 100): Promise<Work[]> {
  const select =
    "id,doi,title,publication_year,primary_topic,primary_location,authorships," +
    "cited_by_count,open_access,is_retracted";
  const per = Math.min(Math.max(limit, 1), 200);
  const url =
    `https://api.openalex.org/works?filter=authorships.author.id:${encodeURIComponent(oaid)}` +
    `&select=${select}&per-page=${per}&sort=cited_by_count:desc${AUTH}`;
  try {
    const r = await fetch(url, {
      headers: { "User-Agent": `al-web/1.0 (${MAILTO})` },
      next: { revalidate: SEARCH_REVALIDATE },
    });
    if (!r.ok) return [];
    const j: any = await r.json();
    return (j.results || []).map((w: any) => mapWork(w));
  } catch {
    return [];
  }
}
