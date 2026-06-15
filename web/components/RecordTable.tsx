"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import Byline from "./Byline";
import type { MetricView, RecordItem } from "@/lib/types";
import { SUBFIELD_SHORT } from "@/lib/subfieldShort";

export type SortKey = "_r" | "title" | "subfield" | "year" | "cites" | "qalField" | "qalSynth";
type ColType = "rank" | "str" | "num";

// The header row is CSS-uppercased; keep the "QaL" wordmark mixed-case with a no-transform span.
const NOUP = { textTransform: "none" as const };
const COLS: { k: SortKey; t: ReactNode; cls?: string; type: ColType }[] = [
  { k: "_r", t: "#", cls: "rank", type: "rank" },
  { k: "title", t: "Title", type: "str" },
  { k: "subfield", t: "Fields", type: "str" },
  { k: "year", t: "Yr", cls: "num", type: "num" },
  { k: "cites", t: "Cites", cls: "num", type: "num" },
  { k: "qalField", t: <><span style={NOUP}>QaL</span> · field</>, cls: "num", type: "num" },
  { k: "qalSynth", t: <><span style={NOUP}>QaL</span> · synthetic ★</>, cls: "num", type: "num" },
];

function sortVal(w: RecordItem, key: SortKey): number | string {
  if (key === "qalField") return w.metrics?.field?.qal?.point ?? -1;
  if (key === "qalSynth") return w.metrics?.synthetic?.qal?.point ?? -1;
  const v = (w as any)[key];
  return v ?? -1;
}

function QalCell({ m, official }: { m: MetricView | null | undefined; official: boolean }) {
  if (!m) return <span className="qdash">—</span>; // this reference class doesn't apply
  if (!m.qal) return <span className="pend">pending</span>;
  return (
    <>
      <span className={official ? "pt" : "pt2"}>{m.qal.point}</span>{" "}
      <span className="ci">
        [{m.qal.lo}–{m.qal.hi}]
      </span>
    </>
  );
}

// "Fields" column. With a synthetic blend: dominant subfield + weight + "+N more", full blend on
// hover (native title — robust inside the scrollable table). Otherwise the single OpenAlex label;
// "· blend pending" (italic) when explore looked and found no synthetic field, plain when the
// composition wasn't fetched for this view (e.g. the author page).
function FieldCell({ w }: { w: RecordItem }) {
  const muted = "#9aa3af";
  const comp = w.composition;
  if (comp && comp.length > 0) {
    const pct = (x: number) => Math.round(x * 100);
    const d = comp[0];
    const more = comp.length - 1;
    const tip = "Synthetic field — " + comp.map((c) => `${c.name} ${pct(c.weight)}%`).join(" · ");
    return (
      <span className="ftagsm" title={tip} style={{ cursor: "help" }}>
        {d.short} <span style={{ color: muted }}>{pct(d.weight)}%</span>
        {more > 0 ? (
          <span style={{ color: muted, borderBottom: `1px dotted ${muted}` }}> · +{more} more</span>
        ) : null}
      </span>
    );
  }
  const label = (w.sid && SUBFIELD_SHORT[w.sid]) || w.subfield || "—";
  if (comp) {
    return (
      <span className="ftagsm">
        {label} <span style={{ fontStyle: "italic", color: muted }}>· blend pending</span>
      </span>
    );
  }
  return <span className="ftagsm">{label}</span>;
}

export default function RecordTable({
  records,
  initialSortKey = "cites",
  initialSortDir = -1,
  sortKey: cSortKey,
  sortDir: cSortDir,
  onSortChange,
}: {
  records: RecordItem[];
  initialSortKey?: SortKey;
  initialSortDir?: 1 | -1;
  // Controlled mode: when onSortChange is given, the parent owns the sort (so it can persist it,
  // e.g. in the URL). Otherwise the table keeps its own sort state (used by the author page).
  sortKey?: SortKey;
  sortDir?: 1 | -1;
  onSortChange?: (k: SortKey, d: 1 | -1) => void;
}) {
  const [iSortKey, setISortKey] = useState<SortKey>(initialSortKey);
  const [iSortDir, setISortDir] = useState<1 | -1>(initialSortDir);
  const controlled = onSortChange != null;
  const sortKey = controlled ? cSortKey ?? initialSortKey : iSortKey;
  const sortDir = controlled ? cSortDir ?? initialSortDir : iSortDir;

  function clickHeader(k: SortKey, type: ColType) {
    if (type === "rank") return;
    const nd: 1 | -1 = k === sortKey ? ((sortDir * -1) as 1 | -1) : type === "str" ? 1 : -1;
    if (controlled) onSortChange!(k, nd);
    else {
      setISortKey(k);
      setISortDir(nd);
    }
  }

  const col = COLS.find((c) => c.k === sortKey)!;
  const rows = records.slice().sort((a, b) => {
    let va = sortVal(a, sortKey);
    let vb = sortVal(b, sortKey);
    if (col.type === "str") return String(va).localeCompare(String(vb)) * sortDir;
    return ((va as number) - (vb as number)) * sortDir;
  });

  return (
    <div className="tbl-scroll">
      <table className="recs">
        <thead>
          <tr>
            {COLS.map((c) => {
              const act = c.k === sortKey ? " act" : "";
              const ar = c.k === sortKey ? (sortDir < 0 ? " ▼" : " ▲") : "";
              return (
                <th
                  key={c.k}
                  className={`${c.cls || ""}${act}`.trim()}
                  onClick={() => clickHeader(c.k, c.type)}
                >
                  {c.t}
                  {ar}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {rows.map((w, i) => {
            const src = w.doi || `https://openalex.org/${w.oaid}`;
            return (
              <tr key={w.oaid + i}>
                <td className="rank">{i + 1}</td>
                <td>
                  <div className="rtitle">
                    <Link href={`/paper/${w.oaid}`} title="open the academic Ledger paper page">
                      {w.title}
                    </Link>
                  </div>
                  <div className="rmeta">
                    {(() => {
                      const hasAuth = !!(w.authorships?.length || w.authors);
                      return (
                        <>
                          <Byline authorships={w.authorships} fallback={w.authors} />
                          {w.venue ? (hasAuth ? <> · {w.venue}</> : w.venue) : null}
                        </>
                      );
                    })()}
                    {w.oa ? <span style={{ color: "#2e8b57" }}> · OA</span> : null} ·{" "}
                    <a href={src} target="_blank" rel="noopener noreferrer">
                      source ↗
                    </a>
                  </div>
                </td>
                <td>
                  <FieldCell w={w} />
                </td>
                <td className="num">{w.year || ""}</td>
                <td className="num">{(w.cites || 0).toLocaleString()}</td>
                <td className="num qcell">
                  <QalCell m={w.metrics?.field} official={w.metrics?.official === "field"} />
                </td>
                <td className="num qcell">
                  <QalCell
                    m={w.metrics?.synthetic}
                    official={w.metrics?.official === "synthetic"}
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
