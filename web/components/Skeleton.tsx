// Loading skeletons (U1): shown while server pages stream (route loading.tsx) and while
// the explore client fetch is in flight, so the UI never looks frozen.

import type { ReactNode } from "react";

function L({ w, h = 12, mt = 0 }: { w: number | string; h?: number; mt?: number }) {
  return (
    <span
      className="skel skel-line"
      style={{ width: w, height: h, marginTop: mt }}
    />
  );
}

const NOUP = { textTransform: "none" as const };
const HEADERS: { k: string; t: ReactNode }[] = [
  { k: "r", t: "#" },
  { k: "title", t: "Title" },
  { k: "fields", t: "Fields" },
  { k: "yr", t: "Yr" },
  { k: "cites", t: "Cites" },
  { k: "qf", t: <><span style={NOUP}>QaL</span> · field</> },
  { k: "qs", t: <><span style={NOUP}>QaL</span> · synthetic ★</> },
];

export function SkeletonTable({ rows = 10 }: { rows?: number }) {
  return (
    <div className="tbl-scroll" aria-busy="true" aria-label="loading records">
      <table className="recs">
        <thead>
          <tr>
            {HEADERS.map((h) => (
              <th key={h.k}>{h.t}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, i) => (
            <tr key={i}>
              <td className="rank">{i + 1}</td>
              <td>
                <L w="68%" />
                <br />
                <L w="42%" h={9} mt={5} />
              </td>
              <td>
                <L w={92} />
              </td>
              <td className="num">
                <L w={26} />
              </td>
              <td className="num">
                <L w={36} />
              </td>
              <td className="num">
                <L w={52} />
              </td>
              <td className="num">
                <L w={52} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function SkeletonPaper() {
  return (
    <div className="wrap-paper" aria-busy="true">
      <L w="80%" h={22} />
      <div style={{ marginTop: 10 }}>
        <L w="45%" h={13} />
      </div>
      <div className="qhero" style={{ marginTop: 18 }}>
        <div>
          <L w={120} h={11} />
          <div style={{ marginTop: 12 }}>
            <L w={170} h={48} />
          </div>
          <div style={{ marginTop: 12 }}>
            <L w="80%" h={11} />
          </div>
        </div>
        <div className="bkt">
          {[40, 64, 96, 120, 80, 50].map((h, i) => (
            <div className="col" key={i}>
              <span className="skel" style={{ width: 32, height: h, borderRadius: "5px 5px 0 0" }} />
            </div>
          ))}
        </div>
      </div>
      <div className="card">
        <L w={180} h={11} />
        <div className="grid" style={{ marginTop: 12 }}>
          {Array.from({ length: 6 }).map((_, i) => (
            <div className="cell" key={i}>
              <L w={70} h={18} />
              <br />
              <L w={100} h={9} mt={6} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function SkeletonAuthor() {
  return (
    <div className="wrap-author" aria-busy="true">
      <div className="ahead">
        <div>
          <L w={240} h={26} />
          <div style={{ marginTop: 8 }}>
            <L w={180} h={13} />
          </div>
        </div>
        <div className="astat">
          {Array.from({ length: 3 }).map((_, i) => (
            <div className="c" key={i}>
              <L w={40} h={20} />
              <br />
              <L w={48} h={9} mt={6} />
            </div>
          ))}
        </div>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <L w={160} h={11} />
        <div style={{ marginTop: 14 }}>
          <SkeletonTable rows={8} />
        </div>
      </div>
    </div>
  );
}
