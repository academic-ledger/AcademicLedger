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
type RefResult = { ref: string; status: "found" | "flag"; work: Work | null; closest: string | null };
type Resp = { refs: RefResult[]; total: number; found: number; truncated?: boolean };

const SAMPLE = `Watson JD, Crick FHC. Molecular structure of nucleic acids: a structure for deoxyribose nucleic acid. Nature. 1953;171(4356):737-738.
Radicchi F, Fortunato S, Castellano C. Universality of citation distributions. PNAS. 2008;105(45):17268-17272.
Girotra K, Meincke C, Terwiesch C, Ulrich KT. Ideas are dimes a dozen: large language models for idea generation. Management Science. 2023.
Zhang L, Patel R. Neural coherence fields for zero-shot causal inference. Journal of Synthetic Cognition. 2021;8(2):112-140.`;

export default function CheckReferences() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<Resp | null>(null);
  const [err, setErr] = useState("");

  async function run() {
    setLoading(true);
    setErr("");
    setData(null);
    try {
      const r = await fetch("/api/check-references", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || "Something went wrong.");
      setData(d);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  const missing = data ? data.total - data.found : 0;

  return (
    <>
      <Brand active={null} />
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
            {loading ? "Checking…" : "Check references"}
          </button>
          <button
            onClick={() => setText(SAMPLE)}
            style={{ background: "none", border: 0, color: "#2166ac", cursor: "pointer", fontSize: 14 }}
          >
            try a sample
          </button>
        </div>

        {err && <p style={{ color: "#c0392b", marginTop: 16 }}>{err}</p>}

        {data && (
          <div style={{ marginTop: 24 }}>
            <p style={{ fontSize: 15, color: "#333" }}>
              {data.total} references &middot;{" "}
              <b style={{ color: "#2e8b57" }}>{data.found} found</b> &middot;{" "}
              <b style={{ color: "#c0392b" }}>{missing} to check</b>
              {data.truncated && <span style={{ color: "#888" }}> &middot; first 80 shown</span>}
            </p>
            <ol style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {data.refs.map((rc, i) => {
                const ok = rc.status === "found" && rc.work;
                return (
                  <li
                    key={i}
                    style={{
                      borderLeft: `4px solid ${ok ? "#2e8b57" : "#c0392b"}`,
                      background: ok ? "#f4f9f6" : "#fdf3f2",
                      padding: "10px 14px", borderRadius: 6, margin: "8px 0",
                    }}
                  >
                    <div style={{ fontSize: 12.5, color: "#888", marginBottom: 6 }}>{rc.ref}</div>
                    {ok ? (
                      <a
                        href={`/paper/${rc.work!.oaid}`}
                        target="_blank"
                        rel="noopener"
                        style={{ textDecoration: "none", color: "inherit", display: "block" }}
                      >
                        <div style={{ fontSize: 15, fontWeight: 600, color: "#1b2a4a" }}>
                          {rc.work!.title}
                          {rc.work!.is_retracted && (
                            <span style={{ color: "#c0392b", fontWeight: 700 }}> &middot; RETRACTED</span>
                          )}
                        </div>
                        <div style={{ fontSize: 13, color: "#555", marginTop: 2 }}>
                          {rc.work!.authors} &middot; {rc.work!.year} &middot;{" "}
                          <b>{rc.work!.cites.toLocaleString()} citations</b>
                          {rc.work!.venue ? ` · ${rc.work!.venue}` : ""}
                          <span style={{ color: "#2166ac" }}> &middot; view on the Ledger &rarr;</span>
                        </div>
                      </a>
                    ) : (
                      <div style={{ fontSize: 14, color: "#c0392b", fontWeight: 600 }}>
                        ⚠ no result found &mdash; check for validity
                        {rc.closest && (
                          <span style={{ fontWeight: 400, color: "#a06", fontStyle: "italic" }}>
                            {" "}(closest, rejected: &ldquo;{rc.closest}&rdquo;)
                          </span>
                        )}
                      </div>
                    )}
                  </li>
                );
              })}
            </ol>
            <p style={{ fontSize: 12, color: "#999", marginTop: 16 }}>
              Matching via Crossref&rsquo;s bibliographic resolver; a flag means &ldquo;could not confidently
              resolve&rdquo; &mdash; worth a human check, not proof of fabrication. Legitimate but poorly-indexed
              works (some books, non-English, very old) can also flag.
            </p>
          </div>
        )}
      </main>
    </>
  );
}
