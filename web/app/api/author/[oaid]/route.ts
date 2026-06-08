import { NextResponse } from "next/server";
import { getAuthor } from "@/lib/queries";

export const dynamic = "force-dynamic";

export async function GET(_req: Request, { params }: { params: { oaid: string } }) {
  try {
    const payload = await getAuthor(params.oaid);
    if (!payload) return NextResponse.json({ error: "not found" }, { status: 404 });
    return NextResponse.json(payload);
  } catch (e: any) {
    return NextResponse.json({ error: e?.message ?? "error" }, { status: 500 });
  }
}
