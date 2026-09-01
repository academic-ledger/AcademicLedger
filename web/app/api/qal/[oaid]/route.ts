import { NextResponse } from "next/server";
import { getPaperRecord } from "@/lib/queries";

export const dynamic = "force-dynamic";

// CDN-cache successful GETs (Aug-2026 egress fix): repeat crawler/API hits on the same paper are
// served from Vercel's edge, not re-invoking the function or re-querying Neon.
const CACHE = { "Cache-Control": "public, s-maxage=86400, stale-while-revalidate=604800" } as const;

export async function GET(_req: Request, { params }: { params: { oaid: string } }) {
  try {
    const rec = await getPaperRecord(params.oaid);
    if (!rec) return NextResponse.json({ error: "not found" }, { status: 404 });
    return NextResponse.json(rec, { headers: CACHE });
  } catch (e: any) {
    return NextResponse.json({ error: e?.message ?? "error" }, { status: 500 });
  }
}
