import { NextResponse } from "next/server";
import { checkReference } from "@/lib/openalex";

export const dynamic = "force-dynamic";
export const maxDuration = 60; // a long bibliography = many external lookups

const clean = (s: string) =>
  s.replace(/^\s*(?:\[\d{1,3}\]|\(?\d{1,3}[.)])\s*/, "").replace(/\s+/g, " ").trim();

// Split a pasted reference list into individual references. Handles numbered lists ([1] / 1. / (1)),
// and — the common hard case — author-date bibliographies that are HARD-WRAPPED across several lines.
// For those, a new reference begins at a line bearing a parenthesised year "(YYYY)"; continuation
// lines fold in, stray page numbers are dropped, and a trailing hyphen joins without a space so DOIs
// broken across a line break (…s12197-024-\n09691-w) are reconnected.
function splitRefs(text: string): string[] {
  const t = text.replace(/\r/g, "").trim();
  const lines = t.split("\n").map((l) => l.trim());
  const numberedStarts = lines.filter((l) => /^\s*(?:\[\d{1,3}\]|\(?\d{1,3}[.)])\s/.test(l)).length;
  if (numberedStarts > 3) {
    return t
      .split(/\n(?=\s*(?:\[\d{1,3}\]|\(?\d{1,3}[.)])\s)/)
      .map(clean)
      .filter((s) => s.length >= 15);
  }
  const YEAR = /\((?:19|20)\d{2}[a-z]?\)/;
  const refs: string[] = [];
  let cur = "";
  for (const s of lines) {
    if (!s || /^\d{1,4}$/.test(s)) continue;
    if (YEAR.test(s) && cur) {
      refs.push(cur);
      cur = s;
    } else if (cur.endsWith("-")) cur += s;
    else cur = cur ? cur + " " + s : s;
  }
  if (cur) refs.push(cur);
  let out = refs;
  if (out.length < 2) {
    const blocks = t.split(/\n\s*\n/);
    out = blocks.length > 1 ? blocks : t.split(/\n/);
  }
  return out.map(clean).filter((s) => s.length >= 15);
}

async function mapLimit<T, R>(items: T[], n: number, fn: (t: T) => Promise<R>): Promise<R[]> {
  const out: R[] = new Array(items.length);
  let i = 0;
  await Promise.all(
    Array.from({ length: Math.min(n, items.length) }, async () => {
      while (i < items.length) {
        const k = i++;
        out[k] = await fn(items[k]);
      }
    })
  );
  return out;
}

export async function POST(req: Request) {
  try {
    const { text } = await req.json();
    if (!text || typeof text !== "string") {
      return NextResponse.json({ error: "Paste a reference list." }, { status: 400 });
    }
    const refs = splitRefs(text);
    if (!refs.length) return NextResponse.json({ error: "No references found in the pasted text." }, { status: 400 });
    const capped = refs.slice(0, 80);
    const results = await mapLimit(capped, 6, checkReference);
    const found = results.filter((r) => r.status === "found").length;
    return NextResponse.json({ refs: results, total: results.length, found, truncated: refs.length > 80 });
  } catch (e: any) {
    return NextResponse.json({ error: e?.message ?? "error" }, { status: 500 });
  }
}
