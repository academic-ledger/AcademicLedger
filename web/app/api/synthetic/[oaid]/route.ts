import { NextResponse } from "next/server";
import { computeSyntheticDisplay, writeSyntheticCache } from "@/lib/queries";

export const dynamic = "force-dynamic";

// The behavior gate. The expensive (~15-40 OpenAlex calls) synthetic-field compute lives ONLY here,
// and only on POST — a flat crawler GET (the budget/DoS vector) can't reach it. It's called by the
// paper page's client island after the page mounts in a real browser. On success it writes
// synthetic_cache so the next server render serves the official synthetic field for free.
//
// Bounds: (1) the cache — each paper computes at most once, then it's free; (2) this per-instance
// concurrency guard against a single-instance call-storm; (3) the GLOBAL bound is the Vercel edge
// rate-limit — extend the existing /paper rule to also cover /api/synthetic.
let inflight = 0;
const MAX_INFLIGHT = 3;

export async function POST(_req: Request, { params }: { params: { oaid: string } }) {
  if (inflight >= MAX_INFLIGHT) {
    return NextResponse.json({ ok: false, reason: "busy" }, { status: 429 });
  }
  inflight++;
  try {
    const payload = await computeSyntheticDisplay(params.oaid);
    if (!payload) return NextResponse.json({ ok: false, reason: "unplaceable" });
    await writeSyntheticCache(params.oaid, payload);
    return NextResponse.json({ ok: true });
  } catch (e: any) {
    return NextResponse.json({ ok: false, error: e?.message ?? "error" }, { status: 500 });
  } finally {
    inflight--;
  }
}
