"use client";

import { useState } from "react";
import Brand from "@/components/Brand";

type Work = {
  oaid: string;
  title: string | null;
  authors: string | null;
  year: number | null;
  venue: string | null;
  cites: number;
  is_retracted: boolean;
};
type RefResult = {
  ref: string;
  status: "found" | "flag" | "unresolved";
  work: Work | null;
  closest: string | null;
  note: string | null;
};

const BATCH = 12; // references per request — keeps each call fast and paces Crossref

const SAMPLE = `Watson JD, Crick FHC. Molecular structure of nucleic acids: a structure for deoxyribose nucleic acid. Nature. 1953;171(4356):737-738.
Radicchi F, Fortunato S, Castellano C. Universality of citation distributions. PNAS. 2008;105(45):17268-17272.
Girotra K, Meincke C, Terwiesch C, Ulrich KT. Ideas are dimes a dozen: large language models for idea generation. Management Science. 2023.
Zhang L, Patel R. Neural coherence fields for zero-shot causal inference. Journal of Synthetic Cognition. 2021;8(2):112-140.`;

export default function CheckReferences() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [refs, setRefs] = useState<string[]>([]);
  const [results, setResults] = useState<(RefResult | null)[]>([]);
  const [truncated, setTruncated] = useState(false);
  const [err, setErr] = useState("");

  async function post(body: unknown) {
    const r = await fetch("/api/check-references", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || "Something went wrong.");
    return d;
  }

  // Resolve a set of indices (in BATCH-sized chunks) and merge into `acc`, refreshing the UI as we go.
  async function resolve(acc: (RefResult | null)[], list: string[], idxs: number[]) {
    for (let i = 0; i < idxs.length; i += BATCH) {
      const chunk = idxs.slice(i, i + BATCH);
      try {
        const d = await post({ batch: chunk.map((k) => list[k]) });
        chunk.forEach((k, j) => (acc[k] = d.results[j] ?? acc[k]));
      } catch {
        // whole request failed — mark this chunk unresolved so it renders as retryable (and the
        // auto-retry / manual retry pick it up), rather than sticking on "checking…".
        chunk.forEach((k) => {
          if (!acc[k]) acc[k] = { ref: list[k], status: "unresolved", work: null, closest: null, note: null };
        });
      }
      setResults([...acc]);
    }
  }

  async function run() {
    setErr("");
    setRefs([]);
    setResults([]);
    setLoading(true);
    try {
      const split = await post({ text });
      const list: string[] = split.refs || [];
      if (!list.length) throw new Error("No references found in the pasted text.");
      setRefs(list);
      setTruncated(!!split.truncated);
      const acc: (RefResult | null)[] = list.map(() => null);
      setResults([...acc]);
      await resolve(acc, list, list.map((_, i) => i));
      // one automatic retry pass for anything the resolver throttled
      const stuck = acc.map((r, i) => (r && r.status === "unresolved" ? i : -1)).filter((i) => i >= 0);
      if (stuck.length) await resolve(acc, list, stuck);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function retryUnresolved() {
    const list = refs;
    const acc = [...results];
    const stuck = acc.map((r, i) => (r && r.status === "unresolved" ? i : -1)).filter((i) => i >= 0);
    if (!stuck.length) return;
    setLoading(true);
    try {
      await resolve(acc, list, stuck);
    } finally {
      setLoading(false);
    }
  }

  const done = results.filter(Boolean).length;
  const found = results.filter((r) => r?.status === "found").length;
  const flagged = results.filter((r) => r?.status === "flag").length;
  const unresolved = results.filter((r) => r?.status === "unresolved").length;
  const total = refs.length;

  return (
    <>
      <Brand active="check-references" />
      <main style={{ maxWidth: 860, margin: "0 auto", padding: "8px 20px 80px" }}>
        <h1 style={{ color: "#1b2a4a", marginBottom: 4 }}>Check my references</h1>
        <p style={{ color: "#555", lineHeight: 1.5, marginTop: 0 }}>
          Paste a paper&rsquo;s reference list. We resolve each reference against the scholarly record and show its
          citation impact on the Ledger. Anything we can&rsquo;t confidently match is flagged{" "}
          <b style={{ color: "#c0392b" }}>check for validity</b> &mdash; a fast scan for fabricated, garbled, or dead
          citations.
        </p>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={11}
          placeholder="Paste the reference list here…"
          style={{
            width: "100%", boxSizing: "border-box", padding: 12, fontSize: 14, lineHeight: 1.5,
            border: "1px solid #ccd2da", borderRadius: 8, fontFamily: "inherit", resize: "vertical",
          }}
        />
        <div style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 10 }}>
          <button
            onClick={run}
            disabled={loading || text.trim().length < 20}
            style={{
              background: "#2e8b57", color: "#fff", border: 0, borderRadius: 8, padding: "9px 18px",
              fontSize: 15, fontWeight: 600, cursor: loading || text.trim().length < 20 ? "not-allowed" : "pointer",
              opacity: loading || text.trim().length < 20 ? 0.55 : 1,
            }}
          >
            {loading && total ? `Checking ${done} / ${total}…` : loading ? "Checking…" : "Check references"}
          </button>
          <button
            onClick={() => setText(SAMPLE)}
            style={{ background: "none", border: 0, color: "#2166ac", cursor: "pointer", fontSize: 14 }}
          >
            try a sample
          </button>
        </div>

        {err && <p style={{ color: "#c0392b", marginTop: 16 }}>{err}</p>}

        {total > 0 && (
          <div style={{ marginTop: 24 }}>
            {/* progress bar */}
            {loading && (
              <div style={{ height: 4, background: "#eee", borderRadius: 3, overflow: "hidden", marginBottom: 14 }}>
                <div style={{ width: `${total ? (done / total) * 100 : 0}%`, height: "100%", background: "#2e8b57", transition: "width .2s" }} />
              </div>
            )}
            <p style={{ fontSize: 15, color: "#333" }}>
              {total} references &middot;{" "}
              <b style={{ color: "#2e8b57" }}>{found} found</b> &middot;{" "}
              <b style={{ color: "#c0392b" }}>{flagged} to check</b>
              {unresolved > 0 && (
                <>
                  {" "}&middot; <b style={{ color: "#b8860b" }}>{unresolved} couldn&rsquo;t check</b>
                  {!loading && (
                    <button
                      onClick={retryUnresolved}
                      style={{ marginLeft: 8, background: "none", border: "1px solid #d9c58a", color: "#8a6d1f",
                        borderRadius: 6, padding: "2px 9px", fontSize: 12.5, cursor: "pointer" }}
                    >
                      retry
                    </button>
                  )}
                </>
              )}
              {truncated && <span style={{ color: "#888" }}> &middot; first {total} shown</span>}
            </p>
            <ol style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {refs.map((refStr, i) => {
                const rc = results[i];
                const ok = rc?.status === "found" && rc.work;
                const un = rc?.status === "unresolved";
                const pending = !rc;
                const accent = ok ? "#2e8b57" : pending ? "#d7d7d7" : un ? "#d9b24a" : "#c0392b";
                const bg = ok ? "#f4f9f6" : pending ? "#fafafa" : un ? "#fdf9ee" : "#fdf3f2";
                return (
                  <li key={i} style={{ borderLeft: `4px solid ${accent}`, background: bg, padding: "10px 14px", borderRadius: 6, margin: "8px 0" }}>
                    <div style={{ fontSize: 12.5, color: "#888", marginBottom: 6 }}>{refStr}</div>
                    {ok ? (
                      <a href={`/paper/${rc!.work!.oaid}`} target="_blank" rel="noopener"
                        style={{ textDecoration: "none", color: "inherit", display: "block" }}>
                        <div style={{ fontSize: 15, fontWeight: 600, color: "#1b2a4a" }}>
                          {rc!.work!.title}
                          {rc!.work!.is_retracted && <span style={{ color: "#c0392b", fontWeight: 700 }}> &middot; RETRACTED</span>}
                        </div>
                        <div style={{ fontSize: 13, color: "#555", marginTop: 2 }}>
                          {rc!.work!.authors} &middot; {rc!.work!.year} &middot;{" "}
                          <b>{rc!.work!.cites.toLocaleString()} citations</b>
                          {rc!.work!.venue ? ` · ${rc!.work!.venue}` : ""}
                          <span style={{ color: "#2166ac" }}> &middot; view on the Ledger &rarr;</span>
                        </div>
                      </a>
                    ) : pending ? (
                      <div style={{ fontSize: 13.5, color: "#999" }}>⋯ checking…</div>
                    ) : un ? (
                      <div style={{ fontSize: 14, color: "#8a6d1f", fontWeight: 600 }}>
                        ⧗ couldn&rsquo;t reach the resolver (rate-limited) &mdash; not yet checked; press retry
                      </div>
                    ) : (
                      <div style={{ fontSize: 14, color: "#c0392b", fontWeight: 600 }}>
                        ⚠{" "}
                        {rc!.note ? "cited DOI belongs to a different paper — likely fabricated" : "no result found — check for validity"}
                        {rc!.closest && (
                          <span style={{ fontWeight: 400, color: "#a06", fontStyle: "italic" }}>
                            {" "}({rc!.note ? "resolves to" : "closest, rejected"}: &ldquo;{rc!.closest}&rdquo;)
                          </span>
                        )}
                      </div>
                    )}
                  </li>
                );
              })}
            </ol>
            <p style={{ fontSize: 12, color: "#999", marginTop: 16 }}>
              Matching via Crossref&rsquo;s bibliographic resolver; a red flag means &ldquo;could not confidently
              resolve&rdquo; &mdash; worth a human check, not proof of fabrication. Legitimate but poorly-indexed
              works (some books, arXiv-only preprints, non-English, very old) can also flag. An amber
              &ldquo;couldn&rsquo;t check&rdquo; means the resolver was rate-limited, not that the reference is bad.
            </p>
          </div>
        )}
      </main>
    </>
  );
}
