import Brand from "@/components/Brand";

export const metadata = { title: "Talk — academic Ledger" };

// "Talk" = the seminar slides, embedded as a PDF so visitors see the deck immediately (the browser's
// native PDF viewer), with links to open it full-window or download it. The interactive reveal.js
// deck is still at /talk.html for presenting (press F to fullscreen).
const PDF = "/aL-Talk-OIDD-09July2026.pdf";

export default function TalkPage() {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100dvh" }}>
      <Brand active="talk" />
      <div
        style={{
          display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12,
          padding: "7px 22px", borderBottom: "1px solid #e5e7eb", background: "#fafbfc", flex: "0 0 auto",
        }}
      >
        <span style={{ fontSize: 13.5, color: "#333" }}>
          <b>All You Need is Q<i>a</i>L</b> &mdash; seminar slides, OID Department, July 2026
        </span>
        <span style={{ display: "flex", gap: 8 }}>
          <a
            href={PDF}
            target="_blank"
            rel="noopener"
            style={{ fontSize: 13, color: "#2166ac", textDecoration: "none", border: "1px solid #ccd2da", borderRadius: 6, padding: "4px 11px" }}
          >
            Open in new tab ↗
          </a>
          <a
            href={PDF}
            download
            style={{ fontSize: 13, color: "#fff", background: "#2e8b57", textDecoration: "none", borderRadius: 6, padding: "5px 12px", fontWeight: 600 }}
          >
            ⬇ Download PDF
          </a>
        </span>
      </div>
      <iframe src={PDF} title="academic Ledger — seminar slides" style={{ flex: 1, width: "100%", border: 0 }} />
    </div>
  );
}
