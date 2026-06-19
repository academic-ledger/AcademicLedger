import { query } from "./db";

// C2 — author-originated overlay: "canonical version & author notes" on a paper page. Repeatable
// items per (author, paper). Writes ONLY paper_notes; never the metric tables; never changes QaL.
// See db/migrations/008_paper_notes.sql + docs/community_layer_v0.md.

const RELATIONS = new Set(["canonical", "supersedes", "related", "note"]);
const MAX_PER_AUTHOR_WORK = 12;

let _ready = false;
async function ensureTable(): Promise<void> {
  if (_ready) return;
  await query(`create table if not exists paper_notes (
    id serial primary key,
    user_id integer not null references users(id) on delete cascade,
    work_oaid text not null,
    target_oaid text, target_title text,
    relation text not null default 'note',
    body text,
    visible boolean not null default true,
    status text not null default 'active',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
  )`);
  _ready = true;
}

export interface PaperNote {
  id: number;
  work_oaid: string;
  target_oaid: string | null;
  target_title: string | null;
  relation: string;
  body: string | null;
  author_name: string | null;
  author_orcid: string;
  created_at: string;
  updated_at: string;
}

function normOrcid(s: string): string {
  return String(s || "").replace(/^https?:\/\/(sandbox\.)?orcid\.org\//, "").trim();
}
function bareDoi(s: string | null | undefined): string | null {
  if (!s) return null;
  return String(s).toLowerCase().replace(/^https?:\/\/doi\.org\//, "").trim() || null;
}

export async function getUserIdByOrcid(orcid: string): Promise<number | null> {
  try {
    const rows = await query<{ id: number }>(`select id from users where orcid_id = $1`, [normOrcid(orcid)]);
    return rows.length ? rows[0].id : null;
  } catch {
    return null;
  }
}

// Authorship gate: the signed-in ORCID is on the work's OpenAlex byline, OR the work's DOI is in the
// member's cached ORCID works. (Neither → it's the C3 "claim" case, not yet built.)
export async function isAuthorOfWork(
  orcid: string,
  userId: number,
  work: { authorships?: Array<{ orcid?: string | null }> | null; doi?: string | null }
): Promise<boolean> {
  const me = normOrcid(orcid);
  if ((work.authorships ?? []).some((a) => a?.orcid && normOrcid(a.orcid) === me)) return true;
  const doi = bareDoi(work.doi);
  if (doi) {
    try {
      const rows = await query(
        `select 1 from orcid_works where user_id = $1
          and lower(replace(doi, 'https://doi.org/', '')) = $2 limit 1`,
        [userId, doi]
      );
      if (rows.length) return true;
    } catch {
      /* orcid_works may be empty */
    }
  }
  return false;
}

// Public read for the display-merge: visible notes on a work, author name/iD joined, canonical first.
export async function listNotes(workOaid: string): Promise<PaperNote[]> {
  try {
    await ensureTable();
    return await query<PaperNote>(
      `select n.id, n.work_oaid, n.target_oaid, n.target_title, n.relation, n.body,
              u.display_name as author_name, u.orcid_id as author_orcid,
              n.created_at, n.updated_at
         from paper_notes n join users u on u.id = n.user_id
        where n.work_oaid = $1 and n.visible and n.status = 'active'
        order by case n.relation when 'canonical' then 0 when 'supersedes' then 1
                                 when 'related' then 2 else 3 end, n.created_at`,
      [workOaid]
    );
  } catch {
    return [];
  }
}

interface NoteInput {
  target_oaid?: string | null;
  target_title?: string | null;
  relation?: string;
  body?: string | null;
}
function clean(item: NoteInput) {
  const relation = RELATIONS.has(item.relation ?? "") ? (item.relation as string) : "note";
  return {
    relation,
    target_oaid: item.target_oaid ? String(item.target_oaid).slice(0, 32) : null,
    target_title: item.target_title ? String(item.target_title).slice(0, 400) : null,
    body: item.body ? String(item.body).slice(0, 1000) : null,
  };
}

export async function addNote(userId: number, workOaid: string, item: NoteInput): Promise<number> {
  await ensureTable();
  const c = clean(item);
  const cnt = await query<{ n: number }>(
    `select count(*)::int n from paper_notes where user_id = $1 and work_oaid = $2 and status = 'active'`,
    [userId, workOaid]
  );
  if ((cnt[0]?.n ?? 0) >= MAX_PER_AUTHOR_WORK) throw new Error("Note limit reached for this paper.");
  if (c.relation === "canonical") {
    // one canonical per (author, paper): demote any prior canonical
    await query(
      `update paper_notes set relation = 'related', updated_at = now()
        where user_id = $1 and work_oaid = $2 and relation = 'canonical' and status = 'active'`,
      [userId, workOaid]
    );
  }
  const rows = await query<{ id: number }>(
    `insert into paper_notes (user_id, work_oaid, target_oaid, target_title, relation, body)
       values ($1, $2, $3, $4, $5, $6) returning id`,
    [userId, workOaid, c.target_oaid, c.target_title, c.relation, c.body]
  );
  return rows[0].id;
}

export async function updateNote(userId: number, id: number, item: NoteInput): Promise<void> {
  await ensureTable();
  const c = clean(item);
  const own = await query<{ work_oaid: string }>(
    `select work_oaid from paper_notes where id = $1 and user_id = $2 and status = 'active'`,
    [id, userId]
  );
  if (!own.length) throw new Error("Note not found.");
  if (c.relation === "canonical") {
    await query(
      `update paper_notes set relation = 'related', updated_at = now()
        where user_id = $1 and work_oaid = $2 and relation = 'canonical' and status = 'active' and id <> $3`,
      [userId, own[0].work_oaid, id]
    );
  }
  await query(
    `update paper_notes set target_oaid = $1, target_title = $2, relation = $3, body = $4, updated_at = now()
      where id = $5 and user_id = $6`,
    [c.target_oaid, c.target_title, c.relation, c.body, id, userId]
  );
}

export async function deleteNote(userId: number, id: number): Promise<void> {
  await ensureTable();
  await query(
    `update paper_notes set status = 'deleted', visible = false, updated_at = now()
      where id = $1 and user_id = $2`,
    [id, userId]
  );
}
