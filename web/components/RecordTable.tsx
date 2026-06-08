"use client";

import { useState } from "react";
import Link from "next/link";
import type { RecordItem } from "@/lib/types";

type SortKey = "_r" | "title" | "subfield" | "year" | "cites" | "obs" | "qal";
type ColType = "rank" | "str" | "num";

const COLS: { k: SortKey; t: string; cls?: string; type: ColType }[] = [
  { k: "_r", t: "#", cls: "rank", type: "rank" },
  { k: "title", t: "Title", type: "str" },
  { k: "subfield", t: "Field", type: "str" },
  { k: "year", t: "Yr", cls: "num", type: "num" },
  { k: "cites", t: "Cites", cls: "num", type: "num" },
  { k: "obs", t: "Observed %", cls: "num", type: "num" },
  { k: "qal", t: "QaL (eventual %)", cls: "num", type: "num" },
];

function sortVal(w: RecordItem, key: SortKey): number | string {
  if (key === "qal") return w.qal ? w.qal.point : -1;
  const v = (w as any)[key];
  return v ?? -1;
}

export default function RecordTable({
  records,
  initialSortKey = "cites",
  initialSortDir = -1,
}: {
  records: RecordItem[];
  initialSortKey?: SortKey;
  initialSortDir?: 1 | -1;
}) {
  const [sortKey, setSortKey] = useState<SortKey>(initialSortKey);
  const [sortDir, setSortDir] = useState<1 | -1>(initialSortDir);

  function clickHeader(k: SortKey, type: ColType) {
    if (type === "rank") return;
    if (k === sortKey) setSortDir((d) => (d * -1) as 1 | -1);
    else {
      setSortKey(k);
      setSortDir(type === "str" ? 1 : -1);
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
                    {w.authors ? w.authors + (w.venue ? " · " + w.venue : "") : w.venue || ""}
                    {w.oa ? <span style={{ color: "#2e8b57" }}> · OA</span> : null} ·{" "}
                    <a href={src} target="_blank" rel="noopener noreferrer">
                      source ↗
                    </a>
                  </div>
                </td>
                <td>
                  <span className="ftagsm">{w.subfield || "—"}</span>
                  <br />
                  {w.calibrated ? (
                    <span className="seeddot">calibrated</span>
                  ) : (
                    <span className="penddot">pending</span>
                  )}
                </td>
                <td className="num">{w.year || ""}</td>
                <td className="num">{(w.cites || 0).toLocaleString()}</td>
                <td className="num">
                  {w.obs == null ? (
                    "—"
                  ) : (
                    <span className="obsv">
                      {w.obs}
                      <span className="pc">%</span>
                    </span>
                  )}
                </td>
                <td className="num qcell">
                  {w.calibrated && w.qal ? (
                    <>
                      <span className="pt">{w.qal.point}</span>{" "}
                      <span className="ci">
                        [{w.qal.lo}–{w.qal.hi}]
                      </span>
                    </>
                  ) : (
                    <span className="pend">calibration-pending</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
