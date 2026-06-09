// Live OpenAlex work fetch for the paper page (QaL_spec §11 cheap-path). Keeps the displayed
// metadata current — title, byline, citations — so stored snapshots can't go stale. Cached
// via Next fetch revalidation so repeat views don't re-hit the API.

const MAILTO = process.env.OPENALEX_MAILTO || "ktulrich@gmail.com";
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

export async function fetchWork(oaid: string): Promise<Work | null> {
  const select =
    "id,doi,title,publication_year,primary_topic,primary_location,authorships," +
    "cited_by_count,biblio,open_access,is_retracted,referenced_works";
  const url =
    `https://api.openalex.org/works/${encodeURIComponent(oaid)}` +
    `?select=${select}&mailto=${encodeURIComponent(MAILTO)}`;
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
  const w: any = await r.json();
  const pt = w.primary_topic || {};
  const sub = pt.subfield || {};
  return {
    oaid: (w.id || "").split("/").pop() || oaid,
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
