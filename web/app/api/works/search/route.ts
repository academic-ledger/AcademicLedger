import { NextResponse } from "next/server";
import { searchWorks } from "@/lib/openalex";

// Typeahead for the C2 "canonical version" picker — live OpenAlex search (reuses the explore-fallback
// searcher), returns lightweight {oaid,title,year,authors} rows. Read-only.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const q = new URL(req.url).searchParams.get("q") || "";
  if (q.trim().length < 3) return NextResponse.json({ items: [] });
  try {
    const works = await searchWorks(q);
    return NextResponse.json({
      items: works.slice(0, 8).map((w) => ({ oaid: w.oaid, title: w.title, year: w.year, authors: w.authors })),
    });
  } catch {
    return NextResponse.json({ items: [] });
  }
}
