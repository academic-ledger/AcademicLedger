"use client";

import { useEffect, useMemo, useState } from "react";
import type { RecordItem } from "@/lib/types";
import RecordTable from "./RecordTable";
import { SkeletonTable } from "./Skeleton";

type Sort = "qalField" | "qalSynth" | "cites" | "year";

export default function ExploreClient() {
  const [all, setAll] = useState<RecordItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [field, setField] = useState(""); // subfield label
  const [year, setYear] = useState(0);
  const [calOnly, setCalOnly] = useState(false);
  const [sort, setSort] = useState<Sort>("qalField");

  useEffect(() => {
    fetch("/api/explore?sort=qal&limit=1000")
      .then((r) => r.json())
      .then((d) => setAll(d.items ?? []))
      .catch(() => setAll([]))
      .finally(() => setLoading(false));
  }, []);

  const fields = useMemo(
    () => [...new Set(all.map((d) => d.subfield).filter(Boolean) as string[])].sort(),
    [all]
  );
  const years = useMemo(
    () => [...new Set(all.map((d) => d.year).filter(Boolean) as number[])].sort((a, b) => b - a),
    [all]
  );

  const filtered = useMemo(() => {
    const ql = q.trim().toLowerCase();
    return all.filter((d) => {
      if (ql && !(d.title?.toLowerCase().includes(ql) || d.authors?.toLowerCase().includes(ql)))
        return false;
      if (field && d.subfield !== field) return false;
      if (year && (d.year || 0) < year) return false;
      if (calOnly && !d.calibrated) return false;
      return true;
    });
  }, [all, q, field, year, calOnly]);

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
            {fields.map((f) => (
              <option key={f} value={f}>
                {f}
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
          "Management Science & OR",
          "Information Systems & Management",
          "General Decision Sciences",
        ].map((sf) => (
          <button
            key={sf}
            className="lead"
            onClick={() => {
              setField(sf);
              setCalOnly(true);
              setSort("qalSynth");
            }}
          >
            Top QaL · {sf.replace("Management Science & OR", "MS&OR").replace("Information Systems & Management", "Info Systems").replace("General Decision Sciences", "Decision Sciences")}
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
        ) : (
          `${filtered.length} of ${all.length} records · sorted by ${sortLabel} ↓`
        )}
      </div>

      {loading ? (
        <SkeletonTable rows={12} />
      ) : (
        <RecordTable key={sortKey} records={filtered} initialSortKey={sortKey} initialSortDir={-1} />
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
