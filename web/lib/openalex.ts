// Live OpenAlex work fetch for the paper page (QaL_spec §11 cheap-path). Keeps the displayed
// metadata current — title, byline, citations — so stored snapshots can't go stale. Cached
// via Next fetch revalidation so repeat views don't re-hit the API.

import type { Authorship } from "./types";

const MAILTO = process.env.OPENALEX_MAILTO || "ktulrich@gmail.com";
// The web defaults to the FREE polite pool (no api_key) so anonymous/bot traffic can't drain the
// metered OpenAlex budget — a paper/author page is just credits, but a crawler hitting them adds up.
// Re-enable the premium key (faster, higher limits) only when bots are fully blocked, by setting
// OPENALEX_WEB_PREMIUM=1 in the Vercel env. The Python pipeline is unaffected (it reads .env).
const API_KEY = process.env.OPENALEX_WEB_PREMIUM === "1" ? (process.env.OPENALEX_API_KEY || "") : "";
const AUTH = `&mailto=${encodeURIComponent(MAILTO)}${API_KEY ? `&api_key=${encodeURIComponent(API_KEY)}` : ""}`;
const REVALIDATE = 60 * 60 * 24; // 1 day
const AUTHOR_TIMEOUT_MS = 1200; // typeahead must stay snappy even if /authors?search is degraded

// Every OpenAlex call is bounded by a timeout — a degraded endpoint (e.g. /authors?search returning
// a 30s gateway timeout) must never hang a request — and falls back to the free polite pool when the
// premium budget (shared with the batch pipeline) is exhausted (429 "Insufficient budget"). The web
// app's availability must not depend on the batch's budget OR on one slow OpenAlex endpoint.
async function oaFetch(url: string, init: RequestInit): Promise<Response> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  if (!init.signal) {
    const ctrl = new AbortController();
    timer = setTimeout(() => ctrl.abort(), 8000);
    init = { ...init, signal: ctrl.signal };
  }
  try {
    const r = await fetch(url, init);
    if (r.status === 429 && API_KEY && url.includes(`api_key=${encodeURIComponent(API_KEY)}`)) {
      return await fetch(url.replace(`&api_key=${encodeURIComponent(API_KEY)}`, ""), init);
    }
    return r;
  } finally {
    if (timer) clearTimeout(timer);
  }
}

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
    r = await oaFetch(url, {
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
    const r = await oaFetch(url, {
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

// A pasted DOI, OpenAlex work id, or SSRN/doi.org URL is a direct reference, not a text query.
// Resolve it via the single-entity / `filter=doi:` endpoints — which OpenAlex does NOT rate-limit —
// instead of the throttled text search. Returns an OpenAlex-resolvable id, or null for an ordinary
// query. (backlog U12: lets a paper be found by pasting its link even if search is degraded.)
export function parseWorkRef(term: string): { kind: "oaid" | "doi"; id: string } | null {
  const t = term.trim();
  const oa = t.match(/^(?:https?:\/\/openalex\.org\/)?(W\d{4,})$/i); // W-id, bare or as a URL
  if (oa) return { kind: "oaid", id: oa[1].toUpperCase() };
  const ssrn = t.match(/ssrn\.com\/\S*abstract_?id=(\d+)/i); // SSRN page -> its SSRN DOI
  if (ssrn) return { kind: "doi", id: `10.2139/ssrn.${ssrn[1]}` };
  const doi = t.match(/^(?:doi:|https?:\/\/(?:dx\.)?doi\.org\/)?(10\.\d{4,}\/\S+)$/i);
  if (doi) return { kind: "doi", id: doi[1].replace(/[.,;)\]]+$/, "") };
  return null;
}

export async function searchWorks(
  q: string,
  opts: { since?: number | null } = {}
): Promise<Work[]> {
  const term = q.trim();
  if (!term) return [];
  // Direct DOI/ID/URL paste -> exact lookup, bypassing the (rate-limited) text search.
  const ref = parseWorkRef(term);
  if (ref) {
    if (ref.kind === "oaid") {
      const w = await fetchWork(ref.id);
      return w ? [w] : [];
    }
    const rows = await searchOne(`doi:${ref.id}`);
    return rows.length ? [mapWork(rows[0])] : [];
  }
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

// ---- "Check my references" (paste a bibliography; resolve each line to a Ledger paper) --------
// A raw citation string (authors + title + venue + year + pages) confuses OpenAlex's relevance
// search, so we resolve each reference with Crossref's purpose-built bibliographic matcher, then
// look the returned DOI up in OpenAlex for the Ledger view (cites, QaL). A reference with no
// confident match is flagged "check for validity" — the fabricated / garbled / dead-citation signal.

export interface RefResult {
  ref: string;
  status: "found" | "flag";
  work: Work | null; // the matched Ledger paper (oaid, cites, …) when found
  closest: string | null; // best (rejected) title, shown on a flag for context
  note: string | null; // a specific flag reason (e.g. the cited DOI resolves to a different paper)
}

function refToks(s: string | null): Set<string> {
  return new Set(
    (s || "").toLowerCase().normalize("NFKD").replace(/[^a-z0-9\s]/g, " ").split(/\s+/).filter((w) => w.length > 2)
  );
}
// fraction of the candidate title's content words that appear in the reference string
function titleOverlap(title: string | null, ref: string): number {
  const a = refToks(title);
  if (a.size < 2) return 0;
  const b = refToks(ref);
  let hit = 0;
  a.forEach((w) => { if (b.has(w)) hit++; });
  return hit / a.size;
}

async function crossrefTop(ref: string): Promise<{ title: string | null; doi: string | null; score: number } | null> {
  const url =
    `https://api.crossref.org/works?query.bibliographic=${encodeURIComponent(ref.slice(0, 400))}` +
    `&rows=1&select=title,DOI,score&mailto=${encodeURIComponent(MAILTO)}`;
  try {
    const r = await oaFetch(url, {
      headers: { "User-Agent": `academic-ledger/1.0 (mailto:${MAILTO})` },
      next: { revalidate: SEARCH_REVALIDATE },
    });
    if (!r.ok) return null;
    const j: any = await r.json();
    const it = j?.message?.items?.[0];
    if (!it) return null;
    return { title: it.title?.[0] ?? null, doi: it.DOI ?? null, score: it.score ?? 0 };
  } catch {
    return null;
  }
}

const asFound = (ref: string, w: Work): RefResult => ({ ref, status: "found", work: w, closest: null, note: null });
const clip = (t: string | null) => (t && t.length > 140 ? t.slice(0, 140) + "…" : t);

export async function checkReference(ref: string): Promise<RefResult> {
  const trimmed = ref.trim();

  // 1) The reference's own DOI — accept ONLY if the resolved paper's title matches the citation.
  //    A DOI that resolves to a different paper is a strong fabrication signal (a borrowed DOI).
  const dm = trimmed.match(/\b10\.\d{4,}\/[^\s"<>,;]+/);
  const refDoi = dm ? dm[0].replace(/[.,;:)\]]+$/, "") : null;
  if (refDoi) {
    const rows = await searchOne(`doi:${refDoi}`);
    if (rows.length) {
      const w = mapWork(rows[0]);
      if (titleOverlap(w.title, trimmed) >= 0.35) return asFound(trimmed, w);
      return { ref: trimmed, status: "flag", work: null, closest: clip(w.title),
        note: "the cited DOI resolves to a different paper" };
    }
    // ref DOI not indexed in OpenAlex (common for arXiv/IEEE) -> fall through to Crossref / title.
  }

  // 2) Resolve the citation string via Crossref; then find the work in OpenAlex by Crossref's DOI,
  //    else by title — so a real paper whose arXiv/IEEE DOI OpenAlex lacks is still found.
  const cx = await crossrefTop(trimmed);
  if (cx?.title) {
    const ov = titleOverlap(cx.title, trimmed);
    // real refs land at overlap ~1 (or lower + a high Crossref score when the stored title carries a
    // subtitle the citation omits); fabricated refs get low overlap AND low score.
    if (ov >= 0.65 || (ov >= 0.35 && cx.score >= 50)) {
      if (cx.doi) {
        const rows = await searchOne(`doi:${cx.doi}`);
        if (rows.length) {
          const w = mapWork(rows[0]);
          if (titleOverlap(w.title, trimmed) >= 0.35 || titleOverlap(w.title, cx.title) >= 0.6) return asFound(trimmed, w);
        }
      }
      for (const raw of (await searchOne(`title.search:${encodeURIComponent(cx.title)}`)).slice(0, 3)) {
        const w = mapWork(raw);
        if (titleOverlap(w.title, cx.title) >= 0.6) return asFound(trimmed, w);
      }
    }
  }
  return { ref: trimmed, status: "flag", work: null, closest: clip(cx?.title ?? null), note: null };
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
    r = await oaFetch(url, {
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
    const r = await oaFetch(url, {
      headers: { "User-Agent": `al-web/1.0 (${MAILTO})` },
      next: { revalidate: SEARCH_REVALIDATE },
      signal: AbortSignal.timeout(AUTHOR_TIMEOUT_MS), // don't let a hung /authors?search block the typeahead
    });
    if (!r.ok) return [];
    const j: any = await r.json();
    return ((j.results || []) as any[]).map(map).filter((s) => s.oaid && s.name);
  } catch {
    return [];
  }
}

// Hybrid typeahead. `authors?filter=display_name.search:` requires the query's tokens to appear in
// ONE author's NAME — so "Sophie Yu" resolves to real people named Sophie … Yu, and "Cachon" still
// surfaces Gérard P. Cachon — unlike the earlier `authors?search=`, whose fuzzy relevance + citation
// sort buried less-famous authors under mega-cited near-matches (e.g. "Sophie Yu" returned V. O.
// Tikhomirov). `/autocomplete/authors` adds prefix matches (good while still typing). Query both,
// merge by id, citation-sort, top 8. (backlog U16.)
export async function autocompleteAuthors(q: string): Promise<AuthorSuggestion[]> {
  const term = q.trim();
  if (term.length < 2) return [];
  const enc = encodeURIComponent(term.replace(/,/g, " ")); // commas delimit OpenAlex filters
  const [search, ac] = await Promise.all([
    _authorsList(
      `https://api.openalex.org/authors?filter=display_name.search:${enc}&sort=cited_by_count:desc&per-page=8` +
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
// Returns the author's works, or `null` when OpenAlex couldn't be reached (rate-limit/budget 429,
// timeout, network). `null` ≠ `[]`: an empty array means the author genuinely has no works, while
// `null` lets the caller show an honest "source unavailable" state instead of an empty portfolio
// that falsely implies a scholar with no work.
export async function fetchAuthorWorks(oaid: string, limit = 100): Promise<Work[] | null> {
  const select =
    "id,doi,title,publication_year,primary_topic,primary_location,authorships," +
    "cited_by_count,open_access,is_retracted";
  const per = Math.min(Math.max(limit, 1), 200);
  const url =
    `https://api.openalex.org/works?filter=authorships.author.id:${encodeURIComponent(oaid)}` +
    `&select=${select}&per-page=${per}&sort=cited_by_count:desc${AUTH}`;
  try {
    const r = await oaFetch(url, {
      headers: { "User-Agent": `al-web/1.0 (${MAILTO})` },
      next: { revalidate: SEARCH_REVALIDATE },
    });
    if (!r.ok) return null; // 429/budget/5xx -> unavailable, not "no works"
    const j: any = await r.json();
    return (j.results || []).map((w: any) => mapWork(w));
  } catch {
    return null; // timeout / network -> unavailable
  }
}
