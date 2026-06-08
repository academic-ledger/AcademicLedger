import { NextResponse } from "next/server";
import { getQalRecord } from "@/lib/queries";

export const dynamic = "force-dynamic";

export async function GET(_req: Request, { params }: { params: { oaid: string } }) {
  try {
    const rec = await getQalRecord(params.oaid);
    if (!rec) return NextResponse.json({ error: "not found" }, { status: 404 });
    return NextResponse.json(rec);
  } catch (e: any) {
    return NextResponse.json({ error: e?.message ?? "error" }, { status: 500 });
  }
}
