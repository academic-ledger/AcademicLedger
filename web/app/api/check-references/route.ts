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
  const YEAR = /\((?:19|20)\d{2}[a-z]?[,)]/; // (2015) or (2026, April 8) or (2020a)
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

const MAX_REFS = 300; // generous cap; the client checks these in small sequential batches
const MAX_BATCH = 25; // per request — bounded so each stays well under maxDuration and paces Crossref

// Two request shapes so the client can process arbitrarily long bibliographies without hitting the
// function timeout or Crossref's burst rate limit:
//   { text }          -> split only, returns the individual reference STRINGS (no lookups; fast)
//   { batch: string[] } -> resolve this small chunk, returns RefResult[]
// The client splits once, then walks the list in sequential batches (with retries for "unresolved").
export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));

    if (Array.isArray(body?.batch)) {
      const batch = (body.batch as unknown[]).filter((s): s is string => typeof s === "string").slice(0, MAX_BATCH);
      const results = await mapLimit(batch, 6, checkReference);
      return NextResponse.json({ results });
    }

    const text = body?.text;
    if (!text || typeof text !== "string") {
      return NextResponse.json({ error: "Paste a reference list." }, { status: 400 });
    }
    const refs = splitRefs(text);
    if (!refs.length) return NextResponse.json({ error: "No references found in the pasted text." }, { status: 400 });
    return NextResponse.json({ refs: refs.slice(0, MAX_REFS), truncated: refs.length > MAX_REFS });
  } catch (e: any) {
    return NextResponse.json({ error: e?.message ?? "error" }, { status: 500 });
  }
}
