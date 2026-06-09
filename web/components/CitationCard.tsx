"use client";

import { useState } from "react";

export default function CitationCard({ citation }: { citation: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="card">
      <h2>
        Cite this <span className="src">— formatted reference</span>
      </h2>
      <p className="citation">{citation}</p>
      <button
        className="copybtn"
        onClick={() => {
          navigator.clipboard?.writeText(citation).then(
            () => {
              setCopied(true);
              setTimeout(() => setCopied(false), 1500);
            },
            () => {}
          );
        }}
      >
        {copied ? "Copied ✓" : "Copy citation"}
      </button>
    </div>
  );
}
