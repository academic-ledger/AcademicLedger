import { NextResponse } from "next/server";
import { checkReference } from "@/lib/openalex";

export const dynamic = "force-dynamic";
export const maxDuration = 60; // a long bibliography = many external lookups

// Split a pasted reference list into individual references. Handles numbered lists ([1] / 1. / (1)),
// blank-line-separated blocks, and one-per-line; strips the leading marker.
function splitRefs(text: string): string[] {
  const t = text.replace(/\r/g, "").trim();
  let parts: string[];
  const numbered = t.split(/\n(?=\s*(?:\[\d{1,3}\]|\(?\d{1,3}[.)])\s)/);
  if (numbered.length > 3) parts = numbered;
  else {
    const blocks = t.split(/\n\s*\n/);
    parts = blocks.length > 3 ? blocks : t.split(/\n/);
  }
  return parts
    .map((s) => s.replace(/^\s*(?:\[\d{1,3}\]|\(?\d{1,3}[.)])\s*/, "").replace(/\s+/g, " ").trim())
    .filter((s) => s.length >= 15);
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
