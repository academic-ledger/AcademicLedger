"use client";
import { useEffect, useRef, useState } from "react";
import { useSession, signIn } from "next-auth/react";
import { useRouter } from "next/navigation";

// C2 — "Canonical version & author notes" block (above Cite on the paper page). Read view for
// everyone; the editor (Add / edit / delete, with a version typeahead) shows only for the signed-in
// ORCID-verified author of THIS paper (canEdit, computed server-side). Writes go through
// /api/paper/[oaid]/note, which re-verifies authorship server-side. Never touches QaL.

interface Note {
  id: number;
  target_oaid: string | null;
  target_title: string | null;
  relation: string;
  body: string | null;
  author_name: string | null;
  author_orcid: string;
  created_at: string;
}
interface Hit {
  oaid: string;
  title: string;
  year: number | null;
  authors: string | null;
}

const RELATION_LABEL: Record<string, string> = {
  canonical: "Canonical version",
  supersedes: "Supersedes",
  related: "Related",
  note: "",
};
const fmtDate = (s: string) => {
  try {
    return new Date(s).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return "";
  }
};
const normOrcid = (s?: string | null) =>
  String(s || "").replace(/^https?:\/\/(sandbox\.)?orcid\.org\//, "").trim();

export default function PaperNotes({
  oaid,
  notes,
  canEdit,
}: {
  oaid: string;
  notes: Note[];
  canEdit: boolean;
}) {
  const { data, status } = useSession();
  const router = useRouter();
  const myOrcid = normOrcid((data as any)?.orcid ?? (data?.user as any)?.orcid);

  // editor state
  const [editing, setEditing] = useState<number | "new" | null>(null);
  const [target, setTarget] = useState<{ oaid: string; title: string } | null>(null);
  const [relation, setRelation] = useState("canonical");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // version typeahead
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    const t = setTimeout(async () => {
      if (q.trim().length < 3) return setHits([]);
      try {
        const r = await fetch("/api/works/search?q=" + encodeURIComponent(q));
        const d = await r.json();
        if (!cancelled) {
          setHits(d.items ?? []);
          setOpen(true);
        }
      } catch {
        /* ignore */
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [q]);

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  function openNew() {
    setEditing("new");
    setTarget(null);
    setRelation("canonical");
    setBody("");
    setQ("");
    setHits([]);
    setErr(null);
  }
  function openEdit(n: Note) {
    setEditing(n.id);
    setTarget(n.target_oaid ? { oaid: n.target_oaid, title: n.target_title ?? n.target_oaid } : null);
    setRelation(n.relation === "note" ? "canonical" : n.relation);
    setBody(n.body ?? "");
    setQ("");
    setHits([]);
    setErr(null);
  }

  async function save() {
    setBusy(true);
    setErr(null);
    const payload = {
      id: editing === "new" ? undefined : editing,
      target_oaid: target?.oaid ?? null,
      target_title: target?.title ?? null,
      relation: target ? relation : "note", // no linked version => a plain note
      body: body.trim() || null,
    };
    if (!payload.target_oaid && !payload.body) {
      setErr("Add a linked version, a comment, or both.");
      setBusy(false);
      return;
    }
    try {
      const r = await fetch(`/api/paper/${oaid}/note`, {
        method: editing === "new" ? "POST" : "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok || j?.ok === false) {
        setErr(j?.error ?? "Couldn't save.");
      } else {
        setEditing(null);
        router.refresh();
      }
    } catch {
      setErr("Couldn't save.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    if (!confirm("Delete this note?")) return;
    try {
      await fetch(`/api/paper/${oaid}/note`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id }),
      });
      router.refresh();
    } catch {
      /* ignore */
    }
  }

  const hasNotes = notes.length > 0;
  if (!hasNotes && !canEdit && status !== "loading") {
    // nothing to show and viewer can't add — but offer the nudge to (possibly) signed-out authors
    if (status === "unauthenticated") {
      return (
        <div className="card pnotes">
          <h2>Canonical version &amp; author notes</h2>
          <p className="pnotes-nudge">
            Are you an author of this paper?{" "}
            <button className="authbtn authbtn-in" onClick={() => signIn("orcid")}>
              Sign in with ORCID
            </button>{" "}
            to mark the canonical version or add a note.
          </p>
        </div>
      );
    }
    return null; // signed-in non-author, no notes: keep the page clean
  }

  return (
    <div className="card pnotes">
      <h2>Canonical version &amp; author notes</h2>

      {hasNotes && (
        <ul className="pnotes-list">
          {notes.map((n) => {
            const mine = canEdit && normOrcid(n.author_orcid) === myOrcid;
            return (
              <li key={n.id}>
                {n.target_oaid && RELATION_LABEL[n.relation] && (
                  <div className="pnotes-rel">
                    <b>{RELATION_LABEL[n.relation]}:</b>{" "}
                    <a href={`/paper/${n.target_oaid}`}>{n.target_title ?? n.target_oaid}</a>{" "}
                    <span className="arr">↗</span>
                  </div>
                )}
                {n.body && <div className="pnotes-body">{n.body}</div>}
                <div className="pnotes-attr">
                  — {n.author_name || "ORCID author"} ·{" "}
                  <span className="verified">ORCID-verified author</span> · {fmtDate(n.created_at)}
                  {mine && (
                    <>
                      {" · "}
                      <button className="pnotes-link" onClick={() => openEdit(n)}>
                        edit
                      </button>{" "}
                      <button className="pnotes-link" onClick={() => remove(n.id)}>
                        delete
                      </button>
                    </>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {canEdit && editing === null && (
        <button className="authbtn authbtn-in" onClick={openNew}>
          + Add a note
        </button>
      )}

      {canEdit && editing !== null && (
        <div className="pnotes-editor">
          <label className="pnotes-flabel">Link a version (optional)</label>
          <div className="authsearch" ref={box}>
            {target ? (
              <div className="pnotes-picked">
                {target.title}{" "}
                <button className="pnotes-link" onClick={() => setTarget(null)}>
                  change
                </button>
              </div>
            ) : (
              <input
                type="text"
                value={q}
                placeholder="Search papers by title or author…"
                onChange={(e) => setQ(e.target.value)}
                onFocus={() => hits.length && setOpen(true)}
              />
            )}
            {open && !target && hits.length > 0 && (
              <ul className="authsug">
                {hits.map((h) => (
                  <li
                    key={h.oaid}
                    onMouseDown={(e) => {
                      e.preventDefault();
                      setTarget({ oaid: h.oaid, title: h.title });
                      setOpen(false);
                    }}
                  >
                    <span className="nm">{h.title}</span>
                    <span className="meta">
                      {h.authors || "—"}
                      {h.year ? ` · ${h.year}` : ""}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {target && (
            <div className="pnotes-relrow">
              <label className="pnotes-flabel">This version is:</label>
              <select value={relation} onChange={(e) => setRelation(e.target.value)}>
                <option value="canonical">the canonical version</option>
                <option value="supersedes">superseded by this</option>
                <option value="related">related / see also</option>
              </select>
            </div>
          )}

          <label className="pnotes-flabel">Note (optional)</label>
          <textarea
            value={body}
            maxLength={1000}
            placeholder="e.g. The Management Science version is the most recent and most complete."
            onChange={(e) => setBody(e.target.value)}
          />

          {err && <p className="pnotes-err">{err}</p>}
          <div className="pnotes-actions">
            <button className="authbtn authbtn-in" disabled={busy} onClick={save}>
              {busy ? "Saving…" : "Save"}
            </button>
            <button className="authbtn" disabled={busy} onClick={() => setEditing(null)}>
              Cancel
            </button>
          </div>
          <p className="pnotes-fine">
            Shown publicly, attributed to you. Doesn&rsquo;t change the paper&rsquo;s QaL.
          </p>
        </div>
      )}
    </div>
  );
}
