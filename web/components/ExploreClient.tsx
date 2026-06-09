"use client";

import { useEffect, useState } from "react";
import type { RecordItem } from "@/lib/types";
import RecordTable from "./RecordTable";
import { SkeletonTable } from "./Skeleton";

type Sort = "qalField" | "qalSynth" | "cites" | "year";

// The calibrated seed communities, used to seed the field dropdown (others accrue from results).
const SEED_FIELDS: { sid: string; label: string }[] = [
  { sid: "1803", label: "Management Science and Operations Research" },
  { sid: "1802", label: "Information Systems and Management" },
  { sid: "1800", label: "General Decision Sciences" },
];

export default function ExploreClient() {
  const [all, setAll] = useState<RecordItem[]>([]);
  const [live, setLive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [qDebounced, setQDebounced] = useState("");
  const [field, setField] = useState(""); // subfield id
  const [year, setYear] = useState(0);
  const [calOnly, setCalOnly] = useState(false);
  const [sort, setSort] = useState<Sort>("qalField");
  const [fieldOpts, setFieldOpts] = useState(SEED_FIELDS);
  const [years, setYears] = useState<number[]>([]);

  // Debounce the search box so each keystroke doesn't hit the API.
  useEffect(() => {
    const t = setTimeout(() => setQDebounced(q), 300);
    return () => clearTimeout(t);
  }, [q]);

  // Server-side query: search + filters run against the FULL dataset, not a pre-fetched slice.
  useEffect(() => {
    const p = new URLSearchParams();
    if (qDebounced.trim()) p.set("q", qDebounced.trim());
    if (field) p.set("field", field);
    if (year) p.set("since", String(year));
    if (calOnly) p.set("calibrated_only", "true");
    p.set("sort", sort === "cites" ? "cites" : sort === "year" ? "year" : "qal");
    p.set("limit", "500");
    setLoading(true);
    let cancelled = false;
    fetch("/api/explore?" + p.toString())
      .then((r) => r.json())
      .then((d) => {
        if (cancelled) return;
        setAll(d.items ?? []);
        setLive(!!d.live);
      })
      .catch(() => {
        if (cancelled) return;
        setAll([]);
        setLive(false);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [qDebounced, field, year, calOnly, sort]);

  // Accumulate field + year dropdown options from results (union, so they never shrink).
  useEffect(() => {
    setFieldOpts((prev) => {
      const m = new Map(prev.map((f) => [f.sid, f.label]));
      for (const d of all) if (d.sid && d.subfield) m.set(d.sid, d.subfield);
      return [...m].map(([sid, label]) => ({ sid, label })).sort((a, b) => a.label.localeCompare(b.label));
    });
    setYears((prev) => {
      const s = new Set(prev);
      for (const d of all) if (d.year) s.add(d.year);
      return [...s].sort((a, b) => b - a);
    });
  }, [all]);

  const sortKey = sort; // RecordTable understands qalField | qalNeigh | cites | year
  const sortLabel =
    sort === "cites"
      ? "Cites"
      : sort === "year"
      ? "Yr"
      : sort === "qalSynth"
      ? "QaL · synthetic field"
      : "QaL · field";

  return (
    <div className="wrap-explore">
      <h1>Explore the Ledger</h1>
      <p className="lede">
        Search and rank records by QaL within a stated reference class and vintage. Leaderboards are
        just this view with a fixed filter and a QaL sort.
      </p>

      <div className="controls">
        <label>
          Search title or author
          <input
            id="q"
            type="text"
            placeholder="e.g. bandit, Terwiesch"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </label>
        <label>
          Field
          <select value={field} onChange={(e) => setField(e.target.value)}>
            <option value="">All fields</option>
            {fieldOpts.map((f) => (
              <option key={f.sid} value={f.sid}>
                {f.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Vintage (since)
          <select value={year} onChange={(e) => setYear(Number(e.target.value))}>
            <option value={0}>Any</option>
            {years.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>
        <label className="chk">
          <input type="checkbox" checked={calOnly} onChange={(e) => setCalOnly(e.target.checked)} />{" "}
          Calibrated only
        </label>
      </div>

      <div className="presets">
        <span className="pl">Leaderboards</span>
        {[
          { sid: "1803", short: "MS&OR" },
          { sid: "1802", short: "Info Systems" },
          { sid: "1800", short: "Decision Sciences" },
        ].map((f) => (
          <button
            key={f.sid}
            className="lead"
            onClick={() => {
              setField(f.sid);
              setCalOnly(true);
              setSort("qalSynth");
            }}
          >
            Top QaL · {f.short}
          </button>
        ))}
        <span className="pl" style={{ marginLeft: 6 }}>
          Sort
        </span>
        <button onClick={() => setSort("qalSynth")}>QaL · synthetic ★</button>
        <button onClick={() => setSort("qalField")}>QaL · field</button>
        <button onClick={() => setSort("cites")}>Most cited</button>
        <button onClick={() => setSort("year")}>Newest</button>
      </div>

      <p className="rcnote">
        Both reference classes are shown: <b>QaL · field</b> (the single OpenAlex subfield &amp;
        vintage) and <b>QaL · synthetic ★</b> (the <b>official</b> class — the paper ranked against a
        recency-weighted blend of its true intellectual community's cohorts; computed for the
        prefilled set, "—" until computed). Click any column to re-sort; the official number stays the
        synthetic field. Divergence between the two flags a field-sensitive paper and is itself
        information.
      </p>

      <div className="count">
        {loading ? (
          <>
            <span className="spin" />
            Loading records…
          </>
        ) : live ? (
          `${all.length} live match${all.length === 1 ? "" : "es"} from OpenAlex · most cited first`
        ) : (
          `${all.length}${all.length === 500 ? "+" : ""} records · sorted by ${sortLabel} ↓`
        )}
      </div>

      {!loading && live && all.length > 0 && (
        <div className="livebanner">
          Not in the indexed set — showing live matches from <b>OpenAlex</b>. Only the seed
          Decision-Sciences communities are pre-computed; these papers carry their{" "}
          <b>observed standing</b> only, with a calibrated QaL forecast{" "}
          <em>pending</em> (the QaL columns read &ldquo;pending&rdquo;). Open any paper for its live
          record.
        </div>
      )}

      {loading ? (
        <SkeletonTable rows={12} />
      ) : all.length === 0 ? (
        <div className="notfound" style={{ padding: "40px 24px" }}>
          No records match{q.trim() ? ` “${q.trim()}”` : " these filters"}
          {q.trim() ? " — in the index or on OpenAlex" : ""}. Note: only the seed Decision-Sciences
          communities are indexed so far.
        </div>
      ) : (
        <RecordTable key={sortKey} records={all} initialSortKey={sortKey} initialSortDir={-1} />
      )}

      <footer>
        <span className="wh">academic Ledger</span> · explore view, Level 0 prototype. Records,
        citations, fields and open-access status from OpenAlex (CC0). Two reference classes are shown
        side by side: the single-subfield field percentile and the synthetic field (a recency-weighted
        topic-mixture of full cohorts, §5); the <b>official</b> number is the synthetic field, fixed to
        prevent reference-class shopping, with column sorting for exploration. QaL forecast intervals
        are <em>illustrative pending calibration</em>, and the calibration mapping is currently
        field-based (QaL_spec.md).
      </footer>
    </div>
  );
}
