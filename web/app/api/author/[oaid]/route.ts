import { NextResponse } from "next/server";
import { getAuthorRecord } from "@/lib/queries";

export const dynamic = "force-dynamic";

// CDN-cache successful GETs (Aug-2026 egress fix): repeat hits served from the edge, not Neon.
const CACHE = { "Cache-Control": "public, s-maxage=86400, stale-while-revalidate=604800" } as const;

export async function GET(_req: Request, { params }: { params: { oaid: string } }) {
  try {
    const payload = await getAuthorRecord(params.oaid);
    if (!payload) return NextResponse.json({ error: "not found" }, { status: 404 });
    return NextResponse.json(payload, { headers: CACHE });
  } catch (e: any) {
    return NextResponse.json({ error: e?.message ?? "error" }, { status: 500 });
  }
}
