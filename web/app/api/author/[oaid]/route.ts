import { NextResponse } from "next/server";
import { getAuthorRecord } from "@/lib/queries";

export const dynamic = "force-dynamic";

export async function GET(_req: Request, { params }: { params: { oaid: string } }) {
  try {
    const payload = await getAuthorRecord(params.oaid);
    if (!payload) return NextResponse.json({ error: "not found" }, { status: 404 });
    return NextResponse.json(payload);
  } catch (e: any) {
    return NextResponse.json({ error: e?.message ?? "error" }, { status: 500 });
  }
}
