import { NextResponse } from "next/server";
import { getExplore } from "@/lib/queries";

export const dynamic = "force-dynamic";

// CDN-cache explore results (1h) so crawler-exploded facet URLs are served from the edge, not Neon.
const CACHE = { "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400" } as const;

export async function GET(req: Request) {
  try {
    const u = new URL(req.url);
    const sortRaw = u.searchParams.get("sort");
    const sort = sortRaw === "cites" || sortRaw === "year" ? sortRaw : "qal";
    const { items, live } = await getExplore({
      field: u.searchParams.get("field") || undefined,
      since: u.searchParams.get("since") ? Number(u.searchParams.get("since")) : undefined,
      q: u.searchParams.get("q") || undefined,
      calibrated_only: u.searchParams.get("calibrated_only") === "true",
      sort,
      limit: u.searchParams.get("limit") ? Number(u.searchParams.get("limit")) : undefined,
    });
    return NextResponse.json({ count: items.length, items, live }, { headers: CACHE });
  } catch (e: any) {
    return NextResponse.json({ error: e?.message ?? "error" }, { status: 500 });
  }
}
