import Brand from "@/components/Brand";
import CitationCard from "@/components/CitationCard";
import { getQalRecord } from "@/lib/queries";

export const dynamic = "force-dynamic";

const BUCKET_DEFS = [
  { key: "lt50", xl: "<50", lo: 0, hi: 50 },
  { key: "b50_75", xl: "50–75", lo: 50, hi: 75 },
  { key: "b75_90", xl: "75–90", lo: 75, hi: 90 },
  { key: "b90_95", xl: "90–95", lo: 90, hi: 95 },
  { key: "b95_99", xl: "95–99", lo: 95, hi: 99 },
  { key: "b99_100", xl: "99–100", lo: 99, hi: 100 },
] as const;

export default async function PaperPage({ params }: { params: { oaid: string } }) {
  const rec: any = await getQalRecord(params.oaid);
  if (!rec) {
    return (
      <>
        <Brand />
        <div className="notfound">No record for {params.oaid}.</div>
      </>
    );
  }

  const calibrated = rec.calibrated && rec.qal;
  const age = rec.year ? Math.max(1, 2026 - rec.year + 1) : null;
  const src = rec.doi || `https://openalex.org/${rec.oaid}`;

  // U4: a clean formatted citation from the fields we have (volume/issue/pages pending the
  // OpenAlex `biblio` field — see backlog U4).
  const citation = [
    rec.authors,
    rec.year ? `(${rec.year}).` : null,
    rec.title ? `${rec.title}.` : null,
    rec.venue ? `${rec.venue}.` : null,
    rec.doi || `https://openalex.org/${rec.oaid}`,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <>
      <Brand />
      <div className="wrap-paper">
        <h1 className="title">{rec.title}</h1>
        {rec.authors && <p className="authors">{rec.authors}</p>}
        <p className="meta">
          {rec.venue && <span className="pill">{rec.venue}</span>}
          {rec.reference_class?.field_label && <span className="pill">{rec.reference_class.field_label}</span>}
          {rec.year && (
            <>
              {" "}
              Posted <b>{rec.year}</b>
              {age ? ` · ${age} years on the record` : ""}
            </>
          )}
        </p>

        {/* ===== QaL HERO ===== */}
        <div className="qhero">
          <div>
            <div className="qal-tag">Quality on the academic Ledger</div>
            <div className="qal-name">
              Q<span className="a">a</span>L
            </div>
            {calibrated ? (
              <>
                <div className="qal-est">
                  <span className="qal-lo" title="lower bound, 90% interval">
                    {rec.qal.ci90[0]}
                  </span>
                  <span className="qal-pt" title="point estimate">
                    {rec.qal.point}
                  </span>
                  <span className="qal-hi" title="upper bound, 90% interval">
                    {rec.qal.ci90[1]}
                  </span>
                </div>
                <div className="qal-cap">
                  eventual percentile · point estimate with 90% interval · <em>illustrative</em>
                </div>
              </>
            ) : (
              <>
                <div className="qal-pending">calibration-pending</div>
                <div className="qal-cap">
                  Observed standing is{" "}
                  <b>{rec.obs_percentile != null ? `${rec.obs_percentile}th percentile` : "—"}</b> in
                  field &amp; vintage. A calibrated QaL forecast is shown once this community passes the
                  Layer-B back-test.
                </div>
              </>
            )}
            {rec.reference_class?.kind === "synthetic" ? (
              <div className="qal-rc">
                <b>Reference class:</b> synthetic field · official headline
                <br />
                recency-weighted blend of its community&rsquo;s cohorts
                {rec.reference_class.field_percentile != null && (
                  <>
                    {" "}
                    · <span title="for contrast — single OpenAlex subfield">field pct{" "}
                    {rec.reference_class.field_percentile}</span>
                  </>
                )}
              </div>
            ) : (
              <div className="qal-rc">
                <b>Reference class:</b> single-field percentile{" "}
                <span style={{ color: "#9aa3af" }}>(stand-in)</span>
                <br />
                synthetic field pending for this paper
              </div>
            )}
          </div>
          <div>
            {calibrated ? (
              <>
                <div className="bkt">
                  {BUCKET_DEFS.map((d) => {
                    const val: number = rec.qal.buckets[d.key] ?? 0;
                    const maxVal = Math.max(...BUCKET_DEFS.map((b) => rec.qal.buckets[b.key] ?? 0), 1);
                    const h = Math.max(2, Math.round((val / maxVal) * 128));
                    const hot = rec.qal.point >= d.lo && rec.qal.point < (d.hi === 100 ? 101 : d.hi);
                    return (
                      <div className={`col ${hot ? "hot" : ""}`} key={d.key}>
                        <div className="p">{val}%</div>
                        <div className="barv" style={{ height: h }} />
                        <div className="xl">{d.xl}</div>
                      </div>
                    );
                  })}
                </div>
                <div className="bkt-cap">
                  probability of landing in each NSF percentile class (top 50 / 25 / 10 / 5 / 1%)
                </div>
              </>
            ) : (
              <div className="bkt-cap" style={{ textAlign: "left" }}>
                The NSF-bucket probability forecast appears for papers in a calibrated community.
              </div>
            )}
          </div>
        </div>
        {calibrated && (
          <p className="qal-cap" style={{ margin: "-4px 2px 0" }}>
            Decided late: the interval is wide early and narrows as evidence accrues.
          </p>
        )}

        {/* ===== REFERENCE-CLASS COMPOSITION — flat strip, no bars ===== */}
        {rec.composition && rec.composition.length > 0 && (() => {
          const shown = rec.composition.filter((c: any) => c.weight >= 0.02);
          const rolled = rec.composition.filter((c: any) => c.weight < 0.02);
          const rolledPct = Math.round(rolled.reduce((s: number, c: any) => s + c.weight, 0) * 100);
          return (
            <div className="compstrip">
              <span className="compstrip-label">Synthetic field · weighted by recent references</span>
              <span className="compstrip-list">
                {shown.map((c: any, i: number) => (
                  <span key={c.sid}>
                    {i > 0 ? " · " : ""}
                    {c.name} ({Math.round(c.weight * 100)}%)
                  </span>
                ))}
                {rolled.length > 0 ? ` · +${rolled.length} more (${rolledPct}%)` : ""}
              </span>
              <span className="compstrip-note">
                The official reference class is this recency-weighted blend of the communities the
                paper actually draws on (QaL_spec §5), not OpenAlex&rsquo;s single label
                {rec.field ? ` (“${rec.field}”)` : ""}. Divergence is the signal.
              </span>
            </div>
          );
        })()}

        {/* ===== EVIDENCE ===== */}
        <div className="card">
          <h2>
            Evidence behind the estimate <span className="src">— pulled from OpenAlex</span>
          </h2>
          <div className="grid">
            <div className="cell">
              <div className="v">{(rec.evidence.cited_by_count || 0).toLocaleString()}</div>
              <div className="l">Citations (total)</div>
            </div>
            <div className="cell">
              <div className="v">{rec.obs_percentile != null ? `${rec.obs_percentile}%` : "—"}</div>
              <div className="l">
                Observed percentile{" "}
                {rec.reference_class?.kind === "synthetic" ? "(synthetic field)" : "(field & vintage)"}
              </div>
            </div>
            {/* U5: Access (oa_status) cell removed — Unpaywall's OA label is not reader-useful and
                understates real availability. is_oa/oa_url kept in the data layer. */}
            <div className="cell">
              <div className="v">{rec.evidence.is_retracted ? "Retracted" : "None"}</div>
              <div className="l">Retractions / corrections</div>
            </div>
            <div className="cell">
              <div className="v">{age ? `${age} yr` : "—"}</div>
              <div className="l">Age since posting</div>
            </div>
            <div className="cell">
              <div className="v">{rec.field || rec.subfield || "—"}</div>
              <div className="l">Detected field (OpenAlex)</div>
            </div>
          </div>
        </div>

        {/* ===== CITATION ===== */}
        <CitationCard citation={citation} />

        {/* ===== LINKS ===== */}
        <div className="card">
          <h2>
            Read &amp; cite <span className="src">— the Ledger points to the record; it does not host it</span>
          </h2>
          <div className="links">
            {rec.doi && (
              <a href={rec.doi}>
                Read at source <span className="arr">↗</span>
              </a>
            )}
            {rec.doi && (
              <a href={rec.doi}>
                {rec.doi.replace("https://doi.org/", "DOI ")} <span className="arr">↗</span>
              </a>
            )}
            <a href={`https://openalex.org/${rec.oaid}`}>
              OpenAlex record <span className="arr">↗</span>
            </a>
            <a href={`https://scholar.google.com/scholar?q=${encodeURIComponent(rec.title)}`}>
              Google Scholar <span className="arr">↗</span>
            </a>
            <a href={`https://openalex.org/works?filter=cites:${rec.oaid}`} target="_blank" rel="noopener noreferrer">
              Cited by ({(rec.evidence.cited_by_count || 0).toLocaleString()}) ↗
            </a>
          </div>
        </div>

        <p className="statusline">
          <span className="dot" />
          <b>Status:</b> indexed and QaL-estimated. Refereed and Canon tiers, endorsements, and
          discussion require the community layer and are not part of this MVP.
        </p>

        <footer>
          <span className="wh">academic Ledger is an independent, non-commercial record of scholarship.</span>{" "}
          QaL computed from open public data (OpenAlex, OpenCitations, Crossref, ORCID); method
          version {rec.method_version}; data snapshot {rec.data_snapshot}. Prototype: metadata and
          observed percentiles are real; QaL point estimates and the synthetic field are
          illustrative pending Level 0 calibration.
        </footer>
      </div>
    </>
  );
}
