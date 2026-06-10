"use client";

import { useState } from "react";
import RecordTable from "./RecordTable";
import AuthorSearch from "./AuthorSearch";
import type { AuthorPayload } from "@/lib/types";

const BINS: { l: string; t: (x: number) => boolean }[] = [
  { l: "Top 1% (≥99)", t: (x) => x >= 99 },
  { l: "1–5% (95–99)", t: (x) => x >= 95 && x < 99 },
  { l: "5–10% (90–95)", t: (x) => x >= 90 && x < 95 },
  { l: "10–25% (75–90)", t: (x) => x >= 75 && x < 90 },
  { l: "25–50% (50–75)", t: (x) => x >= 50 && x < 75 },
  { l: "Below 50", t: (x) => x < 50 },
];

export default function AuthorView({ payload }: { payload: AuthorPayload }) {
  const { author, works } = payload;
  const obsvals = works.map((w) => w.obs).filter((x): x is number => x != null);
  const counts = BINS.map((b) => obsvals.filter(b.t).length);
  const mx = Math.max(1, ...counts);

  const fmap = new Map<string, { n: number; cal: boolean; field: string | null }>();
  works.forEach((w) => {
    const k = w.subfield || "Unclassified";
    const cur = fmap.get(k) || { n: 0, cal: w.calibrated, field: w.field };
    cur.n += 1;
    fmap.set(k, cur);
  });
  const frows = [...fmap.entries()].sort((a, b) => b[1].n - a[1].n);
  const calN = works.filter((w) => w.calibrated).length;

  // Click a field to filter the Works table to that subfield (e.g. "what does OpenAlex call
  // Museology in my record?"). null = show everything.
  const [selSub, setSelSub] = useState<string | null>(null);
  const shownWorks = selSub ? works.filter((w) => (w.subfield || "Unclassified") === selSub) : works;

  return (
    <div className="wrap-author">
      <div className="authtop">
        <span className="authtop-l">Jump to another author</span>
        <AuthorSearch />
      </div>
      <div className="ahead">
        <div>
          <h1 className="name">{author.name}</h1>
          <p className="affil">{author.aff || ""}</p>
          <p className="ids">
            {author.orcid && (
              <a href={author.orcid} title="ORCID (verified-identity overlay)">
                <span className="orcd">iD</span> {author.orcid.replace("https://", "")}
              </a>
            )}
            <a href={`https://openalex.org/${author.oaid}`} title="OpenAlex author entity (the canonical key)">
              OpenAlex {author.oaid}
            </a>
          </p>
        </div>
        <div className="astat">
          <div className="c">
            <div className="v">{author.works_count}</div>
            <div className="l">works</div>
          </div>
          <div className="c">
            <div className="v">{(author.cites || 0).toLocaleString()}</div>
            <div className="l">citations</div>
          </div>
          <div className="c">
            <div className="v">{works.length}</div>
            <div className="l">shown here</div>
          </div>
        </div>
      </div>

      <div className="twocol">
        <div className="card dist">
          <h2>
            Portfolio — where the work stands{" "}
            <span style={{ fontWeight: 400, textTransform: "none", letterSpacing: 0, color: "#aab0bb", fontSize: 11 }}>
              · observed percentile, within field &amp; vintage
            </span>
          </h2>
          <div>
            {BINS.map((b, i) => (
              <div className={`row ${i <= 1 ? "hot" : ""}`} key={b.l}>
                <div className="lab">{b.l}</div>
                <div className="track">
                  <div className="fill" style={{ width: `${Math.round((100 * counts[i]) / mx)}%` }} />
                </div>
                <div className="n">{counts[i]}</div>
              </div>
            ))}
          </div>
          <div className="distcap">
            Distribution of the shown works by observed within-field-and-vintage percentile. This is
            the universal layer and is available for every paper.
          </div>
          <div className="noscore" style={{ marginTop: 12 }}>
            <b>No single author score.</b> academic Ledger reports quality per paper, with an
            interval, and deliberately does not roll a scholar up to one number. A personal scalar
            would recreate the h-index incentives the project rejects.
          </div>
        </div>

        <div className="card fields">
          <h2>
            Fields represented &amp; calibration coverage{" "}
            <span className="src">· click a field to filter the works below</span>
          </h2>
          <div>
            {frows.map(([sf, o]) => (
              <div
                className={`frow click${selSub === sf ? " sel" : ""}`}
                key={sf}
                role="button"
                tabIndex={0}
                onClick={() => setSelSub((cur) => (cur === sf ? null : sf))}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setSelSub((cur) => (cur === sf ? null : sf));
                  }
                }}
                title={selSub === sf ? "Show all works" : `Show only ${sf} works`}
              >
                <span className="ftag">
                  {sf} <span style={{ color: "#aab0bb" }}>· {o.field || ""}</span>
                </span>
                {o.cal ? <span className="seedb">calibrated</span> : <span className="pendb">pending</span>}
                <span className="fn">{o.n}</span>
              </div>
            ))}
          </div>
          <div className="coverline">
            <b>
              {calN} of {works.length}
            </b>{" "}
            shown works are in a calibrated community (Decision Sciences seed: Management Science &amp;
            OR, Information Systems &amp; Management, General Decision Sciences). The rest show observed
            standing only and carry a <span className="penddot">calibration-pending</span> forecast
            until their community is calibrated.
          </div>
        </div>
      </div>

      <div className="card">
        <h2>
          {selSub ? (
            <>
              Works in <span style={{ color: "#16243d" }}>{selSub}</span>{" "}
              <span className="src">
                · {shownWorks.length} of {works.length} ·{" "}
                <button className="linkbtn" onClick={() => setSelSub(null)}>
                  show all
                </button>
              </span>
            </>
          ) : (
            <>
              Works <span className="src">· click a column to sort · titles link to the record</span>
            </>
          )}
        </h2>
        <RecordTable
          key={selSub || "all"}
          records={shownWorks}
          initialSortKey="cites"
          initialSortDir={-1}
        />
      </div>

      <p className="coverline">
        <b>Disambiguation.</b> Works are clustered by OpenAlex&rsquo;s author ID, which is imperfect;
        some records may be mis-attributed. A later release lets an author claim and curate the
        profile via ORCID, which becomes the verified-identity layer.
      </p>

      <footer>
        <span className="wh">academic Ledger</span> · author view, Level 0 prototype. Identity,
        works, citations, fields and open-access status from OpenAlex (CC0). Observed percentiles
        computed live by exact within-(subfield, year) count queries. QaL forecast intervals are{" "}
        <em>illustrative pending calibration</em> (QaL_spec.md, §5). No participant data; no conferred
        tiers in the MVP.
      </footer>
    </div>
  );
}
