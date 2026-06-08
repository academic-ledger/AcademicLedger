"use client";

import { useEffect, useMemo, useState } from "react";
import type { RecordItem } from "@/lib/types";
import RecordTable from "./RecordTable";

type Sort = "qal" | "cites" | "year";

export default function ExploreClient() {
  const [all, setAll] = useState<RecordItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [field, setField] = useState(""); // subfield label
  const [year, setYear] = useState(0);
  const [calOnly, setCalOnly] = useState(false);
  const [rc, setRc] = useState<"neigh" | "field">("neigh");
  const [sort, setSort] = useState<Sort>("qal");

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

  const sortKey = sort === "cites" ? "cites" : sort === "year" ? "year" : "qal";

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
        <label>
          Reference class
          <select value={rc} onChange={(e) => setRc(e.target.value as "neigh" | "field")}>
            <option value="neigh">Co-citation neighborhood (official)</option>
            <option value="field">Detected field (exploration)</option>
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
              setSort("qal");
            }}
          >
            Top QaL · {sf.replace("Management Science & OR", "MS&OR").replace("Information Systems & Management", "Info Systems").replace("General Decision Sciences", "Decision Sciences")}
          </button>
        ))}
        <span className="pl" style={{ marginLeft: 6 }}>
          Sort
        </span>
        <button onClick={() => setSort("qal")}>By QaL</button>
        <button onClick={() => setSort("cites")}>Most cited</button>
        <button onClick={() => setSort("year")}>Newest</button>
      </div>

      <p className="rcnote">
        {rc === "neigh" ? (
          <>
            Reference class: <b>co-citation neighborhood</b> (official). In this prototype the figure
            shown is the within-detected-field percentile as a stand-in for the neighborhood.
          </>
        ) : (
          <>
            Reference class: <b>detected field</b> — exploration only; the official QaL is fixed to
            the co-citation neighborhood to prevent reference-class shopping.
          </>
        )}
      </p>

      <div className="count">
        {loading
          ? "Loading records…"
          : `${filtered.length} of ${all.length} records · sorted by ${
              sort === "qal" ? "QaL (eventual %)" : sort === "cites" ? "Cites" : "Yr"
            } ↓`}
      </div>

      <RecordTable key={sortKey} records={filtered} initialSortKey={sortKey} initialSortDir={-1} />

      <footer>
        <span className="wh">academic Ledger</span> · explore view, Level 0 prototype. Records,
        citations, fields and open-access status from OpenAlex (CC0); observed percentiles are exact
        within-(subfield, year) standing. The official reference class is the co-citation
        neighborhood; in this prototype the displayed standing is the within-detected-field
        percentile as a stand-in, and QaL forecast intervals are <em>illustrative pending
        calibration</em> (QaL_spec.md). The official number is fixed; the reference-class selector is
        for exploration only.
      </footer>
    </div>
  );
}
