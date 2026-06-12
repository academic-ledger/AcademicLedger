"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { RecordItem } from "@/lib/types";
import RecordTable, { type SortKey } from "./RecordTable";
import { SkeletonTable } from "./Skeleton";

interface AuthorSug {
  oaid: string;
  name: string;
  institution: string | null;
  works_count: number | null;
}

// The calibrated seed communities, used to seed the field dropdown (others accrue from results).
const SEED_FIELDS: { sid: string; label: string }[] = [
  { sid: "1803", label: "Management Science and Operations Research" },
  { sid: "1802", label: "Information Systems and Management" },
  { sid: "1800", label: "General Decision Sciences" },
];

// U9: vintages are a continuous range (current year down to a floor), not the set of years that
// happen to appear in the loaded rows — otherwise unsampled years (2024, 2025, …) drop out.
const AS_OF = 2026;
const MIN_VINTAGE = 2000;
const VINTAGES: number[] = Array.from({ length: AS_OF - MIN_VINTAGE + 1 }, (_, i) => AS_OF - i);

const SORT_KEYS: SortKey[] = ["_r", "title", "subfield", "year", "cites", "qalField", "qalSynth"];
const SORT_LABEL: Record<SortKey, string> = {
  _r: "rank",
  title: "Title",
  subfield: "Field",
  year: "Yr",
  cites: "Cites",
  qalField: "QaL · field",
  qalSynth: "QaL · synthetic field",
};
// The server only orders by qal / cites / year (it picks WHICH top records load); the table then
// displays them by the chosen column. title/subfield have no server order — keep the qal selection.
const serverSort = (k: SortKey): string => (k === "cites" ? "cites" : k === "year" ? "year" : "qal");

export default function ExploreClient() {
  const router = useRouter();
  const sp = useSearchParams();
  // Initial view state is read from the URL query, so navigating to a paper and hitting Back —
  // or sharing/bookmarking the link — restores the same filters, sort, and author selection.
  const [all, setAll] = useState<RecordItem[]>([]);
  const [live, setLive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState(() => sp.get("q") ?? "");
  const [qDebounced, setQDebounced] = useState(() => sp.get("q") ?? "");
  const [field, setField] = useState(() => sp.get("field") ?? ""); // subfield id
  const [year, setYear] = useState(() => Number(sp.get("since")) || 0);
  const [calOnly, setCalOnly] = useState(() => sp.get("cal") === "1");
  const [tk, setTk] = useState<SortKey>(() => {
    const s = sp.get("sort") as SortKey;
    return SORT_KEYS.includes(s) ? s : "qalField";
  });
  const [td, setTd] = useState<1 | -1>(() => (sp.get("dir") === "1" ? 1 : -1));
  const [fieldOpts, setFieldOpts] = useState(SEED_FIELDS);
  const [authorSugs, setAuthorSugs] = useState<AuthorSug[]>([]);
  const [authOpen, setAuthOpen] = useState(false);
  const [authActive, setAuthActive] = useState(-1);
  const [authorFilter, setAuthorFilter] = useState<{ oaid: string; name: string } | null>(() => {
    const a = sp.get("author");
    return a ? { oaid: a, name: sp.get("an") ?? "" } : null;
  });
  const [authorWorks, setAuthorWorks] = useState<RecordItem[]>([]);
  const searchRef = useRef<HTMLDivElement>(null);
  const restoredScroll = useRef(false);

  const ssort = serverSort(tk); // the server-side ordering implied by the chosen column

  // Set the table sort (key + direction). Presets always sort descending.
  function chooseSort(k: SortKey) {
    setTk(k);
    setTd(-1);
  }

  // Pick an author from the dropdown -> filter Explore in place to that author's papers (ranked),
  // rather than navigating away to their profile page.
  function pickAuthor(s: AuthorSug) {
    setAuthorFilter({ oaid: s.oaid, name: s.name });
    setQ(s.name);
    setAuthOpen(false);
    setAuthorSugs([]);
  }

  // Debounce the search box so each keystroke doesn't hit the API.
  useEffect(() => {
    const t = setTimeout(() => setQDebounced(q), 300);
    return () => clearTimeout(t);
  }, [q]);

  // Author typeahead on the search box — same mechanism as the author-page search. Selecting a
  // suggestion filters Explore in place to that author's papers (pickAuthor), staying in the
  // ranked-records view rather than navigating to the profile page.
  useEffect(() => {
    if (authorFilter) return; // a filter is active; don't re-suggest from the pinned name
    const term = qDebounced.trim();
    if (term.length < 2) {
      setAuthorSugs([]);
      return;
    }
    let cancelled = false;
    fetch("/api/authors/search?q=" + encodeURIComponent(term))
      .then((r) => r.json())
      .then((d) => {
        if (cancelled) return;
        setAuthorSugs(d.items ?? []);
        setAuthOpen(true);
        setAuthActive(-1);
      })
      .catch(() => !cancelled && setAuthorSugs([]));
    return () => {
      cancelled = true;
    };
  }, [qDebounced, authorFilter]);

  // Close the author dropdown on an outside click.
  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) setAuthOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  // Author filter active -> fetch that author's papers once (live, ranked), reusing the author API.
  useEffect(() => {
    if (!authorFilter) {
      setAuthorWorks([]);
      return;
    }
    setLoading(true);
    let cancelled = false;
    fetch("/api/author/" + authorFilter.oaid)
      .then((r) => r.json())
      .then((d) => {
        if (cancelled) return;
        setAuthorWorks(d.works ?? []);
        setLive(false);
      })
      .catch(() => !cancelled && setAuthorWorks([]))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [authorFilter]);

  // Author-filtered view: apply the field / vintage / calibrated controls CLIENT-SIDE to the
  // author's works (they're all loaded), so those dropdowns work here too.
  useEffect(() => {
    if (!authorFilter) return;
    setAll(
      authorWorks.filter(
        (w) =>
          (!field || w.sid === field) &&
          (!year || (w.year != null && w.year >= year)) &&
          (!calOnly || w.calibrated)
      )
    );
  }, [authorFilter, authorWorks, field, year, calOnly]);

  // Server-side query: search + filters run against the FULL dataset, not a pre-fetched slice.
  // Depends on the server ORDERING (ssort), not the display column, so re-sorting the loaded set by
  // title/subfield doesn't trigger a re-fetch.
  useEffect(() => {
    if (authorFilter) return; // author-filtered view is handled by the effect above
    const p = new URLSearchParams();
    if (qDebounced.trim()) p.set("q", qDebounced.trim());
    if (field) p.set("field", field);
    if (year) p.set("since", String(year));
    if (calOnly) p.set("calibrated_only", "true");
    p.set("sort", ssort);
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
  }, [qDebounced, field, year, calOnly, ssort, authorFilter]);

  // Accumulate field dropdown options from results (union, so they never shrink). Vintages are a
  // fixed continuous range (VINTAGES), not result-driven — see U9.
  useEffect(() => {
    setFieldOpts((prev) => {
      const m = new Map(prev.map((f) => [f.sid, f.label]));
      for (const d of all) if (d.sid && d.subfield) m.set(d.sid, d.subfield);
      return [...m].map(([sid, label]) => ({ sid, label })).sort((a, b) => a.label.localeCompare(b.label));
    });
  }, [all]);

  // Mirror the view state into the URL (replace — no new history entry per keystroke/click) so that
  // Back from a paper restores it. Keyed on the *applied* values (qDebounced) that drive results.
  useEffect(() => {
    const p = new URLSearchParams();
    if (qDebounced.trim()) p.set("q", qDebounced.trim());
    if (field) p.set("field", field);
    if (year) p.set("since", String(year));
    if (calOnly) p.set("cal", "1");
    if (tk !== "qalField") p.set("sort", tk);
    if (td !== -1) p.set("dir", "1");
    if (authorFilter) {
      p.set("author", authorFilter.oaid);
      if (authorFilter.name) p.set("an", authorFilter.name);
    }
    const qs = p.toString();
    router.replace(qs ? `/explore?${qs}` : "/explore", { scroll: false });
  }, [qDebounced, field, year, calOnly, tk, td, authorFilter, router]);

  // Remember scroll position per view, and restore it once after the first results render — so Back
  // lands you where you were in the list, not at the top.
  useEffect(() => {
    const onScroll = () => {
      try {
        sessionStorage.setItem("explore:y:" + window.location.search, String(window.scrollY));
      } catch {}
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  useEffect(() => {
    if (restoredScroll.current || loading) return;
    restoredScroll.current = true;
    try {
      const y = sessionStorage.getItem("explore:y:" + window.location.search);
      if (y) requestAnimationFrame(() => window.scrollTo(0, parseInt(y, 10)));
    } catch {}
  }, [loading]);

  const sortLabel = SORT_LABEL[tk] ?? "QaL · field";
  const arrow = td < 0 ? "↓" : "↑";

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
          <div className="expl-search" ref={searchRef}>
            <input
              id="q"
              type="text"
              placeholder="e.g. bandit, Cachon, Terwiesch"
              value={q}
              autoComplete="off"
              onChange={(e) => {
                setQ(e.target.value);
                if (authorFilter) setAuthorFilter(null); // typing exits the author filter
              }}
              onFocus={() => authorSugs.length && setAuthOpen(true)}
              onKeyDown={(e) => {
                if (!authOpen || !authorSugs.length) return;
                if (e.key === "ArrowDown") {
                  e.preventDefault();
                  setAuthActive((a) => Math.min(a + 1, authorSugs.length - 1));
                } else if (e.key === "ArrowUp") {
                  e.preventDefault();
                  setAuthActive((a) => Math.max(a - 1, 0));
                } else if (e.key === "Enter" && authActive >= 0) {
                  e.preventDefault();
                  pickAuthor(authorSugs[authActive]);
                } else if (e.key === "Escape") {
                  setAuthOpen(false);
                }
              }}
            />
            {authOpen && authorSugs.length > 0 && (
              <ul className="authsug">
                <li className="sug-head">Authors — filter Explore to their papers</li>
                {authorSugs.map((s, i) => (
                  <li
                    key={s.oaid}
                    className={i === authActive ? "on" : ""}
                    onMouseEnter={() => setAuthActive(i)}
                    onMouseDown={(e) => {
                      e.preventDefault();
                      pickAuthor(s);
                    }}
                  >
                    <span className="nm">{s.name}</span>
                    <span className="meta">
                      {s.institution || "—"}
                      {s.works_count != null ? ` · ${s.works_count.toLocaleString()} works` : ""}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
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
            {VINTAGES.map((y) => (
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
              chooseSort("qalSynth");
            }}
          >
            Top QaL · {f.short}
          </button>
        ))}
        <span className="pl" style={{ marginLeft: 6 }}>
          Sort
        </span>
        <button onClick={() => chooseSort("qalSynth")}>QaL · synthetic ★</button>
        <button onClick={() => chooseSort("qalField")}>QaL · field</button>
        <button onClick={() => chooseSort("cites")}>Most cited</button>
        <button onClick={() => chooseSort("year")}>Newest</button>
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
        ) : authorFilter ? (
          <>
            Papers by <b style={{ color: "#16243d" }}>{authorFilter.name}</b> · {all.length} ·{" "}
            sorted by {sortLabel} {arrow} ·{" "}
            <button
              className="linkbtn"
              onClick={() => {
                setAuthorFilter(null);
                setQ("");
              }}
            >
              clear
            </button>
          </>
        ) : live ? (
          `${all.length} live match${all.length === 1 ? "" : "es"} from OpenAlex · most cited first`
        ) : (
          `${all.length}${all.length === 500 ? "+" : ""} records · sorted by ${sortLabel} ${arrow}`
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
          {authorFilter ? (
            <>No papers found for {authorFilter.name}.</>
          ) : (
            <>
              No records match{q.trim() ? ` “${q.trim()}”` : " these filters"}
              {q.trim() ? " — in the index or on OpenAlex" : ""}. Note: only the seed
              Decision-Sciences communities are indexed so far.
            </>
          )}
        </div>
      ) : (
        <RecordTable records={all} sortKey={tk} sortDir={td} onSortChange={(k, d) => { setTk(k); setTd(d); }} />
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
